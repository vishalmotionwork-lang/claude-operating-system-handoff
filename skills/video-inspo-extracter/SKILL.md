---
name: video-inspo-extracter
description: >-
  Extract inspiration from any video and lay it on a FigJam board. Two modes:
  (A) Edited-segment extraction — scene-detect a video, classify every shot as
  no-talking-head / talking-head+overlay / plain-talking-head, and pull every
  EDITED segment (b-roll, animation, screen-recordings, overlays) into clip files
  + a segregated FigJam grid. (B) Creator teardown — download, transcribe, write
  strategy analysis, cut story-beat clips, and build a teardown board. Use when
  the user wants to break down a video's editing/b-roll, extract reference footage,
  "get everything out of a video," study a creator's content, or build a teardown
  board. Triggers: "extract the edited parts", "all the b-roll", "video breakdown",
  "creator teardown", "inspo board", "/video-inspo-extracter".
---

# Video Inspo Extracter

Turn a video (usually a YouTube URL) into reusable inspiration on a FigJam board.
Two modes — pick by intent, or ask the user:

- **Mode A — Edited-segment extraction** ("pull every edited/b-roll/animation part",
  "get everything out of the video"). Output: clip files for each edited segment +
  a FigJam grid, segregated A (no talking head) / B (talking head + overlay).
- **Mode B — Creator teardown** ("break down this video", "what's the strategy",
  "position us the same"). Output: transcript + 2 analysis panels + story-beat clips
  on a board that mirrors a reference teardown.

Both modes share the download/transcribe/clip/paste plumbing. All scripts live in
`scripts/`; the FigJam board engines (figma_execute code) live in `reference/`.

---

## Prerequisites (check once)
- `yt-dlp`, `ffmpeg`, `ffprobe` (brew). `uvx` (for PySceneDetect + OpenCV, isolated).
- **macOS has no `timeout`** — never wrap commands in it. Long jobs: run backgrounded, poll.
- ffmpeg in a `while read` loop **must** use `-nostdin` or it eats the loop's stdin and skips items.
- **figma-console Desktop Bridge** must be connected for board work: `figma_get_status({probe:true})`;
  if not, tell the user to open Figma Desktop → a FigJam file → Plugins → Development →
  Figma Desktop Bridge → Run. (The official Figma desktop MCP can READ FigJam but not write nodes.)
- **Scripted `Cmd+V`** (auto-paste) needs the host to have macOS Accessibility permission. Test on
  one clip first (paste → confirm a new `MEDIA` node via the plugin). If blocked, fall back to
  "you paste, I position" (set clipboard, user presses Cmd+V).
- Mode B transcription uses `~/.claude/scripts/transcribe.sh` (Groq Whisper; key auto-read).

Work in a per-video folder, e.g. `~/Downloads/<slug>/`.

---

## MODE A — Edited-segment extraction

