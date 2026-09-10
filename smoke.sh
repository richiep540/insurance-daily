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

ENGINE=$(./venv/bin/python -c "import json;print(json.load(open('config.json')).get('tts_engine','gemini'))")
echo "4. Checking credentials for the '$ENGINE' engine..."
if [ "$ENGINE" = "gemini" ]; then
  if [ -f service-account.json ]; then
    echo "   OK - using service-account.json"
  elif [ -n "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then
    echo "   OK - using GOOGLE_SERVICE_ACCOUNT_JSON"
  else
    echo "   FAILED: Gemini-TTS needs a service account, not an API key."
    echo
    echo "   1. Go to https://console.cloud.google.com/iam-admin/serviceaccounts"
    echo "   2. Create a service account, any name"
    echo "   3. Grant it the role: Vertex AI User"
    echo "   4. Open it, Keys tab, Add key, Create new key, JSON, Create"
    echo "   5. Move the downloaded file into this folder and rename it:"
    echo "        $(pwd)/service-account.json"
    echo "   6. Run this script again"
    echo
    echo "   Or, to skip all of that and use the free voices instead, set"
    echo "   \"tts_engine\": \"chirp3\" in config.json."
    exit 1
  fi
else
  if [ -z "$GOOGLE_TTS_API_KEY" ]; then
    echo "   Chirp 3: HD needs your Text-to-Speech API key."
    echo "   Get it from https://console.cloud.google.com/apis/credentials"
    echo
    printf "   Paste the key and press Return: "
    read -r GOOGLE_TTS_API_KEY
    export GOOGLE_TTS_API_KEY
    echo
  fi
  [ -z "$GOOGLE_TTS_API_KEY" ] && { echo "   FAILED: no key entered."; exit 1; }
  echo "   OK - ${#GOOGLE_TTS_API_KEY} characters"
fi

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
