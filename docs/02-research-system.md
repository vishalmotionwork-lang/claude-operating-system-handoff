# 02 — The research system

## Source order (before building or claiming anything)

From `rules/common/development-workflow.md`:

1. **GitHub first** — `gh search repos` / `gh search code` for existing implementations.
2. **Library docs second** — Context7 (`/docs`, `docs-lookup` agent) or the vendor's own docs.
3. **Web third** — Firecrawl (`firecrawl-search`, `firecrawl-scrape`) or Exa for broader discovery; `agent-reach` for platform-specific reads (X, Reddit, YouTube, LinkedIn, Instagram, Bilibili…).
4. **Package registries** — npm / PyPI before writing utility code.

For a strategy or research ask, **fan out many agents across distinct angles** (marketing teardowns, competitors, data), then **reason** over what comes back — don't dump raw findings. One agent per angle, each with a narrow brief and disjoint output files.

## Where research is stored

| What | Where |
|---|---|
| A loaded source (video, PDF, post, call) | `memory/sources/<prefix>-<id>.md` + a row in `sources/INDEX.md` (load date, original path/URL) |
| Prefixes | `yt-<id>` · `pdf-<slug>` · `ig-<id>` · `src-<slug>` |
| Research for one project | `memory/projects/<name>/RESEARCH/` (Tier 3 — loaded only when needed) |
| Big outputs (boards, video, data) | The project's own folder on disk — **never** in memory |
| Reusable method learned along the way | `reference_<method>.md` (e.g. "SaaS tech-stack teardown method") |

Check `INDEX.md` before loading a source again.

## Citation rule

Every content output cites its source and location: `[Source: "Video Title" @ MM:SS]`, `[Source: "doc.pdf" p.3]`, `[Source: @handle, post YYYY-MM-DD]`, and ends with a `Sources:` section. Analysis covers **Hook · Structure · CTA · Engagement** (`rules/common/content-creation.md`).

## Honesty rules for findings

- **A sample is not a finding.** State coverage, bias and blind spots before claiming a pattern.
- **Fresh data only** when the user is dictating new strategy — don't pull old memory in unless asked.
- **Don't fabricate depth.** When a brief is thin, ask specific questions instead of generalising from training data.
- **Two honest tiers beat one deep layer** — a large library with a light read plus a smaller set with a deep read, labelled as such, beats waiting for everything to be deep.

## Teardown pipelines (the main research product)

| Pipeline | Input → output |
|---|---|
| **Creator reverse-engineer** (`/creator-reverse-engineer`, public MIT repo) | Instagram handle → every post fetched, transcribed, scene-cut → content formula + money machine → self-contained HTML with a replication plan |
| **YouTube channel teardown** | Channel → `yt-dlp` metadata (per-video, view counts in parallel) → transcripts → per-video type + "why it worked" → interactive board |
| **Company GTM teardown** | Company → site, pricing, socials, founders' posts → board · pipeline · playbook |
| **SaaS tech-stack teardown** | Read-only: CSP headers + logged-in network crawl + JS bundles + vendor OSS repos |
| **SaaS UI-flow board** | Read-only guard, URL params → `flows.py` → FigJam lanes + zip |
| **Electron app static teardown** | asar + source maps + headless UI render — never launch the app |
| **Video style decoder** (`/video-style-decoder`) | An edited video → a repeatable style system an editor can apply to a new topic |
| **Video inspo extracter** (`/video-inspo-extracter`) | A video → scene-detected, classified b-roll clips laid on a FigJam grid |

Rules for teardown deliverables: one page per platform; every video playable in place with its transcript and breakdown card; accounts drawn as real platform profile cards with avatars saved locally; explore each dataset for its own patterns instead of forcing a fixed template.

**Light read when a deep read is quota-bound:** scene cuts/min (ffmpeg) + macOS Vision OCR on 9 frames + a 3×2 frame grid classified by Sonnet via `claude -p --model sonnet`, 12 videos per call. Mark those results as light.

## Transcription stack

| Need | Tool |
|---|---|
| URL (IG/YouTube/TikTok) quick transcript | `/transcript` → Groq Whisper (`GROQ_API_KEY`) |
| Hinglish / long calls / best quality | `/chatgpt-transcript` → ChatGPT's `gpt-4o-transcribe` via the logged-in browser session; chunks long audio, recovers ASR loops |
| Word-synced reel captions | `/synced-captions` → SRT, 2 words per line, phrase-aware |
| YouTube captions only | `scripts/youtube_transcript.py` |

Never install local Whisper (mlx / whisper.cpp) — too slow on this hardware, and the cloud routes are better.
