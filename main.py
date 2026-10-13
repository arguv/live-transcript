import os
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '120')
os.environ.setdefault('HF_HUB_ETAG_TIMEOUT', '30')

SOURCE = os.getenv('AUDIO_SOURCE', 'alsa_output.usb-Logitech_Inc._Logi_USB_Headset_H340-00.analog-stereo.monitor')
MODEL = os.getenv('WHISPER_MODEL', 'tiny.en')
CHUNK_SECONDS = int(os.getenv('CHUNK_SECONDS', '4'))
app = FastAPI()
items = deque(maxlen=150)
state = {'running': False, 'status': 'Stopped', 'error': None}
lock = threading.Lock()
stop_event = threading.Event()
worker = None


def transcribe_loop():
    proc = None
    try:
        from faster_whisper import WhisperModel
        with lock:
            state['status'] = 'Loading speech model (first run downloads model)...'
        try:
            model = WhisperModel(MODEL, device='cpu', compute_type='int8', cpu_threads=3, num_workers=1)
        except Exception as exc:
            raise RuntimeError(
                f'Could not load speech model {MODEL!r}: {exc}. '
                'Prepare a complete model with python download_model.py, then restart '
                'the server with WHISPER_MODEL pointing to the downloaded directory. '
                'See README.md for download troubleshooting.'
            ) from exc
        with lock:
            state['status'] = 'Listening to headset output'
        proc = subprocess.Popen(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'pulse', '-i', SOURCE,
                                 '-ac', '1', '-ar', '16000', '-f', 's16le', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        chunk_size = 16000 * 2 * CHUNK_SECONDS
        while not stop_event.is_set():
            audio = bytearray()
            while len(audio) < chunk_size and not stop_event.is_set():
                block = proc.stdout.read(min(8192, chunk_size - len(audio)))
                if not block:
                    raise RuntimeError('Audio capture stopped. Check the selected PulseAudio monitor source.')
                audio.extend(block)
            if stop_event.is_set():
                break
            import numpy as np
            samples = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            segments, info = model.transcribe(samples, language='en', beam_size=1, vad_filter=True,
                                               condition_on_previous_text=False)
            text = ' '.join(s.text.strip() for s in segments).strip()
            if text:
                with lock:
                    items.appendleft({'time': time.strftime('%H:%M:%S'), 'text': text})
    except Exception as exc:
        with lock:
            state['error'] = str(exc)
            state['status'] = 'Error'
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
        with lock:
            state['running'] = False
            if state['status'] != 'Error':
                state['status'] = 'Stopped'


@app.get('/')
def home():
    return FileResponse(Path(__file__).parent / 'static' / 'index.html')


@app.get('/state')
def get_state():
    with lock:
        return {'items': list(items), **state}


@app.post('/start')
def start():
    global worker
    with lock:
        if state['running']:
            return {'ok': True}
        stop_event.clear()
        state.update(running=True, status='Starting', error=None)
    worker = threading.Thread(target=transcribe_loop, daemon=True)
    worker.start()
    return {'ok': True}


@app.post('/stop')
def stop():
    stop_event.set()
    return {'ok': True}


@app.post('/clear')
def clear():
    with lock:
        items.clear()
    return {'ok': True}
