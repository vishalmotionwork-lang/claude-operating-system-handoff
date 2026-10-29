# Speaker attribution & transcript repair

`gpt-4o-transcribe` returns **one undifferentiated block of text per chunk**. No speaker labels,
no turn boundaries. Everything below exists to recover that structure, because without it you
cannot tell an instruction from a question, or a decision from a suggestion — and that is where
the insight lives.

---

## Why acoustic diarization isn't available (measured, not assumed)

| Option | Status |
|---|---|
| `whisper-cli --diarize` | **Useless here.** Needs speakers on separate stereo channels. |
| `whisper-cli --tinydiarize` | **Useless here.** English-only tdrz model; calls are Hinglish. |
| pyannote / whisperX | Not installed. Needs HF token + gated model acceptance. |

The Meet recordings are **dual-mono** — verified by measuring the L−R difference:

```bash
ffmpeg -ss 1200 -t 30 -i FILE -af "pan=mono|c0=0.5*c0-0.5*c1,volumedetect" -f null /dev/null 2>&1 | grep mean_volume
# → mean_volume: -91.0 dB   (digital silence = channels are bit-identical)
```

Re-run that check on any new source. If it ever returns real signal, the channels genuinely
differ and `--diarize` becomes worth trying. **If the user wants true diarization, offer to
install pyannote — don't do it unprompted.**

So: attribute by **content**, and be honest about confidence.

---

## Pass 1 — Build the roster before attributing anything

Assemble the cast first, from strongest evidence to weakest:

1. **Meeting title / filename** — `Meet-Discussion-Saurabh-Singh` names a participant outright.
2. **Prior reports in `meetings/`** — a meeting series has a stable cast.
3. **Names spoken in the transcript** — direct address, roll-call, third-person mentions.
4. **Roles from memory** — `memory/projects/`, department docs.

Write the roster down before you attribute a single line. Mark each person with what you expect
them to know and do — that becomes your attribution prior.

---

## Pass 2 — Attribute turns

Read the **whole** transcript first. Attribution is a global constraint-satisfaction problem,
not a line-by-line one — a name dropped at minute 40 often resolves speakers at minute 3.

Signals, most reliable first:

| Signal | Example seen in real calls | What it tells you |
|---|---|---|
| **Vocative** | *"Alex, aap ek kaam karna…"* | The **other** person is Alex; the speaker is not |
| **Roll-call** | *"Alex Mani has not joined, Sam has joined"* | Chair + attendance in one line |
| **Role asymmetry** | One explains the strategy, the other asks what a pillar is | Lead vs new joiner |
| **Register** | *"I need scripts from tomorrow"* vs *"mereko clarity chahiye"* | Instructor vs reporter |
| **Self-reference** | *"I'll give you the complete doc"* | Owner of the deliverable |
| **Knowledge boundary** | Only one person knows the ContentOps MCP exists | Identifies the builder |
| **Question→answer pairing** | *"Aapke paas kitne angles hain?"* → list follows | Turn boundary |

Then **check consistency across the whole call.** If your attribution makes one person both ask
a beginner question and issue a strategic instruction, it's wrong — revise.

### Confidence tiers — always assign one

| Tier | Meaning | How to use it |
|---|---|---|
| **Confident** | Named, or unambiguous from role + vocatives | Attribute quotes directly |
| **Probable** | Consistent with role but never named | Attribute with *"appears to be"* / mark `.inf` |
| **Unattributed** | Can't tell | Quote without a name. Say so if it matters. |

**Never invent a name.** A speaker who is never named stays unnamed — ask the user, exactly as
with participants. If the chair of a large call can't be identified, write
*"the chair could not be identified from the audio."*

### Recording the result

Speaker attribution is **working context for better insight**, not a claim of record.

- Use it to decide *who owns* an action, *who decided* vs *who suggested*, *who was corrected*.
- In the report, attribute a quote only at **Confident**.
- At **Probable**, write *"the freelancer's side"*, or mark it `.inf`.
- Optionally include a `.roster` figure listing cast + role + confidence.

---

## Pass 3 — Repair the transcript using whole-conversation context

ASR fails *systematically*, not randomly. The same term is mangled the same way every time — and
usually appears correctly somewhere else in the same call. Exploit that.

### The method

1. **Apply the project lexicon** — `assets/lexicon.md`. Known, recurring substitutions.
2. **Resolve internally.** A term garbled at 12:00 is often clear at 41:00. Prefer the clearest
   occurrence and normalise the rest.
3. **Resolve numerically.** Reconcile any number against `canonical-numbers.md` rather than
   trusting fast speech.
4. **Resolve by search.** Proper nouns get verified externally (see lexicon). Flag what you
   can't confirm.
5. **Mark true gaps.** Genuinely unintelligible audio becomes `[inaudible]`.

### The hard rule

> **Repair means recovering what was said. It never means inventing what might have been said.**

Correcting "cloud code" → "Claude Code" is repair: the referent is certain from context.
Filling a silent gap with a plausible sentence is fabrication. If you cannot recover it, mark it.

When a repair changes meaning materially — a number, a name, a decision — note it in the report
footer so the reader can audit you.

### Worked examples from real calls

| Heard | Actual | How it was resolved |
|---|---|---|
| *"tofu, mofu, gofu"* | TOFU / MOFU / **BOFU** | Funnel model in `canonical-numbers.md` |
| *"cloud ka framework"* | **Claude** | Whole call is about Claude Skills/MCP |
| *"cloud ops"* → later *"content ops"* | **ContentOps** | Same call contains the clean form |
| *"Cleo Abraham"* | **Cleo Abram** | Web search — "Huge If True", matches description |
| *"120 posts a month"* | 60 feed + 60 trials | `canonical-numbers.md §1` |
| *"and so on"* (5th pillar) | **Client / Lead** | `canonical-numbers.md §2` |
| *"SCP"* | **MCP** | Context: model context protocol |

---

## Pass 4 — Make sense of it

Only after roster, attribution and repair:

- **Find the spine.** Every meeting has one — a repeated move, a tension, a correction. Name it.
- **Separate decision from discussion.** Who *decided*, versus who *floated*?
- **Track ownership.** Every action item needs an owner; attribution is how you find them.
- **Diff against prior meetings.** Ownership swaps and reversals are the highest-value catch.
- **Then infer** — quarantined in `.infer-block`, per SKILL.md.

---

## Quality gate

- [ ] Roster built before attribution
- [ ] Whole transcript read before assigning any speaker
- [ ] Attribution consistent end-to-end (no role contradictions)
- [ ] Every attribution carries a confidence tier
- [ ] Quotes attributed only at **Confident**
- [ ] Lexicon applied; new errors added back to it
- [ ] Numbers reconciled against canonical sources
- [ ] Proper nouns verified; unconfirmed flagged
- [ ] `[inaudible]` used instead of invention
- [ ] Material repairs noted in the footer
- [ ] Nobody named who was never named on the call
