# Transcription pipeline — the gotchas, in depth

Every item here cost a real debugging cycle. Read before concluding a transcription failed.

## 1. Dead air at the head of recordings

The recorder starts before anyone speaks. Observed repeatedly:

| Recording | Length | Speech starts |
|---|---|---|
| Content team call, 28 Jul | 28.0 min | **18:00** |
| Strategy lock-in, 28 Jul | 68.9 min | **09:00** |
| YouTube plan, 21 Jul | 22.7 min | **03:00** |

Chunks over dead air return `"Yeah."` (5 chars). That is **not** a failure — the model is
hallucinating a filler token over silence.

**Always profile before diagnosing:**

```bash
# per-segment levels
for s in 0 180 360 540 720 900; do
  echo -n "${s}s: "
  ffmpeg -hide_banner -ss $s -t 180 -i FILE -af volumedetect -f null /dev/null 2>&1 \
    | grep -E "mean_volume|max_volume" | tr '\n' ' '; echo
done
```

- `mean_volume: -91.0 dB` **and** `max_volume: -91.0 dB` → digital silence. Nothing is there.
- `mean_volume: -43 dB` but `max_volume: -5 dB` → mostly silence with real peaks. **Investigate.**

Then locate the exact islands:

```bash
ffmpeg -hide_banner -t 1080 -i FILE -af silencedetect=noise=-50dB:d=2 -f null /dev/null 2>&1 \
  | grep silence_
```

## 2. Recovering faint islands

If a window has peaks, don't write it off. Extract, normalise, retry:

```bash
ffmpeg -hide_banner -loglevel error -ss 524 -t 15 -i FILE \
  -af "loudnorm=I=-16:TP=-1.5" -ar 44100 seg-a.mp3
~/.claude/scripts/chatgpt_transcribe.sh --minutes 1 seg-a.mp3
```

Only report a section as empty after this returns nothing. (In practice these have been
join chimes and a single "Yes." — but verify, don't assume.)

## 3. Resume after a stall

`<name>.chatgpt.progress.json` next to the audio = a previous run stalled partway.
Re-running the script **resumes from cache** — it prints `resuming (N cached)`.

Inspect before re-running:

```bash
python3 -c "
import json; d=json.load(open('FILE.chatgpt.progress.json'))
ch=d['chunks']; print('duration', d['duration_sec']/60, 'min')
print('chunks:', len(ch), 'expected:', round(d['duration_sec']/180+0.5))
for c in ch: print(c.get('start'), c.get('end'), len(c.get('text') or ''))
"
```

A 69-minute file stalled at 13 of 23 chunks once. The `.txt` was **absent** because the run
never completed — the progress file is the only evidence the work exists. Don't restart from zero.

## 4. Rate limits

- **One transcription at a time.** Chain with `&&`, never `&` or parallel tool calls.
- The helper already adds jittered delays and stops hard on HTTP 429.
- Long jobs → `run_in_background`, then block on the log:

```bash
until grep -q "\[saved" LOGFILE 2>/dev/null; do sleep 10; done
```

## 5. Expected throughput

3-minute chunks, ~6–9 s each. Roughly: **23 chunks ≈ 3.5 min wall clock.**
A 69-minute recording is ~4 minutes of transcription, not 40.

## 6. Language

Output is in the **native script** — Devanagari/Gujarati for Hindi/Gujarati, Latin for English.
Hinglish calls come back mixed, which is fine; quote them as-is and translate inline in the
report when the meaning matters.

**Do not trust ASR on:**
- **Proper nouns** — verify every creator/company name by search
- **Gendered pronouns** — routinely inconsistent within one transcript; use names or they/them
- **Numbers spoken quickly** — reconcile against `canonical-numbers.md`

## 7. Output locations

```
<name>.chatgpt.txt            timestamped sections, human-readable
<name>.chatgpt.json           structured, per-chunk
<name>.chatgpt.progress.json  resume state (only while incomplete)
```

Transcripts stay in `~/Downloads`. They are **not** copied into `meetings/` — the report cites
them, the footer records provenance.
