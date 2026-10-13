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

Run these steps from the project directory. Prepare and verify the model once before starting the server:

```bash
.venv/bin/python download_model.py
```

Wait for the command to finish successfully and print `Model verified. Run: ...`. If the downloader fails or stalls, use the [direct download fallback](#direct-download-fallback) below before continuing. On later runs, reuse the downloaded directory; downloading again is unnecessary.

Start one server in your terminal and leave that terminal open:

```bash
WHISPER_MODEL="$PWD/models/tiny.en" .venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

These commands use the project's virtual environment directly, so activation is not required. Run them from the project directory.

## Project files

- `main.py`: FastAPI routes, audio capture, transcription worker, and in-memory state.
- `download_model.py`: Downloads a model and verifies that it loads locally on CPU.
- `static/index.html`: Browser controls and transcript display.
- `requirements.txt`: Python dependencies.
- `models/`: Local model directories prepared by the download helper.
