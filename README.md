# VOIPIRAN Chatterbox

Persian text-to-speech HTTP service for Issabel/Rocky Linux 8 and Asterisk. It runs Chatterbox on CPU and writes WAV audio.

## راهنمای ساده نصب و استفاده

### ۱. آماده‌سازی مدل

یک حساب Hugging Face لازم است. وارد صفحه [مدل فارسی Chatterbox](https://huggingface.co/Thomcles/Chatterbox-TTS-Persian-Farsi) شوید، شرایط دسترسی را بپذیرید و از تنظیمات حساب یک توکن با دسترسی خواندن بسازید. مدل مجوز CC BY-NC 4.0 دارد؛ شرایط آن را پیش از استفاده بررسی کنید.

### ۲. نصب روی Issabel / Rocky Linux 8

سرور هنگام نصب باید به اینترنت دسترسی داشته باشد. مخزن را روی سرور دریافت کنید و از پوشه پروژه نصب را اجرا کنید:

```bash
git clone https://github.com/voipiran/voipiran-chatterbox.git
cd voipiran-chatterbox
sudo bash install.sh
```

نصب‌کننده توکن Hugging Face را به‌صورت مخفی می‌پرسد، وابستگی‌ها و مدل را دریافت می‌کند، سرویس را راه‌اندازی می‌کند و در پایان یک WAV آزمایشی می‌سازد. توکن برای دانلود اولیه است و در فایل سرویس ذخیره نمی‌شود. دانلود مدل ممکن است به‌دلیل حجم آن زمان ببرد.

### ۳. بررسی سرویس

```bash
sudo systemctl status voipiran-chatterbox
curl http://127.0.0.1:8000/health
```

اگر سرویس آماده باشد، پاسخ health شامل `"status":"ok"` است. برای دیدن خطاهای سرویس:

```bash
sudo journalctl -u voipiran-chatterbox -n 50 --no-pager
```

### ۴. ساخت فایل صوتی فارسی

از خود سرور یا کلاینتی که به API دسترسی دارد، این درخواست را اجرا کنید:

```bash
curl -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"سلام، این یک پیام آزمایشی است."}' \
  --output test.wav
```

فایل `test.wav` را پخش کنید. پاسخ API یک فایل WAV تک‌کاناله/مونو PCM با نرخ نمونه‌برداری مدل است.

### ۵. دسترسی از شبکه داخلی و Asterisk

به‌طور پیش‌فرض API فقط روی خود سرور در دسترس است. برای دسترسی از شبکه داخلی، فایل `/etc/voipiran-chatterbox.env` را ویرایش کنید، مقدار `CHATTERBOX_HOST` را به IP داخلی سرور یا `0.0.0.0` تغییر دهید و سرویس را راه‌اندازی مجدد کنید:

```bash
sudo systemctl restart voipiran-chatterbox
```

در firewall فقط دسترسی کلاینت‌های مورداعتماد را به پورت `8000` مجاز کنید. API احراز هویت ندارد، پس آن را مستقیماً در اینترنت منتشر نکنید. Asterisk می‌تواند از طریق HTTP فایل WAV را دریافت کند؛ فایل را در مسیری بگذارید که Asterisk بتواند بخواند و سپس با `Playback()` پخش کنید.

> **Model access and license:** `Thomcles/Chatterbox-TTS-Persian-Farsi` is gated on Hugging Face and licensed CC BY-NC 4.0. Accept the model conditions on its page and use it only in ways allowed by that license. A Hugging Face token is needed for the initial model download, but is not needed for inference after download.

## Install on Rocky Linux 8

Run as root on a machine with internet access. The installer installs Python 3.11, creates an isolated service account and virtual environment, installs CPU PyTorch, downloads the gated model, registers a loopback-only systemd service, and makes a real Persian WAV as its final check.

```bash
sudo bash install.sh
```

The installer prompts silently for `HF_TOKEN`; the token is used only for that download and is not written into the service configuration. The model is stored in `/var/lib/voipiran-chatterbox/model`.

Defaults are `127.0.0.1:8000`. To allow access from a trusted internal network, edit `/etc/voipiran-chatterbox.env`, set `CHATTERBOX_HOST` to the server's private address (or `0.0.0.0`), and restart the service. Restrict the firewall to trusted clients. This API has no user authentication; do not expose it to an untrusted network.

## API

`GET /health` reports readiness. `POST /tts` accepts JSON and returns `audio/wav`:

```bash
curl -X POST http://127.0.0.1:8000/tts \
  -H 'Content-Type: application/json' \
  -d '{"text":"سلام، به سرویس گفتار خوش آمدید."}' \
  --output greeting.wav
```

The optional `filename` field is ignored; audio is returned directly and temporary files are not retained. Asterisk can retrieve the WAV with its HTTP client/dialplan and play it via `Playback()` after placing it in an Asterisk-readable sound directory. The response is PCM WAV at the model's sample rate (typically 24 kHz).

## Request and credential flow

There are no existing application components or authentication implementation in the original repository: it was empty. The installed API is an internal service with no caller credentials or token issuance. During installation, the operator's HF token is passed only to the one-shot Hugging Face download process. Downloaded model artifacts are then loaded locally by `ChatterboxTTS.from_local`; the runtime service does not receive the HF token and does not make model-host requests. The installer does not persist credentials. Protect the host and limit network access because `/tts` itself is unauthenticated.

## Compatibility and limitations

The application targets Python 3.11, uses the upstream Chatterbox package loader and forces `device="cpu"`. Rocky Linux 8 is not available in this development environment, so RPM package availability, systemd operation, CPU performance, and the full gated model generation cannot be verified here. The installer checks for the Python 3.11 AppStream package and exits with guidance if unavailable. The model's CC BY-NC 4.0 terms may not permit commercial use.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
```
