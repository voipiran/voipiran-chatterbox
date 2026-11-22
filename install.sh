#!/usr/bin/env bash
set -Eeuo pipefail

[[ $EUID -eq 0 ]] || { echo "Run this installer as root (sudo bash install.sh)." >&2; exit 1; }
[[ -f /etc/rocky-release ]] || { echo "This installer targets Rocky Linux 8." >&2; exit 1; }
release=$(rpm -E '%{rhel}')
[[ "$release" == 8 ]] || { echo "Expected Rocky Linux 8; detected major release $release." >&2; exit 1; }

dnf install -y python3.11 python3.11-pip curl
PYTHON=$(command -v python3.11 || true)
[[ -n "$PYTHON" ]] || { echo "Python 3.11 is unavailable from enabled Rocky 8 repositories." >&2; exit 1; }

APP_DIR=/opt/voipiran-chatterbox
DATA_DIR=/var/lib/voipiran-chatterbox
install -d -m 0755 "$APP_DIR" "$DATA_DIR/model"
id chatterbox >/dev/null 2>&1 || useradd --system --home-dir "$DATA_DIR" --shell /sbin/nologin chatterbox
chown -R chatterbox:chatterbox "$DATA_DIR"

model_is_ready() {
  local name
  for name in ve.safetensors t3_cfg.safetensors s3gen.safetensors tokenizer.json; do
    [[ -s "$DATA_DIR/model/$name" ]] || return 1
  done
  return 0
}

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cp -a "$SCRIPT_DIR/src" "$SCRIPT_DIR/pyproject.toml" "$APP_DIR/"
"$PYTHON" -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip wheel
# Install the CPU build explicitly. Then install the upstream runtime package and
# restore the CPU wheels to ensure no CUDA-enabled torch is left in the environment.
"$APP_DIR/venv/bin/pip" install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
"$APP_DIR/venv/bin/pip" install "$APP_DIR"
"$APP_DIR/venv/bin/pip" install chatterbox-tts
"$APP_DIR/venv/bin/pip" install --force-reinstall --no-deps torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu

if model_is_ready; then
  echo "Found local model files; skipping Hugging Face login and download."
else
  read -r -s -p "Hugging Face token (gated Persian model; not saved): " HF_TOKEN
  echo
  [[ -n "$HF_TOKEN" ]] || { echo "A Hugging Face token is required for the initial download." >&2; exit 1; }
  export CHATTERBOX_MODEL_DIR="$DATA_DIR/model"
  chown chatterbox:chatterbox "$DATA_DIR/model"
  runuser -u chatterbox -- env CHATTERBOX_MODEL_DIR="$DATA_DIR/model" "$APP_DIR/venv/bin/python" -m voipiran_chatterbox.download_model <<< "$HF_TOKEN"
  unset HF_TOKEN
fi

cat >/etc/voipiran-chatterbox.env <<EOF
CHATTERBOX_MODEL_DIR=$DATA_DIR/model
CHATTERBOX_HOST=127.0.0.1
CHATTERBOX_PORT=8000
EOF
chmod 0644 /etc/voipiran-chatterbox.env
install -m 0644 "$SCRIPT_DIR/systemd/voipiran-chatterbox.service" /etc/systemd/system/voipiran-chatterbox.service
systemctl daemon-reload
systemctl enable --now voipiran-chatterbox

for attempt in {1..90}; do
  if curl --fail --silent http://127.0.0.1:8000/health >/dev/null; then break; fi
  sleep 2
done
curl --fail --silent http://127.0.0.1:8000/health >/dev/null || { journalctl -u voipiran-chatterbox -n 80 --no-pager; exit 1; }
TMP_WAV=$(mktemp --suffix=.wav)
trap 'rm -f "$TMP_WAV"' EXIT
curl --fail --silent --show-error -X POST http://127.0.0.1:8000/tts -H 'Content-Type: application/json' \
  -d '{"text":"سلام، این یک آزمون تولید گفتار فارسی است."}' -o "$TMP_WAV"
"$APP_DIR/venv/bin/python" - "$TMP_WAV" <<'PY'
import soundfile as sf, sys
samples, rate = sf.read(sys.argv[1])
if rate <= 0 or samples.size == 0:
    raise SystemExit("Generated WAV is empty or invalid")
print(f"Real Persian TTS generation passed: {sys.argv[1]} ({rate} Hz, {samples.size} samples)")
PY
echo "Installation completed. Service: systemctl status voipiran-chatterbox"
