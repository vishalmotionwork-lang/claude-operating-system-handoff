---
name: video-style-decoder
description: >-
  Decode any edited / motion-graphic video into a REPEATABLE STYLE SYSTEM an editor
  can apply to a brand-new topic without reusing a single original visual. Output is a
  self-contained HTML reader: style fingerprint, the script-to-visual rulebook, a move
  library (every reusable visual treatment with its clip + a "swap-for/never-reuse"
  note), pace/timing stats, a full beat-by-beat timeline, and an "apply it to a new
  video" worksheet. Use when the user wants to break a video's STYLE into rules so an
  editor "just gets it" and can reproduce the look on similar-topic videos. Triggers:
  "break down this style", "make a style system / editing system", "so my editor can
  copy the style", "repeatable breakdown", "decode this edit", "/video-style-decoder".
  Distinct from video-inspo-extracter (which extracts CLIPS or tears down STRATEGY) —
  this extracts the transferable EDITING GRAMMAR.
---

# Video Style Decoder

Turn one edited video into a **style system**: the rules of how it's edited, written so an
editor reads it once, "gets it", and reproduces the style on a different topic — with
**brand-new visuals every time** (the grammar is reusable; the props are disposable).

This is the layer ABOVE `video-inspo-extracter`. That skill pulls assets out (Mode A) or
tears down strategy (Mode B). This one extracts the **editing grammar** and hands the editor
a reusable system. It reuses that skill's pipeline plumbing (`detect_and_sheet.py`, ffmpeg).

**Output:** a single offline HTML reader (`style-system.html`) with every move's clip embedded
inline. Default depth = **editing logic + timing** (what/when/why on screen + pacing), software-
agnostic — no AE/Premiere keyframe recipes unless the user asks.

---

## Prerequisites
- `ffmpeg`, `ffprobe`, `uvx` (for pillow + scenedetect, isolated). macOS has **no `timeout`** — never wrap commands.
- ffmpeg in a `while read` loop **must** use `-nostdin` (or it eats the loop's stdin).
- Transcription: Groq Whisper. For a URL use `~/.claude/scripts/transcribe.sh`; for a LOCAL file,
  extract audio + POST to Groq directly (key in `…/memory/groq-api-creds.md`, pattern below).
- Work in a per-video folder, e.g. `~/Downloads/<slug>-style/`. The HTML + `clips/` ship together.

---

## Workflow

### 1. Ingest + working copy
```bash
ffprobe -v error -show_entries format=duration:stream=codec_type,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 "SRC"          # confirm len / aspect / fps
ffmpeg -y -loglevel error -i "SRC" -vf "scale=1080:-2" -c:v libx264 -preset veryfast -crf 21 \
  -c:a aac -b:a 160k working.mp4                 # 1080-wide working copy (4K is overkill)
ffmpeg -y -loglevel error -i "SRC" -vn -ac 1 -ar 16000 -b:a 64k audio.mp3
```

### 2. Transcribe — the script is the spine
Every visual rule is anchored to a script moment, so get timestamps.
```bash
KEY="$GROQ_API_KEY"
curl -sS --fail-with-body https://api.groq.com/openai/v1/audio/transcriptions \
  -H "Authorization: Bearer $KEY" -F "file=@audio.mp3" -F "model=whisper-large-v3-turbo" \
  -F "response_format=verbose_json" -F "timestamp_granularities[]=segment" > transcript.json
```
If the video has little/no VO (text-driven), the "script" comes from the on-screen text you
read off the grids in step 3 — build the SCRIPT spine from that instead.

### 3. **Decode the frames — the key step (don't skip for scene-detect).**
Motion-graphics grammar lives in ON-SCREEN TEXT + overlays over continuous footage, which hard-cut
detection **under-counts**. Build a timecoded 2fps grid and READ it:
```bash
uvx --with pillow python3 scripts/grid_decode.py working.mp4 2     # -> grids/grid_##.jpg
```
`Read` every grid. For each beat note: which **mode** (Presenter = host+captions+narration, vs
Proof = b-roll/mockups/docs/icons/screen-rec/logos/numbers = concrete claims), the **move** in play,
the typography, the color world, transitions. (Optionally also run
`detect_and_sheet.py working.mp4 27` for a hard-cut count to quote in the pace stats.)

You are looking for the system, not a description:
- **The fingerprint** (6 read-in-3-seconds traits).
- **The core flip** — which two modes it alternates between, and the rate.
- **The one law** — e.g. "show every noun" (concrete thing said ⇒ shown within ~0.3s).
- **The rulebook** — topic-FREE `trigger → treatment` rules (line type ⇒ what goes on screen).
- **The move library** — every reusable visual treatment.
- **Pace** — runtime, hard cuts vs on-screen-state changes, mode split, where the one
  pattern-interrupt is placed (usually right before the CTA).

### 4. Cut one evidence clip per move (audio kept — moves are VO-synced)
Write `clips.csv` (`name,start,dur`) — one row per move, each window isolating ONE move:
```bash
bash scripts/cut_clips.sh working.mp4 clips.csv clips 540
```

### 5. Build the HTML reader
Clone `reference/style-system.template.html` → `style-system.html` and fill ONLY the `DATA`
block per `reference/DATA-CONTRACT.md` (SCRIPT, FP, RULES, MOVES, STATS, PACE, TL, WS, NOREUSE,
CHECK). Match the `:root` palette to the video when cheap. Verify before declaring done:
```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --window-size=1100,1500 \
  --screenshot=_chk.png "file://$PWD/style-system.html"   # eyeball the design
"$CHROME" --headless --disable-gpu --dump-dom "file://$PWD/style-system.html" \
  | grep -oc 'class="move"'                                # confirm all moves rendered
```

---

## The non-negotiables (this is what the user is actually buying)
- **Transferable, not a teardown.** Output is reusable RULES, not a clip catalog or strategy
  breakdown. See `feedback_strip_framework_not_teardown`.
- **Anti-repetition is the whole point.** EVERY move gets a `swap-for / never-reuse` note and the
  `NOREUSE` table is filled. The editor must build new props each video. Grammar = asset, props =
  disposable. See `feedback_remix_not_copy`.
- **Rules are topic-free.** "Line names a company → drop its logo", never "Stripe → Stripe logo".
- **The "apply it" worksheet uses a genuinely different topic** — proves the grammar transfers and
  forces fresh visuals (not a word-swap of the source).
- **Depth = editing logic + timing**, editor-agnostic. No AE/Premiere keyframe recipes unless asked.
- **Plain English.** No marketing-jargon framing ("engine/platform/pillars/loop/brain").
- **Motion must be seen** — embed playable clips, never substitute stills (`feedback_figjam_video_quantity_limit`).

## Gotchas (don't relearn)
- Scene-detect alone misses text-animation grammar — the 2fps grid decode is mandatory for motion graphics.
- Keep audio in the move clips; "synced to the voice" can't be studied silently.
- HTML is offline/self-contained: relative `clips/…` paths, no CDN-required JS. Google-Fonts link
  degrades to system fonts over file://.
- A fingerprint card rendering proves the script ran, but `--dump-dom | grep -c 'class="move"'`
  is the real check that the data-driven sections populated.

## Outputs
A per-video folder: `working.mp4`, `audio.mp3`, `transcript.json`, `grids/grid_##.jpg`,
`clips/NN_*.mp4`, `clips.csv`, and the deliverable **`style-system.html`** (open in any browser).

Reference build: `~/Downloads/fable5-style/` (47s vertical AI-launch short; 17 moves).
