---
description: Transcribe one or more audio/video URLs (Instagram, YouTube, TikTok, direct media) using Groq Whisper. Saves to ~/Downloads/transcripts/YYYY-MM-DD/ and prints to chat.
---

# /transcript

## Purpose

One-shot transcription pipeline. Hand it any URL with audio — Instagram reel, YouTube video, TikTok, or direct .mp3/.mp4 — and get a clean text transcript back, saved to disk and printed in the conversation.

## Usage

```
/transcript URL [URL ...]
```

Examples:
- `/transcript https://www.instagram.com/p/DWiRvV5ApoL/`
- `/transcript https://youtu.be/abc123 https://www.tiktok.com/@user/video/123`
- `/transcript` — if no args, ask the user to paste links (one per line or space-separated)

## Workflow

1. **Parse args** — split `$ARGUMENTS` on whitespace into a list of URLs. Strip surrounding quotes/punctuation. If empty, ask the user via AskUserQuestion: "Paste the URL(s) you want transcribed (space or newline separated)."

2. **Sanity-check URLs** — each entry must look like a URL (`http://` or `https://`). Reject anything else with a one-line warning, but continue with the rest.

3. **Run the helper** — call the bash helper in a single command, passing all URLs as args:

   ```bash
   ~/.claude/scripts/transcribe.sh URL1 URL2 URL3 ...
   ```

   The script handles: yt-dlp download → 25MB downsample if needed → Groq Whisper API → save `.mp3` + `.txt` to `~/Downloads/transcripts/<today>/` → print transcripts to stdout. Cached transcripts are reused (idempotent).

4. **Surface results** — the helper prints each transcript prefixed by `=== <slug> ===`. Relay them to the user as-is, but tighten formatting: render each transcript under a markdown heading with the original URL. End with the output directory path so the user can grab the files.

5. **Errors** — the helper exits non-zero if any URL failed (private post, geo-block, expired). Tell the user which slugs failed and why (look at stderr in the captured output). Don't retry automatically — ask if they want to use cookies (`yt-dlp --cookies-from-browser`) or paste a fresh link.

## Output format

For each URL, output:

```
### <platform> — <slug>
<original URL>

<transcript text>
```

Then a final line:

```
Saved to: ~/Downloads/transcripts/<YYYY-MM-DD>/
```

If a single URL is given, skip the heading wrapper and just show the transcript inline.

## Notes

- Groq key is read from the `GROQ_API_KEY` env var.
- Default model: `whisper-large-v3` (most accurate; `-turbo` garbles Hindi/Hinglish — it translates/mangles code-switched speech). For faster transcription of clean English, override with `GROQ_WHISPER_MODEL=whisper-large-v3-turbo`.
- Files larger than 25MB are auto-downsampled to mono 16kHz mp3 before upload.
- Re-running on the same URL reuses the cached `.txt` — no double charging.
- Instagram refuses anonymous yt-dlp fetches ("empty media response"), so the helper falls back to browser cookies automatically: plain fetch first, then `--cookies-from-browser` across brave → chrome → safari → firefox. Override the order with `YTDLP_COOKIES_BROWSER=chrome` (comma/space separated). If every attempt fails, the last 3 lines of yt-dlp stderr are printed — usually a genuinely private post or an expired link.
