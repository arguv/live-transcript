"""Download and verify the speech model before starting the server."""
import argparse
import os
import shlex
import sys
from pathlib import Path

# Use ordinary HTTP downloads, which also work without the Xet transport.
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '120')
os.environ.setdefault('HF_HUB_ETAG_TIMEOUT', '30')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default='tiny.en',
                        help='Model name or Hugging Face repository ID (default: tiny.en).')
    parser.add_argument('--output', default='models/tiny.en')
    args = parser.parse_args()

    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model

    output = Path(args.output).resolve()
    print(f'Downloading {args.model} to {output}. Rerun to resume if interrupted.', flush=True)
    try:
        download_model(args.model, output_dir=str(output))
        WhisperModel(str(output), device='cpu', compute_type='int8',
                     local_files_only=True)
    except Exception as exc:
        parser.exit(1, f'Model preparation failed: {exc}\n'
                      'Check your connection to huggingface.co and rerun this command.\n')
    print(f'Model verified. Run: WHISPER_MODEL={shlex.quote(str(output))} '
          f'{shlex.quote(sys.executable)} -m uvicorn main:app --host 127.0.0.1 --port 8000')


if __name__ == '__main__':
    main()
