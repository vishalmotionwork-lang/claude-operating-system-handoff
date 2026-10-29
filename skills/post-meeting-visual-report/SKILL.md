---
name: post-meeting-visual-report
description: Turn a meeting recording into a complete visual HTML report — transcribe it, work out what was actually discussed and what it connects to, build the team meeting-notes doc with numbered figures, and file it under meetings/YYYY-MM/<department>/. Use when the user runs /post-meeting-visual-report, points at a call recording, or asks for meeting notes, a meeting report, or a post-meeting doc.
---

# Post Meeting Visual Report

One command: **recording in → filed, rendered, cross-referenced HTML report out.**

The report is not a summary. It is the written record of the meeting *plus* everything you
worked out around it: how it connects to prior meetings, which numbers reconcile against the
strategy of record, what prior in-house work already covers something named on the call, and —
clearly separated — what you infer is going on but nobody said out loud.

---

## Run order

Do these in sequence. Each step catches a failure the next one would hide.

### 1 · Locate the recording

Argument may be a path, a partial filename, or nothing.
- Path given → use it.
- Nothing given → list the newest `Meet-*` / `*.m4a` / `*.mp3` in `~/Downloads` and ask which.
- Never guess between two candidates. Ask.

### 2 · Profile the audio BEFORE transcribing

**Do not skip this.** Recorders routinely start long before anyone speaks — 9-, 18-minute dead
heads are normal here, and they look exactly like a broken transcription.

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 FILE
ffmpeg -hide_banner -i FILE -af silencedetect=noise=-50dB:d=2 -f null /dev/null 2>&1 | grep silence_
```

`mean_volume: -91.0 dB` = digital silence, genuinely nothing there.
Record where real speech starts; it goes in the footer as provenance.

### 3 · Transcribe

```bash
~/.claude/scripts/chatgpt_transcribe.sh "/abs/path.mp3"
```

- **Serially.** Never two at once — rate limits. Multiple files → chain with `&&`.
- Long files → `run_in_background`, then wait on `until grep -q "\[saved" <log>`.
- **It resumes.** A `.chatgpt.progress.json` next to the audio means a previous run stalled;
  re-running picks up from the last completed chunk. Check `chunks recorded` vs expected
  (duration ÷ 3 min) before assuming it finished.

### 4 · Verify the transcript is complete

Chunks returning 5–10 chars ("Yeah.") are **silence, not failure** — confirm against step 2.
If a near-silent window shows real peaks (`max_volume` above about −20 dB), extract it,
normalise, and retry just that window:

```bash
ffmpeg -ss START -t LEN -i FILE -af loudnorm=I=-16:TP=-1.5 seg.mp3
~/.claude/scripts/chatgpt_transcribe.sh --minutes 1 seg.mp3
```

Only after that may you report a section as empty.

### 5 · Read the whole transcript

Read it end to end. Do not skim and do not summarise from the first chunks.

### 5a · Attribute speakers and repair the text — **do not skip**

The transcript arrives as **one undifferentiated block with no speaker labels**. Until you
recover who said what, you cannot tell an instruction from a question or a decision from a
suggestion — which is where every real insight lives.

Full method: **`references/speakers-and-repair.md`**. In short:

1. **Build the roster first** — from the filename, prior reports in `meetings/`, names spoken,
   and roles in memory. Note what each person should know and own.
2. **Attribute turns** using vocatives (*"Alex, aap ek kaam karna"*), role asymmetry, register,
   self-reference and question→answer pairing. Check consistency across the *whole* call — if
   one person both asks a beginner question and issues a strategic instruction, you're wrong.
3. **Tag every attribution** — `Confident` / `Probable` / `Unattributed`. Attribute quotes in the
   report **only at Confident**. Never invent a name; unnamed speakers stay unnamed and get asked
   about.
4. **Repair the text** with `assets/lexicon.md` + whole-conversation context. The same term is
   mangled the same way every time and is usually clear elsewhere in the call.

> **Repair recovers what was said. It never invents what might have been said.**
> `cloud code → Claude Code` is repair. Filling a silent gap with a plausible sentence is
> fabrication — mark it `[inaudible]` instead. Note material repairs in the footer.

**Append every new error you hit to `assets/lexicon.md`.** That file is the compounding asset
of this skill — it gets better every meeting.

Acoustic diarization is **not** available for these recordings (Meet exports are dual-mono;
measured L−R difference = −91 dB). Re-check per `speakers-and-repair.md` if the source changes,
and offer pyannote as an install only if the user asks for true diarization.

### 6 · Establish the facts you'll file under

| Needed | How |
|---|---|
| Date | From the filename / audio metadata |
| Participants | From the transcript — names spoken, people addressed |
| Department | From content → `scripting` / `editing` / `designing` / `founders` / `company` |
| Topic slug | What the meeting was actually about, 2–5 words |

**Never invent a participant.** If a name is never spoken, say so and ask. Same for the chair
of a large call. See "No assumptions about people" below.

### 7 · Reconcile and cross-reference — this is what makes it a report

Before writing a single block:

- **Numbers** → check every figure against `your canonical-numbers file`. If the
  call was vague ("about 120 posts") and the strategy of record resolves it (60 feed + 60
  trials), state the resolved version and cite it with a `.src` chip. Don't repeat the vagueness.
- **Named creators / companies** → verify spelling by web search. ASR mangles names badly
  (heard "Cleo Abraham" → **Cleo Abram**; "Lara Costa" → **Lara Acosta**; "Calway" → **Kallaway**;
  "Nicks" → **Nick Saraev**). Flag anything you couldn't confirm with a `<span class="tag drift">
  spelling to confirm</span>` — never quietly guess.
- **Prior in-house work** → check `~/.claude/projects/-Users-YOUR-USER/memory/projects/` and
  `~/Company Workspace/teardowns/` before treating a reference as new. Several named creators
  already have full teardowns. Point at them; don't rebuild.
- **Local assets** → `~/Company Workspace/yt-board-assets/manifest.json` has avatars, thumbnails
  and sub counts for tracked channels. Embed them with `.creators` cards when a reference matches.
- **Earlier meetings** → read the sibling reports in `meetings/`. If this call *changes* something
  an earlier report states, that is the single most valuable thing in the doc — see below.

### 8 · Write the report

Use `assets/report-template.html` — copy it, keep the CSS byte-identical, fill the body.
Block order and figure rules are in "Report anatomy" below.

### 9 · Verify it renders

```bash
SHELL_BIN=$(ls ~/Library/Caches/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell | head -1)
"$SHELL_BIN" --headless --disable-gpu --hide-scrollbars --screenshot=out.png \
  --window-size=1440,20000 --virtual-time-budget=8000 "file:///abs/path.html"
