#!/usr/bin/env python3
"""
synced_captions.py — word-synced, phrase-aware caption SRT generator.

Takes a local audio/video file OR a URL (Instagram, YouTube, TikTok, direct media),
transcribes it with Groq Whisper at word-level granularity, then groups the words
into short, *meaningful* caption chunks (default 2 words) where each chunk:
  - keeps grammatical units together (article+noun, verb+object, "to PayPal")
  - never dangles on a leading function word ("with", "a", "to", "and", "I"...)
  - is timed to its own words (start of first word -> end of last word)
  - never overlaps the previous caption (strictly monotonic timeline)

Punctuation is stripped from the displayed text by default, while preserving
decimals inside numbers (1.9), the % sign, and apostrophes in contractions
(I'm, I'll) so words don't turn into "Im"/"Ill".

Usage:
  synced_captions.py INPUT [--max-words N] [--out PATH] [--keep-punct]
                            [--model NAME] [--language CODE]

  INPUT        local file path OR http(s) URL
  --max-words  max words per caption chunk (default: 2)
  --out        output .srt path (default: alongside input / transcripts dir)
  --keep-punct keep original punctuation in caption text
  --model      Groq Whisper model (default: whisper-large-v3-turbo)
  --language   ISO-639-1 hint, e.g. en (optional, improves accuracy)

Env:
  GROQ_API_KEY   overrides the key auto-read from the creds file below.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

CREDS_FILE = os.path.expanduser(
    "~/.claude/projects/-Users-YOUR-USER/memory/groq-api-creds.md"
)
GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Words that must NOT be the last word of a caption — they "lead" into the next
# word, so we keep them attached to whatever follows. This is what makes the
# chunks read naturally instead of breaking mid-phrase.
TRAILING_AVOID = {
    # articles
    "a", "an", "the",
    # prepositions
    "of", "to", "in", "on", "at", "for", "with", "from", "by", "as", "into",
    "about", "over", "under", "than",
    # conjunctions
    "and", "or", "but", "so", "nor", "yet",
    # determiners / possessives
    "my", "your", "his", "her", "its", "our", "their", "this", "that",
    "these", "those",
    # subject pronouns (lead into a verb)
    "i", "you", "we", "they", "he", "she", "it",
    # misc leaders
    "no", "if", "is", "are", "was", "were", "be",
}


def die(msg, code=1):
    print(f"synced-captions: {msg}", file=sys.stderr)
    sys.exit(code)


def have(cmd):
    return subprocess.run(["which", cmd], capture_output=True).returncode == 0


def groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key
    if os.path.isfile(CREDS_FILE):
        m = re.search(r"gsk_[A-Za-z0-9]+", open(CREDS_FILE).read())
        if m:
            return m.group(0)
    die("no GROQ_API_KEY set and none found in creds file", 78)


def fetch_audio(inp, workdir):
    """Return a path to a local media file (download URL if needed)."""
    if re.match(r"^https?://", inp):
        if not have("yt-dlp"):
            die("missing dep: yt-dlp (brew install yt-dlp)", 69)
        out = os.path.join(workdir, "source.%(ext)s")
        r = subprocess.run(
            ["yt-dlp", "-f", "bestaudio/best", "-o", out, inp],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            die(f"yt-dlp failed:\n{r.stderr.strip()}", 70)
        files = [f for f in os.listdir(workdir) if f.startswith("source.")]
        if not files:
            die("yt-dlp produced no file", 70)
        return os.path.join(workdir, files[0])
    if not os.path.isfile(inp):
        die(f"file not found: {inp}", 66)
    return inp


def to_mp3(src, workdir):
    """Downsample to mono 16kHz mp3 so it fits Groq's 25MB upload limit."""
    if not have("ffmpeg"):
        die("missing dep: ffmpeg (brew install ffmpeg)", 69)
    mp3 = os.path.join(workdir, "audio.mp3")
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000",
         "-b:a", "64k", mp3, "-loglevel", "error"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        die(f"ffmpeg failed:\n{r.stderr.strip()}", 71)
    return mp3


