from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

import torch

MODEL_ID = "Thomcles/Chatterbox-TTS-Persian-Farsi"
MODEL_DIR = Path(os.getenv("CHATTERBOX_MODEL_DIR", "/var/lib/voipiran-chatterbox/model"))
_model = None
_lock = Lock()


def load_model():
    """Load the fine-tuned checkpoint from disk; never contact Hugging Face."""
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is None:
            required = ("ve.safetensors", "t3_cfg.safetensors", "s3gen.safetensors", "tokenizer.json")
            missing = [name for name in required if not (MODEL_DIR / name).is_file()]
            if missing:
                raise FileNotFoundError(
                    f"Missing model files in {MODEL_DIR}: {', '.join(missing)}. "
                    "Run install.sh and accept the Hugging Face model conditions first."
                )
            # Explicit CPU load avoids accidental CUDA use, including on hosts with GPUs.
            from chatterbox.tts import ChatterboxTTS

            _model = ChatterboxTTS.from_local(MODEL_DIR, device="cpu")
    return _model


def reset_model_for_tests() -> None:
    global _model
    _model = None