"$SHELL_BIN" --headless --disable-gpu --screenshot=m.png \
  --window-size=430,4000 --virtual-time-budget=5000 "file:///abs/path.html"
```

Read the screenshots. Then check mobile has no horizontal overflow — every pixel of the right
edge must be paper `(247,247,247)`:

```python
from PIL import Image
im=Image.open('m.png'); w,h=im.size; px=im.convert('RGB').load()
print(set(px[w-2,y] for y in range(150,h-100,150)))   # must be {(247,247,247)}
```

### 10 · File it

```
~/Company Workspace/meetings/YYYY-MM/<department>/YYYY-MM-DD-<topic-slug>--<people>.html
```

People = first names, lowercase, hyphenated, in speaking order. **Groups larger than ~4 get a
generic label** (`--team-sync`, `--all-hands`) with full attendance inside the doc.
Conventions live in `~/Company Workspace/meetings/README.md` — read it, keep it in sync.

Reports sit three levels below `Company Workspace/`, so embedded assets are
`../../../yt-board-assets/…`. Verify every path resolves after writing.

### 11 · Open it and report back

`open` the file. In your reply, lead with what the meeting *means*, not what you did.

---

## Report anatomy

Required order:

1. **Header** — eyebrow, title, one-paragraph sub, 4-cell props strip (audience, present, date + length, scope)
2. **Welcome callout** — how to read this; where it sits in the sequence of meetings
3. **Alert** (`.alert`, amber) — *only* when something supersedes an earlier report or a hard deadline was set
4. **Status legend** — define every pill used
5. **TOC** — grouped by lettered section
6. **Sections** — `.section-banner` + numbered `.topic` cards + numbered `.viz` figures
7. **Inference block** (`.infer-block`) — see below
8. **Open items** — what's unresolved, who owes what
9. **Footer** — source provenance: length, transcription note, where speech starts, what was cross-checked

### Rules that make it readable

- **Every figure is numbered** (`Figure N`) and carries a `.viz-note` saying *how to read it*.
  A figure without a takeaway line is decoration — delete it or explain it.
- **Full sentences in cards.** Never cryptic fragments.
- **Quote the call** where the phrasing matters. Mark quotes as quotes.
- **Receipts are `.src` chips** naming the source file.
- **Dark `.principle` blocks** carry the through-line — the one idea a section is really about.
  Two or three per report. They earn their weight; don't pad with them.
- **Find the pattern.** Every meeting has a spine — a repeated move, a tension, a correction.
  Name it in the welcome callout and build the sections around it. This is the difference
  between notes and a report.

### Calibrate the size to the meeting

A 12-minute standup does not deserve a 30-block report. Match the depth to the content or the
doc becomes padding — and padding is how a report stops being read.

| Call length | Blocks | Figures | Principle blocks |
|---|---|---|---|
| Under 10 min | 6–9 | 2–3 | 0–1 |
| 10–25 min | 10–15 | 3–6 | 1–2 |
| 25–45 min | 15–20 | 6–10 | 2–3 |
| 45 min+ | 20–30 | 10–20 | 3–4 |

Density beats length. If a section has nothing but restatement in it, cut the section.

### Gold-standard examples on disk

Read one before writing, matched to the shape of your meeting:

| Example | Why it's the reference |
|---|---|
| `meetings/2026-07/scripting/2026-07-28-strategy-lockin--alex-sam-priya.html` | The large one — 30 blocks, 19 figures, master reference table, embedded creator assets |
| `meetings/2026-07/scripting/2026-07-28-standup-ownership-swap--alex-priya-sam.html` | Supersession done right — amber alert + `.swap` figure |
| `meetings/2026-07/company/2026-07-24-sync-execution-status-blockers--team-sync.html` | Short status call — `.tbl` status board, `.roster`, tight |
| `meetings/2026-07/scripting/2026-07-27-craft-and-contentops--alex-sam.html` | `.build` worked example, `.ratio`, audit table |

### Picking a figure

| Shape of the idea | Component |
|---|---|
| Sequence, pipeline, gate | `.flow` (+ `.flow-back` for loops/fails) |
| Hierarchy, org, taxonomy | `.tree` |
| Before vs after, swap | `.swap` |
| This vs that, right vs wrong | `.split` |
| Headline numbers | `.stats` |
| Weighted comparison | `.bars` |
| Narrowing stages | `.funnel` |
| One core, many satellites | `.hub` |
| Ranked list | `.stack` |
| Chronology | `.timeline` |
| Status across many rows | `.tbl` + `.tag` |
| Requirement checklist | `.checks` |
| Stepped argument / worked example | `.build` |
| Attendance | `.roster` + `.chip` |
| Proportional split | `.ratio` |
| Reference creators w/ local images | `.creators` |
| 3 or 4 parallel things | `.cards3` / `.cards4` |

Wide components set `min-width`; `.viz` scrolls them on small screens and they stack under 820px.

---

## The inference block — "what we might be talking about"

The user explicitly wants interpretation, not just transcription. Deliver it **quarantined**,
never blended into the record.

Use `.infer-block` with paired columns: **what was said** → **what it likely means**.

```html
<div class="infer-block">
  <div class="infer-k">Reading between the lines — inference, not record</div>
  <div class="infer-row">
    <div><div class="infer-c">What was said</div>
      <div class="infer-t">"No update today, Gauri is on leave."</div></div>
    <div><div class="infer-c">What it likely means</div>
      <div class="infer-t">Scripting is a <strong>single point of failure</strong> — one
      person out and the department reports nothing. Consistent with the hiring push that
      same week. <span class="inf">inference</span></div></div>
  </div>
