from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

MODEL_ID = "Thomcles/Chatterbox-TTS-Persian-Farsi"
REQUIRED = {"ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json"}


def main() -> int:
    target = Path(os.environ.get("CHATTERBOX_MODEL_DIR", "/var/lib/voipiran-chatterbox/model"))
    # Accept either an explicit HF_TOKEN or a one-shot token on stdin. The
    # installer uses stdin so the secret is not placed in another process's argv.
    token = os.environ.get("HF_TOKEN") or sys.stdin.readline().strip()
    if not token:
        print("HF_TOKEN is required. Accept the model conditions on Hugging Face first.", file=sys.stderr)
        return 2
    try:
        snapshot_download(
            repo_id=MODEL_ID,
            repo_type="model",
            local_dir=target,
            token=token,
            # Keep only the Chatterbox checkpoint files used by upstream from_local().
            allow_patterns=["*.safetensors", "*.json", "*.pt"],
        )
    except Exception as exc:
        print(f"Model download failed: {exc}", file=sys.stderr)
        print("Check HF_TOKEN and verify that the account accepted the gated model conditions.", file=sys.stderr)
        return 1
    missing = sorted(name for name in REQUIRED if not (target / name).is_file())
    if missing:
        print("Downloaded repository does not match upstream Chatterbox checkpoint layout: " + ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