def transcribe(mp3, key, model, language):
    """Call Groq Whisper, return the list of {word,start,end}."""
    cmd = [
        "curl", "-s", GROQ_URL,
        "-H", f"Authorization: Bearer {key}",
        "-F", f"file=@{mp3}",
        "-F", f"model={model}",
        "-F", "response_format=verbose_json",
        "-F", "timestamp_granularities[]=word",
    ]
    if language:
        cmd += ["-F", f"language={language}"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"curl failed:\n{r.stderr.strip()}", 72)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        die(f"unexpected API response:\n{r.stdout[:500]}", 73)
    if "error" in data:
        die(f"groq error: {data['error'].get('message', data['error'])}", 74)
    words = data.get("words")
    if not words:
        die("API returned no word-level timestamps", 75)
    return words


def norm(word):
    """Lowercase, strip punctuation — for the TRAILING_AVOID lookup only."""
    return re.sub(r"[^\w']", "", word).lower()


def group_words(words, max_words):
    """Greedy grouping into <=max_words chunks that don't end on a leader word."""
    groups, i, n = [], 0, len(words)
    while i < n:
        end = min(i + max_words, n)
        # shrink the chunk while its last word is a "leader" (but keep >=1 word)
        while end - 1 > i and norm(words[end - 1]["word"]) in TRAILING_AVOID:
            end -= 1
        groups.append((i, end - 1))
        i = end
    return groups


def clean_text(text):
    """Strip punctuation but keep decimals (1.9), %, and apostrophes."""
    text = re.sub(r"(?<!\d)\.(?!\d)", "", text)      # periods not between digits
    text = re.sub(r"[,!?;:\"“”…—–()\[\]]", "", text)  # other punctuation
    return text.strip()


def ts(t):
    ms = int(round(t * 1000))
    h, m = ms // 3600000, (ms % 3600000) // 60000
    s, f = (ms % 60000) // 1000, ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{f:03d}"


def build_srt(words, groups, keep_punct):
    out, prev_end = [], 0.0
    for n, (a, b) in enumerate(groups, 1):
        start, end = words[a]["start"], words[b]["end"]
        if start < prev_end:          # clamp overlaps -> monotonic
            start = prev_end
        if end <= start:
            end = start + 0.20
        prev_end = end
        text = " ".join(w["word"] for w in words[a:b + 1]).strip()
        if not keep_punct:
            text = clean_text(text)
        out.append(f"{n}\n{ts(start)} --> {ts(end)}\n{text}\n")
    return "\n".join(out) + "\n"


def default_out(inp):
    if re.match(r"^https?://", inp):
        from datetime import date  # only needed in URL branch
        d = os.path.expanduser(f"~/Downloads/transcripts/{date.today()}")
        os.makedirs(d, exist_ok=True)
        slug = re.sub(r"[^\w-]+", "-", inp.split("/")[-1] or "captions").strip("-")
        return os.path.join(d, f"{slug or 'captions'}-synced.srt")
    base = os.path.splitext(os.path.basename(inp))[0]
    return os.path.join(os.path.dirname(os.path.abspath(inp)), f"{base}-synced.srt")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--max-words", type=int, default=2)
    ap.add_argument("--out")
    ap.add_argument("--keep-punct", action="store_true")
    ap.add_argument("--model", default="whisper-large-v3-turbo")
    ap.add_argument("--language", default="")
    args = ap.parse_args()

    out_path = args.out or default_out(args.input)
    key = groq_key()

    with tempfile.TemporaryDirectory() as wd:
        media = fetch_audio(args.input, wd)
        mp3 = to_mp3(media, wd)
        words = transcribe(mp3, key, args.model, args.language)

    groups = group_words(words, args.max_words)
    srt = build_srt(words, groups, args.keep_punct)
    open(out_path, "w").write(srt)

    print(srt, end="")
    print(f"\n--- {len(groups)} captions saved: {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