</div>
```

**Rules, non-negotiable:**

- Every inference is **visibly marked** — purple `.infer-block`, `.inf` chip, or a
  `<span class="status infer">Inference</span>` pill on the topic card.
- Every inference **names the evidence** that suggests it.
- Inference **never enters** the welcome callout, the props strip, the footer, or any
  `.src`-cited line. Those are record only.
- Hedge honestly: "likely", "reads as", "suggests" — not "is".
- If you're inferring something about a **person's** competence, intent or standing, be
  careful and fair. Describe the behaviour and its effect, not the character.

### No assumptions about people — different rule

Interpretation of *content* is wanted. Invention of *facts about people* is not.

- A name never spoken → **ask**. Never guess from context, and never pick a plausible name.
- Department genuinely ambiguous → **ask**.
- Who chaired a large call → if unclear, write "the chair could not be identified from the audio."
- **Pronouns**: ASR is unreliable on gender, especially in Hinglish, and often contradicts itself
  in one transcript. Use the person's name, or they/them. Never infer gender from a name.

---

## Supersession — the highest-value thing you can catch

Meetings contradict each other. Yesterday's owner is today's ex-owner. When this report changes
something an earlier one states:

1. Put an amber `.alert` directly under the welcome callout, headed **"Supersedes earlier notes"**.
2. Say plainly what changed and which report it overrides.
3. Show it as a `.swap` figure — old state on the left at reduced opacity, new state highlighted.
4. Note what *didn't* change; that's usually as informative as what did.

Someone reading the old doc must not act on stale information.

---

## Multiple recordings, one meeting

If several files cover one meeting (merged/split recordings), transcribe each, merge
chronologically, and file **one** report naming the source count in the footer.

---

## Checklist before you call it done

- [ ] Audio profiled; dead air identified and stated in the footer
- [ ] Every chunk accounted for — empty ones confirmed as genuine silence
- [ ] Transcript read end to end
- [ ] **Roster built before attributing anything**
- [ ] **Speakers attributed with a confidence tier; quotes attributed only at Confident**
- [ ] **Attribution consistent across the whole call — no role contradictions**
- [ ] **Lexicon applied; new errors appended to `assets/lexicon.md`**
- [ ] **`[inaudible]` used instead of invention; material repairs noted in the footer**
- [ ] Numbers reconciled against `canonical-numbers.md`, cited with `.src`
- [ ] Creator/company names verified; unconfirmed ones flagged, not guessed
- [ ] Prior in-house teardowns checked and linked
- [ ] Local assets embedded where a reference matches
- [ ] Earlier meeting reports read; supersession flagged if any
- [ ] Every figure numbered with a `.viz-note`
- [ ] Inference quarantined in `.infer-block` and marked
- [ ] No invented participants; unknowns asked about, not filled in
- [ ] Rendered at 1440px **and** 430px; screenshots read; no mobile overflow
- [ ] Asset paths resolve from the filed depth
- [ ] Filed to the right `YYYY-MM/<department>/`, named to convention
- [ ] Opened

---

## After the report: scripts discussed → ERP

When the meeting reviewed scripts or ideas (a scripting review, a strategist call), offer to run the **sprint-planner Flow G** afterwards. It maps every script to its ERP task (linking to existing ones, never duplicating), writes a full-context brief per piece, and links each brief into the task's References. The report's per-script cards are its input, so nothing has to be re-derived.

## Related

- `references/speakers-and-repair.md` — **speaker attribution + transcript repair (step 5a)**
- `references/pipeline.md` — transcription gotchas in depth
- `assets/lexicon.md` — the growing ASR-error glossary; **append to it every run**
- `assets/report-template.html` — the locked visual system
- `~/Company Workspace/meetings/README.md` — filing convention

A `PostToolUse` hook on `chatgpt_transcribe.sh` (`~/.claude/hooks/transcript-meeting-report.sh`)
fires whenever a transcription starts and reminds you to offer this report. If the user has
already asked for the report, don't re-ask — the hook is a safety net, not a second question.
- Memory: `reference_knowai_meeting_doc_format`, `feedback_meeting_report_filing`,
  `feedback_html_board_not_artifact`, `feedback_no_assumptions_ask_instead`
