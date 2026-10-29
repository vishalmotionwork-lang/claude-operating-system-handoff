# 06 — Lessons learned

The most reusable of 158 feedback rules, each written after a real correction. Seed your own `feedback_*.md` files with the ones that fit.

## Working with the user

- **Use AskUserQuestion for every question**, never a plain-text list of questions.
- **Finish the current task first** when a new request arrives mid-task, unless told otherwise.
- **Follow counts literally.** "11 agents individually" means 11 agents, not a bundled optimisation.
- **When told to redo or rebuild, don't argue** — ask what they want.
- **Answer the architecture question first.** If asked "does this need a rewrite? if not, just do it" — read the code, give the verdict, then act.
- **Enhance the user's draft**, don't replace it — keep their structure, voice and examples.
- **Pre-fill what you know.** Never hand over an empty template when the data exists.
- **Don't assume — ask.** When a brief is thin, ask specific questions instead of inventing depth.
- **Link, don't duplicate.** Match new items to existing records before creating new ones.
- **Plain English** in product and strategy docs — say what the thing does; no "engine/platform/OS" framing, no marketing speak.

## Deliverables

- **Deliver the interactive HTML itself**, opened in the browser. Screenshots are your verification evidence, not the deliverable.
- **Full-page detail views** with breadcrumb, back and prev/next — not side drawers — and show the reasoning behind every label.
- **Readable over dashboard** for long-form: one column, generous type.
- **One word, one meaning per screen.** A label that means two things two inches apart reads as a data bug.
- **Paths, not option catalogues** for advice: 3–5 ranked paths with steps plus the research behind them.
- **Build the whole thing, then design** when the content will be restructured anyway.
- **A template is a visual language**, not a container to force-fit new data into.
- **Every claim sourced;** small samples are observations, not findings.

## Engineering

- **Boot the real app and click through it** before calling anything done. Green tests and typecheck miss whole classes of bugs.
- **Fix the root cause** where a recurring bug comes from, not at each callsite.
- **Audit systematically, then fix in a batch** — don't whack-a-mole agent-written bugs one at a time.
- **Local first:** run it end to end locally (Docker, local Supabase) before any hosting talk.
- **Never `rm` with a wildcard** to clean up — delete only an explicit list of paths you created.
- **Never silently swallow errors;** log every skip reason in integration paths.
- **Permissions live on the server only.**
- **Central token maps:** N variants → one Record keyed by type, never literals at callsites.
- **Vercel:** deploy with the CLI; don't connect a GitHub repo without checking identity; the commit author email must be linked.
- **Commit before enqueue** — a worker can't see rows from a still-open transaction.
- **Research before overcomplicating** — when a setup spirals into workarounds, stop and find how others solved it.
- **Don't quit at "it's compiled/locked"** — pursue the technical path (decompile, extract) first. But never strip licence/DRM checks.

## Agents

- **Narrow scope:** disjoint files and explicit endpoint lists. Broad exploratory briefs stall.
- **Never brief a second agent on a file a running agent still owns** — lost-update race.
- **Waves** for big builds: foundation → screens → audits → fixers, 5–15 files per agent.
- **Fan out for research** across distinct angles, then reason over the results.

## Content

- **Remix, don't copy:** extract the framework of a viral piece and apply it to a different topic.
- **Never fabricate** client names, numbers, timelines or receipts in scripts — leave `[FILL]` markers.
- **Scripts are full spoken voice**, not beat skeletons.
- **Titles sell the outcome**, not the creator's identity.
- **Strategy top-down:** bandwidth → cadence counts → funnel → pillars → topics, each summing to its parent.
- **Light read beats a quota wait** — ship the board today with labelled light reads.

## Tool gotchas worth knowing

- YouTube embeds don't play from `file://` (Error 153 — no Referer). Serve on localhost.
- Instagram `/p/<code>/embed/` does play from `file://`.
- `yt-dlp --flat-playlist` returns no view counts on channel pages — fetch per-video metadata in parallel.
- Chrome `--print-to-pdf` ignores `counter-reset` on named `@page`s.
- FigJam: build only in verified-empty space; the bridge writes to whichever Figma file is focused — check the file name first.
- Inline `style.display` beats Tailwind responsive classes like `md:hidden`.
- Radix modals swallow toasts rendered outside them.
