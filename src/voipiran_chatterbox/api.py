from __future__ import annotations

import io
import os
import re
from contextlib import asynccontextmanager

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .model import load_model


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Fail service startup when the checkpoint cannot load, rather than a later call.
    load_model()
    yield


app = FastAPI(title="VOIPIRAN Chatterbox TTS", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "device": "cpu"}


@app.post("/tts")
def synthesize(request: TTSRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="text must not be blank")
    try:
        model = load_model()
        with torch.inference_mode():
            audio = model.generate(text)
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        samples = np.asarray(audio, dtype=np.float32).squeeze()
        if samples.ndim != 1 or samples.size == 0 or not np.isfinite(samples).all():
            raise ValueError("model returned invalid audio samples")
        buffer = io.BytesIO()
        sf.write(buffer, samples, int(model.sr), format="WAV", subtype="PCM_16")
        return Response(
            content=buffer.getvalue(),
            media_type="audio/wav",
            headers={"Content-Disposition": 'attachment; filename="speech.wav"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        # Do not return local paths, secrets, or model internals to API callers.
        raise HTTPException(status_code=503, detail="speech generation failed") from exc


def main():
    import uvicorn

    host = os.getenv("CHATTERBOX_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: API has no caller authentication; restrict access with a firewall.")
    uvicorn.run(app, host=host, port=int(os.getenv("CHATTERBOX_PORT", "8000")), workers=1)


if __name__ == "__main__":
    main()
