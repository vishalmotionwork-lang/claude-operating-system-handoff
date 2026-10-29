# style-system.template.html — data contract

The template is **data-driven**: all CSS + layout + render code are fixed; you only
replace the `DATA` block in the `<script>`. Clone the template into the working folder
as `style-system.html`, then fill these arrays. The reader works offline (file://) with
no dependencies — clips load from the relative `clips/` folder.

Keep the brand-tinted palette in `:root` matched to the video being decoded when it's
cheap to do (it makes the breakdown feel designed, not generic). Default palette = warm
cream + terracotta.

```js
SCRIPT  = [ [t_sec, "voice-over line"], ... ]            // the spine; one row per VO segment
FP      = [ ["fingerprint title", "1–2 sentence why"], ... ]   // 6 cards: the read-in-3-seconds traits
RULES   = [ ["when the line is X", "put Y on screen", "why"], ... ]   // topic-FREE trigger→treatment
MOVES   = [ [ "NN", "clipfile.mp4", "M:SS", "pres"|"proof",
              "move title",
              "what it is", "when to reach for it",
              "how it's built (timing/logic, editor-agnostic — NO software keyframes)",
              "why it works",
              "swap-for / never-reuse note" ], ... ]      // one per visual move; clip sits beside it
STATS   = [ ["big", "label"], ... ]                       // 4 pace headline numbers
PACE    = [ "html bullet about rhythm", ... ]
TL      = [ ["M:SS", "p"|"r", "voice / on-screen", "the move carrying it"], ... ]  // full beat timeline
WS      = [ ["beat name", "NEW-topic VO line", ["→ move on this beat", ...]], ... ] // worked transfer example
NOREUSE = [ ["prop THIS video used (burned)", "fresh prop the same move takes next time"], ... ]
CHECK   = [ "yes/no self-check question (may contain <b>…</b>)", ... ]
```

## Rules for filling it (do not skip)
- **MOVES "how" is editor-agnostic** — timing, sequence, placement, sync. No After Effects /
  Premiere keyframe recipes (that was the user's chosen depth: editing logic + timing only).
- **Every MOVE needs a `swap-for` note** and the whole `NOREUSE` table must be filled. This is
  the anti-repetition contract — the user's #1 requirement is that the editor builds NEW visuals
  for new videos, never recycles these. The grammar is the asset; the props are disposable.
- **RULES must be topic-free.** "Line names a company → drop its logo", never "say Stripe → Stripe logo".
- **WS (apply-it) must be a genuinely different topic**, not a word-swap of the source (see the
  `remix_not_copy` rule). It proves the grammar transfers and forces fresh props.
- Plain English throughout — no marketing-jargon framing ("engine/platform/pillars/loop/brain").
