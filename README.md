# Live Transcript

Local English speech transcription from system playback audio, with a browser interface built on FastAPI and faster-whisper. The app captures a PulseAudio monitor source through FFmpeg and transcribes it on CPU using INT8 inference.

## Requirements

- Linux with PulseAudio, or a compatible PulseAudio service such as PipeWire's PulseAudio interface.
- Python with `venv` support and the packages in `requirements.txt`.
- FFmpeg with PulseAudio input support and `pactl` for selecting an audio source.
- Internet access to download the speech model initially; a complete local model can be used afterward.

## Install

Run these commands from the project directory on Debian/Ubuntu:

```bash
sudo apt update
sudo apt install -y ffmpeg pulseaudio-utils python3-venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Run

Prepare and verify the model before starting the server:

```bash
.venv/bin/python download_model.py
```

Wait for the command to finish successfully and print `Model verified. Run: ...`. Then start the server:

```bash
WHISPER_MODEL="$PWD/models/tiny.en" .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

These commands use the project's virtual environment directly, so activation is not required. Run them from the project directory.

If you previously saw `uvicorn: command not found`, use the command above. If it reports `No module named uvicorn`, install the project dependencies and try again:

```bash
.venv/bin/python -m pip install -r requirements.txt
WHISPER_MODEL="$PWD/models/tiny.en" .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

If `.venv/bin/python` does not exist, complete the [Install](#install) steps first. Uvicorn is included in `requirements.txt`; install it in this virtual environment rather than through `apt`.

Open http://127.0.0.1:8000, click **Start listening**, and play English speech through the selected output device. The default source is the Logitech H340 headset monitor; see [Audio source](#audio-source) to choose another device. The verified local model loads without a model download.

- **Start listening** loads the model and starts capturing playback audio.
- **Stop** requests capture to stop; it may take until the current read/transcription finishes.
- **Clear history** removes the stored transcript entries without stopping capture.

The page displays the latest transcribed chunk and timestamped history, newest first, and polls the server every second. It retains up to 150 nonempty transcript entries in RAM only. History survives stopping and restarting capture, but is lost when the server exits or you clear it. Closing the browser tab does not stop capture; use **Stop** or shut down the server with `Ctrl+C`.

Audio is processed locally and is not saved by the app. All browser clients connected to the same server share capture state and history.

## Configuration

Set environment variables when starting the server:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AUDIO_SOURCE` | Logitech H340 monitor source shown below | PulseAudio source to capture. |
| `WHISPER_MODEL` | `tiny.en` | faster-whisper model name or path to a complete local CTranslate2 model directory. A model name may trigger a download. |
| `CHUNK_SECONDS` | `4` | Audio chunk duration in seconds; use a positive integer. |

For example, after preparing `models/tiny.en`:

```bash
AUDIO_SOURCE='your.output.monitor' \
WHISPER_MODEL="$PWD/models/tiny.en" \
CHUNK_SECONDS=3 \
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Transcription is fixed to English and runs with three CPU threads, one worker, and beam size 1. Restart the server after changing environment variables.

## Model download troubleshooting

During model preparation, Hugging Face may print this warning:

```text
UserWarning: The `local_dir_use_symlinks` argument is deprecated and ignored in `snapshot_download`. Downloading to a local directory does not use symlinks anymore.
```

This warning is harmless: a dependency passes an option that Hugging Face now ignores. It does not mean the download failed or finished. Leave the command running and wait for `Model verified. Run: ...` before starting the server. Do not start a second download while the first is still running. If the command exits with `Model preparation failed: ...`, follow the troubleshooting steps below and rerun it.

The `tiny.en` CTranslate2 model needs roughly 75 MB of weights in `model.bin`, plus configuration and tokenizer files. A 2.5 MB cache containing only those supporting files is incomplete. An `.incomplete` file is download progress, not usable weights.

`download_model.py` uses ordinary HTTP downloads instead of Hugging Face's Xet transport and allows 120 seconds of download inactivity before timing out. Rerun the same command after a failure to reuse completed files and resume supported partial downloads. Do not delete the entire Hugging Face cache. The command reports success only after loading the downloaded model on CPU.

If the connection still fails, check access to `huggingface.co` and the download host named in the error, including any proxy or firewall restrictions. You can also run the download command on another machine with the same dependencies, copy the complete `models/tiny.en` directory here, and start the server with `WHISPER_MODEL` set to its absolute path. Use a faster-whisper/CTranslate2 model directory, rather than OpenAI Whisper `.pt` weights.

To prepare another model, use `.venv/bin/python download_model.py --model base.en --output models/base.en` and point `WHISPER_MODEL` to that directory.

## Audio source

Default source:

`alsa_output.usb-Logitech_Inc._Logi_USB_Headset_H340-00.analog-stereo.monitor`

To override:

```bash
AUDIO_SOURCE='another.monitor.source' WHISPER_MODEL="$PWD/models/tiny.en" \
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Find source names with:

```bash
pactl list short sources
pactl list short sinks
```

Choose the `.monitor` source corresponding to the output device used by your video or meeting app. This captures playback audio, rather than your headset microphone. A source listed as `SUSPENDED` is normal when no audio is playing.

If no transcript appears, check that audio is playing through the matching output device and inspect the status message in the browser. If capture stops with an error, verify that `AUDIO_SOURCE` exists and FFmpeg can access the PulseAudio service in your user session.

## Performance

This prototype uses `tiny.en` with CPU INT8, 4-second chunks and sequential transcription. The delay is at least one chunk plus model processing time and can be much longer on an older CPU. Chunk boundaries can split words and sentences. Text is not guaranteed to be a question. For a faster or more accurate version, benchmark the machine first.

## HTTP API

| Method | Endpoint | Behavior |
| --- | --- | --- |
| `GET` | `/` | Serves the browser interface. |
| `GET` | `/state` | Returns `running`, `status`, `error`, and `items` (each with `time` and `text`). |
| `POST` | `/start` | Starts the transcription worker if it is not already running. |
| `POST` | `/stop` | Requests the worker to stop. |
| `POST` | `/clear` | Clears transcript history. |

The POST endpoints return `{"ok": true}` when the request is accepted; poll `/state` for the actual worker status and errors. Interactive API documentation is available at http://127.0.0.1:8000/docs while the server is running.

## Project files

- `main.py`: FastAPI routes, audio capture, transcription worker, and in-memory state.
- `download_model.py`: Downloads a model and verifies that it loads locally on CPU.
- `static/index.html`: Browser controls and transcript display.
- `requirements.txt`: Python dependencies.
- `models/`: Local model directories prepared by the download helper.
