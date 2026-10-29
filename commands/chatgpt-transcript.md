---
description: Transcribe an audio/video file using ChatGPT's own voice-to-text (gpt-4o-transcribe) via your logged-in browser session. Chunks long audio, auto-recovers ASR loops, saves a timestamped .txt + .json next to the file.
---

# /chatgpt-transcript

## Purpose

Transcribe a local audio/video file with **ChatGPT's transcription model**
(`gpt-4o-transcribe`, the model behind ChatGPT voice) — using the user's
logged-in ChatGPT session, no API key or payment. Best when the user wants
ChatGPT-quality transcription (incl. Hindi/Gujarati/Hinglish code-switching).

For transcribing from URLs (YouTube/Instagram/TikTok) via Groq Whisper instead,
use `/transcript`.

## Usage

```
/chatgpt-transcript <path-to-audio-or-video> [more files…]
```

If no path is given, ask the user for the file path(s) (AskUserQuestion).

## Workflow

1. **Parse args** — collect file path(s) from `$ARGUMENTS`. Strip surrounding
   quotes. Skip anything that isn't an existing file (warn, continue).

2. **Run the helper, one file at a time** (serial — never parallel, to stay well
   under ChatGPT rate limits):

   ```bash
   ~/.claude/scripts/chatgpt_transcribe.sh "/abs/path/to/file.m4a"
   ```

   The helper handles everything: browser-session auth (auto-detects Brave →
   Chrome → Edge → Firefox), 3-min chunking, the ChatGPT transcribe endpoint,
   decoder-loop collapse, adaptive 1-min re-split of any looped/empty chunk, and
   writes `<name>.chatgpt.txt` (timestamped sections) + `<name>.chatgpt.json`
   next to the input. The transcript is also printed to stdout.

3. **Long files run in the background** — a 30-min file is ~10+ requests over
   several minutes. Launch with `run_in_background`, then wait for completion
   (e.g. an `until grep -q "\[saved:" <logfile>` Bash background wait), and
   report when done. Don't block the session polling.

4. **Surface results** — show the saved path(s) and a short content summary.
   Output is in the **native script** ChatGPT returns (Devanagari/Gujarati for
   Hindi/Gujarati; Latin for English). To romanize to Latin Hinglish, offer the
   Groq llama romanizer as a follow-up (it does not add ChatGPT requests).

## Options (pass through to the helper)

| flag | default | meaning |
|------|---------|---------|
| `--minutes N` | `3` | chunk length. ≤10 (endpoint max), but 10 loops — keep ≤3. |
| `--browser B` | `auto` | `brave`\|`chrome`\|`edge`\|`firefox`\|`auto` |
| `--delay S` | `4` | base seconds between requests (jitter added) |
| `--out DIR` | next to input | output directory |

## Notes / gotchas

- **Requires being logged into ChatGPT** in a supported browser. First run pops a
  macOS **Keychain prompt** ("…wants to use Brave/Chrome Safe Storage") — the user
  must click **Allow** so cookies can be decrypted.
- The endpoint accepts **mp3 only** (the helper transcodes for you); m4a/long
  chunks fail — handled internally.
- `gpt-4o-transcribe` **hallucinates repeat-loops** on long/multi-speaker audio;
  the helper detects (chars/sec spike) and re-transcribes those windows at 60s.
- **Rate-safe by design**: serial requests, jittered delays, one reused token,
  hard stop on HTTP 429. Keep it serial across multiple files too.
- This uses an undocumented internal endpoint on the user's own account — a ToS
  gray area for personal use. Don't run high-volume batches.
- First invocation auto-creates a venv at
  `~/.claude/scripts/.chatgpt-transcript-venv` (deps: browser_cookie3, curl_cffi);
  system deps: `ffmpeg`.
