---
name: synced-captions
description: >
  Generate word-synced, phrase-aware caption SRT files from a local audio/video
  file OR a URL (Instagram, YouTube, TikTok, direct media). Produces short
  reels-style captions (default 2 words per line) where each chunk is timed to
  its own words and grouped into meaningful phrases — not a mechanical N-word
  split. Punctuation is stripped by default while decimals (1.9), % and
  contractions (I'm/I'll) are preserved. Use when the user asks for an SRT,
  "captions", "subtitles", "2-word synced captions", "karaoke captions", or
  caption files for a reel / short / talking-head video.
allowed-tools: Bash, Read, AskUserQuestion
---

# synced-captions

Turn any audio/video — a local file or a URL — into a clean, word-synced caption
`.srt` with short reels-style lines that actually read well.

## What makes this different from `/transcript`

- `/transcript` outputs a plain `.txt` transcript from URLs only.
- This skill outputs a **timed `.srt`** from **local files or URLs**, with
  **word-level sync** and **phrase-aware grouping** (1–2 word lines that keep
  grammatical units together), plus **punctuation stripping** for caption style.

## Usage

```
~/.claude/skills/synced-captions/scripts/synced_captions.py INPUT [options]
```

- `INPUT` — local file path **or** `http(s)` URL
- `--max-words N` — max words per caption (default `2`)
- `--out PATH` — output `.srt` path (default: next to a local file, or
  `~/Downloads/transcripts/<today>/<slug>-synced.srt` for a URL)
- `--keep-punct` — keep original punctuation in the caption text
- `--model NAME` — Groq Whisper model (default `whisper-large-v3-turbo`)
- `--language CODE` — ISO-639-1 hint, e.g. `en` (optional, improves accuracy)

## Workflow

1. **Parse the request.** Identify the input (local path or URL) and the desired
   words-per-caption (default 2). If no input is given, ask the user via
   AskUserQuestion for the file path or URL. Quote shell paths with spaces.

2. **Run the script** with Bash:

   ```bash
   ~/.claude/skills/synced-captions/scripts/synced_captions.py "<input>" --max-words 2
   ```

   It handles the whole pipeline: fetch/locate media → extract & downsample audio
   to mono 16kHz mp3 (fits Groq's 25MB upload limit even for multi-GB ProRes) →
   Groq Whisper `verbose_json` with `timestamp_granularities[]=word` → phrase-aware
   grouping → punctuation cleanup → monotonic timing → write `.srt`. The full SRT
   prints to stdout; the save path prints to stderr.

3. **Surface the result.** Show the user the caption count and the saved path.
   If they want different phrasing on specific lines, edit just those — the script
   is deterministic, so re-running gives the same base to tweak from.

## How the phrasing heuristic works

Greedy chunking up to `--max-words`, but a chunk is **never allowed to end on a
"leader" word** — articles (a/an/the), prepositions (of/to/with/from/as…),
conjunctions (and/or/but/so), determiners/possessives (my/your/this/that…), or
subject pronouns (I/you/we/they…). When the last word of a candidate chunk is a
leader, the chunk shrinks by one so that word leads the **next** caption instead.
That's what turns a robotic `Hi, I'm` / `Alex. I` split into natural
`I'm Alex` / `I spent` / `the last` / `10 years` lines.

## Punctuation rules (default)

Stripped: `. , ! ? ; : " () […]` and other sentence punctuation.
Preserved: decimal points **inside numbers** (`1.9`), the `%` sign, and
apostrophes in contractions (`I'm`, `I'll`). Pass `--keep-punct` to keep
everything.

## Requirements

- `ffmpeg`, `curl` (and `yt-dlp` only if the input is a URL) — `brew install ffmpeg yt-dlp`
- A Groq API key. The script reads `GROQ_API_KEY` from the environment, falling
  back to `~/.claude/projects/-Users-YOUR-USER/memory/groq-api-creds.md`.
  **To share this skill, set `GROQ_API_KEY` in your env** — the creds-file path is
  machine-specific.

## Notes

- Whisper word timestamps can overlap slightly at segment seams; the script
  clamps each caption's start to the previous caption's end so the timeline is
  strictly increasing (no double captions on screen).
- Re-run with `--max-words 3` for slightly longer lines, or `--max-words 1` for
  strict one-word-at-a-time karaoke captions.
- Idempotent for a given input/options — safe to re-run.
