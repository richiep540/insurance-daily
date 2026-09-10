#!/bin/bash
# Audition the podcast voices. Run:  bash smoke.sh
# Checks its own environment first and says plainly what is wrong.

cd "$(dirname "$0")" || { echo "FAILED: cannot find the project folder."; exit 1; }
echo "Project folder: $(pwd)"
echo

echo "1. Checking Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "   FAILED: python3 is not installed."
  echo "   Fix: install it from https://www.python.org/downloads/macos/"
  exit 1
fi
echo "   OK - $(python3 --version)"

echo "2. Checking the virtual environment..."
if [ ! -x "venv/bin/python" ]; then
  echo "   Not found. Creating it (takes about 30 seconds)..."
  python3 -m venv venv || { echo "   FAILED: could not create venv."; exit 1; }
fi
echo "   OK"

echo "3. Checking dependencies..."
if ! ./venv/bin/python -c "import feedparser, requests, pydub" >/dev/null 2>&1; then
  echo "   Installing..."
  ./venv/bin/pip install -q -r requirements.txt || { echo "   FAILED: pip install failed."; exit 1; }
fi
echo "   OK"

echo "4. Checking the Google key..."
if [ -z "$GOOGLE_TTS_API_KEY" ]; then
  echo "   Not set in this window."
  echo "   Get it from: https://console.cloud.google.com/apis/credentials"
  echo "   (click your Text-to-Speech key, then Show key)"
  echo
  printf "   Paste the key here and press Return: "
  read -r GOOGLE_TTS_API_KEY
  export GOOGLE_TTS_API_KEY
  echo
fi
if [ -z "$GOOGLE_TTS_API_KEY" ]; then
  echo "   FAILED: no key entered."
  exit 1
fi
echo "   OK - ${#GOOGLE_TTS_API_KEY} characters"

echo
echo "5. Voicing the sample..."
echo
./venv/bin/python scripts/generate_episode.py --smoke-test 2>&1 | grep -v "NotOpenSSLWarning\|warnings.warn\|RuntimeWarning\|Couldn't find ffmpeg\|warn("
status=${PIPESTATUS[0]}

echo
if [ "$status" -eq 0 ] && [ -f smoke_test.wav ]; then
  echo "DONE. Opening the audio now."
  open smoke_test.wav
else
  echo "That did not work. Copy everything above this line and send it to Claude."
fi
