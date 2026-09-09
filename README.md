# Insurance Daily

A ten-minute US insurance news briefing, automatically produced and published every weekday
morning. Written for **independent agents and brokers** — the people placing and servicing
commercial and personal lines.

Hosts: **Dana** and **Ray**.

Every weekday at 09:00 UTC (5am US Eastern) a GitHub Action pulls the last thirty hours of trade
press, has Claude select and rank the stories that actually matter to an agency, writes a briefing
around them, voices it with Google's Gemini-TTS multi-speaker synthesis, and publishes it to a
podcast RSS feed on GitHub Pages.

---

## Why this show exists

Every B2B vertical has interview podcasts, because that is what a human can sustainably make.
Almost none have a tight daily news briefing, because that is relentless, unglamorous work for a
person — and trivial for a pipeline. Insurance has ~90 podcasts and not one of them is a briefing.
That gap is the whole thesis.

## How it works

```
8 RSS feeds ──▶ ~70 stories/day ──▶ drop anything covered in the last 5 days
      │
      ▼
TRIAGE: one Claude call ranks them and picks ~11, assigning each a slot
      │
      ├── lead      the day's top story
      ├── deep      one story unpacked properly
      ├── headline  the main run, ~6 stories
      └── quick     one-line mentions
      │
      ▼
Claude writes 4 segments from that selection (~2,000 words ≈ 10 minutes)
      │
      ▼
Gemini-TTS voices it in conversational batches ──▶ one mp3
      │
      ▼
docs/feed.xml + episodes.json + index.html ──▶ GitHub Pages
```

**Triage is the part that makes a daily show viable.** These feeds produce roughly seventy
usable stories a day and the show can carry eleven. Picking by recency — which is what a simpler
pipeline does — gets you plane crashes and consumer Medicare explainers. Picking by editorial
brief gets you carrier appetite changes and renewal-cycle shifts. The brief lives in
`config.json` under `editorial_brief` and is the single highest-leverage thing to tune.

### Files

| Path | What it is |
| --- | --- |
| `config.json` | Feeds, editorial brief, segments, hosts, voices |
| `scripts/generate_episode.py` | The whole pipeline |
| `scripts/make_cover.py` | Generates `docs/cover.jpg` (run locally, result committed) |
| `tests/test_offline.py` | Checks needing no API keys; runs in CI before generation |
| `.github/workflows/daily-podcast.yml` | Weekday 09:00 UTC schedule |
| `docs/feed.xml` | The podcast feed — **generated, do not hand-edit** |
| `docs/transcripts/` | The written script for each episode |
| `docs/episodes/` | The mp3 files |

---

## Setup

Identical to the other pipelines. In short:

1. Public GitHub repo, push this folder to `main`
2. **Settings → Secrets and variables → Actions → Secrets**: add `ANTHROPIC_API_KEY` and
   `GOOGLE_TTS_API_KEY`. The Anthropic key must be **workspace-scoped**, not organisation-scoped
   (choose a workspace in the **Scope** dropdown when creating it), or add an
   `ANTHROPIC_WORKSPACE_ID` variable instead.
3. **Settings → Pages**: deploy from branch `main`, folder `/docs`
4. **Variables tab**: `PUBLIC_BASE_URL` = the Pages URL, **no trailing slash**
5. Google Cloud: enable **Cloud Text-to-Speech API** *and* **Vertex AI API** — Gemini-TTS runs on
   Vertex and returns a 403 without it
6. **Actions → Daily podcast → Run workflow** to produce the first episode
7. Submit the feed at [podcastsconnect.apple.com](https://podcastsconnect.apple.com) and
   [podcasters.spotify.com](https://podcasters.spotify.com)

---

## Editorial rules built into the prompts

These exist because the audience is professional and will not forgive sloppiness:

- **Sources are named on air.** "Insurance Journal is reporting…" Every story, every time. It is
  honest, it tells the listener how much weight to give a claim, and it keeps the show on the
  right side of using other people's reporting. Summarising reported facts with attribution is
  ordinary news commentary; reading their prose aloud would not be, and the prompt forbids it.
- **Nothing is invented.** No number, name, quote or rate change that is not in the source
  material. An audience of brokers will spot a fabricated figure immediately and never return.
- **No advice.** The show reports what happened and what it may mean commercially. It does not
  tell anyone how to handle a claim or read a policy.

## Tuning it

**`editorial_brief`** — what makes the show and what does not. Most valuable dial in the file.

**`audience`** — currently agents and brokers. Change this and triage, framing and vocabulary all
shift with it.

**`segments[].words`** — currently 250 / 900 / 650 / 200 = 2,000 words ≈ 10 minutes at Gemini-TTS
pace (measured at roughly 199 words per minute). Scale together to change runtime.

**`gemini_tts_style_prompt`** — how the hosts sound. Plain English direction. Audition changes
cheaply without generating an episode:

```bash
GOOGLE_TTS_API_KEY=... python scripts/generate_episode.py --smoke-test
```

**Feeds** — `source_name` overrides an unwieldy feed title, since sources get read aloud.
`require_any` filters loosely-related results, needed on the Google News feed.

## Local testing

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/generate_episode.py --feeds-only    # no keys needed
./venv/bin/python tests/test_offline.py
```

## Known gotchas

- **403 from Gemini-TTS** — the Vertex AI API is not enabled on the Google Cloud project.
- **"API key is not scoped to a workspace"** — org-scoped Anthropic key; see setup step 2.
- **`coverager.com` returns 403** to automated fetches. It fails gracefully and the other feeds
  more than cover the gap.
- **Episodes not playing** — `PUBLIC_BASE_URL` missing or has a trailing slash.