1. **Identify + download** (1080p is plenty; graphics classification + board don't need 4K):
   ```bash
   yt-dlp --print "%(title)s | %(duration>%H:%M:%S)s | %(width)sx%(height)s" "<URL>"
   yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]" -o "video.%(ext)s" "<URL>"
   ```

2. **Detect shots + contact sheets**:
   ```bash
   uvx --with opencv-python-headless --with numpy --from scenedetect \
     python3 scripts/detect_and_sheet.py video.mp4 27
   ```
   → `scenes.csv` + `sheets/sheet_NN.jpg`. Lower the threshold (~22) for very fast-cut edits.

3. **Classify by eye — THIS is the step automation can't do.** `Read` each `sheets/sheet_NN.jpg`
   and label every shot:
   - **A** = no talking head: b-roll, animation, motion-graphics, screen-recordings, charts,
     title cards, logos, **external/interview clips of other people**.
   - **B** = talking head WITH graphics/text/QR/overlay composited on top.
   - **C** = plain presenter talking to camera, nothing on top → **skip**.
   Face-detection alone fails here (B has a face too) — your vision IS the classifier.
   When unsure, lean KEEP (the goal is "get everything edited"). The presenter's plain shots are
   the only thing excluded; external people talking = b-roll = A. Write the result to `classes.txt`
   (one letter per shot in order, length == number of shots in `scenes.csv`).

4. **Plan**: `python3 scripts/plan_from_classes.py scenes.csv classes.txt`
   → `plan_per_shot.csv` (every kept shot) + `plan_merged.csv` (consecutive same-type merged into
   passages — the usual extraction granularity). Prints A/B/C counts + % of video that's edited.

5. **Extract clips**: `bash scripts/extract_clips.sh video.mp4 plan_merged.csv clips 720 23`
   → `clips/segNN_<A|B>_<stc>-<etc>.mp4` (timeline-named, ~small).

6. **Build the FigJam grid** — follow `reference/board-grid.md`:
   start `cors_server.py <dir>` (for labels) → PASS 1 build empty cells → PASS 2 `paste_batch.sh`
   in batches + PASS 3 idempotent id-order positioning → embed source on top → optionally SEGREGATE
   into A-block / B-block. Screenshot to verify each pass.

7. **Write `README.md`** (method + counts + file map). Stop the CORS server.

Granularity options to offer: merged-by-type (clean, recommended) · every-shot · merged-passages.

---

## MODE B — Creator teardown

1. **Download + transcribe**:
   ```bash
   yt-dlp -f "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b" -o "ep.%(ext)s" \
     --write-auto-subs --sub-langs "en.*" --convert-subs srt "<URL>"
   ~/.claude/scripts/transcribe.sh "<URL>"     # clean Groq transcript (no `timeout`)
   ```
   Auto-captions give free timestamps; the Groq pass gives clean punctuated text.

2. **Analyze** — write two panels in the user's plain-English voice (no marketing jargon):
   - `panel-A.md` — strategy/business breakdown (numbered, ends on the cliffhanger/insight).
   - `panel-B.md` — content-format teardown + "how we position the same" adaptation for the user.
   Cite sources. Don't invent numbers/names.

3. **Cut story-beat clips** with ffmpeg (`-nostdin`, `-ss start -t dur`) from the opening beats
   (preview/hook, intro+credentials, what they build, the idea, team) — mirror the reference board.

4. **Build the board** — `reference/board-teardown.md`: mirror the reference node style, fetch panel
   text + thumbnail via CORS, lay 2 panels + source block + labeled clip slots + connectors. Paste
   clips (set_clipboard + Cmd+V, one per slot) and the source URL embed. Optional inline full video:
   compress to ≤ ~35 MB / 360p first (FigJam import cap).

---

## Hard-won gotchas (don't relearn these)
- **The plugin cannot create video.** Get media in via OS clipboard file-paste (`set_clipboard.sh`)
  + `Cmd+V`. A pasted clip = `type:"MEDIA"`; a pasted URL = `type:"EMBED"`.
- **FigJam media import cap:** ~32 MB OK, ~66 MB fails. Keep clips small (720p clips, 360p full video).
- **Position media by node-id order** (== paste order == segment order). Re-running the position pass
  is idempotent and self-corrects drift. Don't match nodes by canvas position once media overlap slots.
- **Segregate by deleting+rebuilding slots/labels**, keeping media and re-deriving order from id-sort.
- **CORS on port 9230** (manifest-allowlisted) to feed label CSVs / thumbnails / panel text into
  figma_execute at zero context cost. Bind `""`, fetch `http://localhost:9230/...` (not 127.0.0.1).
- **`figma_take_screenshot` uses a REST token that expires** → use `figma_capture_screenshot` (plugin
  runtime) instead. Full-page caps at 1568px; pass a nodeId for detail.
- The **figjam-board PreToolUse hook** nags to use its kanban kit. These boards are video/connector/
  square layouts the kit can't make — its FIX-flow explicitly allows targeted figma_execute. Proceed.
- Build in a verified-empty zone; FigJam `createPage` throws (user moves the section to a page after).

## Outputs
A per-video folder with `video.mp4`, `scenes.csv`, `sheets/`, `classes.txt`, `plan_*.csv`,
`clips/segNN_*.mp4`, `README.md` (Mode A) and/or `*.transcript.clean.txt`, `panel-A/B.md`,
story-beat `clips/` (Mode B) — plus the FigJam board on the connected file.
