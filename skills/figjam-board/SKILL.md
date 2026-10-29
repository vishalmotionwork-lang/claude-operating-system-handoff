---
name: figjam-board
description: Build or fix rich FigJam boards reliably (roadmaps, kanban, living source-of-truth boards, competitive maps) via the figma-console MCP. Use when the user wants to create, populate, restructure, or repair a FigJam board. Provides a coordinate-safe place-and-verify engine + reusable kit that neutralizes FigJam's section/coordinate traps.
---

## What this is

A reliable engine for producing and repairing FigJam boards through `figma-console` (`figma_execute` + the FigJam helper tools). It exists because hand-placing nodes in FigJam is fragile — appending to a section displaces children, `absoluteBoundingBox` is stale right after reparenting, and you can't create pages. The kit (`figjam-kit.js`) bakes the fixes in and adds a verify pass so quality doesn't depend on eyeballing.

Use it for: roadmaps, kanban / living boards, competitive maps, workshop boards, any multi-card FigJam layout — and for **fixing** existing boards (overlaps, overflow, dead space, restructuring).

## Before anything: connect

1. `figma_get_status` with `probe:true`.
2. If not connected, tell the user: open **Figma Desktop** → a **FigJam** file → **Plugins → Development → Figma Desktop Bridge → Run**, wait ~3s. Plugin manifest: `~/.figma-console-mcp/plugin/manifest.json`.
3. Confirm `editorType:"figjam"` and note `currentFileName`. **Never build into a file/page that has unrelated work without isolating** — build in empty space and wrap in one section (see Safe Placement).

## CREATE flow

1. **Read the kit**: `~/.claude/skills/figjam-board/figjam-kit.js`. Paste its ENTIRE contents at the top of a single `figma_execute` call.
2. **Plan the layout on paper first** — zone list, sizes, x/y. Decide a column grid and stick to it. Boards read best stacked full-width with an explainer column on the right (see Conventions).
3. **Safe placement**: start with `const OX = clearOrigin(400);` and offset every zone's x by `OX`. This drops the board to the right of all existing content so you never clobber it.
4. **Build** below the kit using `zone()`, `card()`, `text()`, `kanban()`, `row()`. Tag cards with their zone name so verify can check them.
5. **Verify in the same call**: `const warnings = verify(); return { wrapperId: finish("Title  ▸ (move/duplicate this whole block)"), warnings };`
6. **Act on warnings** — OVERLAP / OUT-OF-ZONE / OVERFLOW? Adjust coords or sizes (bigger card, smaller font, shorter text) and re-run. Don't ship with warnings unless intentional.
7. **Screenshot** the wrapper in a follow-up call: `figma_capture_screenshot({ nodeId: wrapperId, scale: 1 })`. Eyeball alignment/spacing/clipping. Iterate ≤3×.
8. Tell the user where it is (file, page) and that the wrapper section can be right-clicked → **Move to page** (since `createPage` isn't available in FigJam).

### Minimal build skeleton (after pasting the kit)
```js
const OX = clearOrigin(400);
text(OX, -230, 2000, "My Board", 64, "Bold", T.ink);
const NS = zone("★  NORTH STAR", OX, 0, 2560, 250, T.zone.gold);
card(OX+30, 90, 1640, 140, "🎯 THE ONE GOAL\n[ … ]", T.white, "#E5B53A", 22, null, NS.name);
const WK = zone("▶  THIS WEEK", OX, 310, 2560, 780, T.zone.green);
kanban(OX, 310, 2560, WK.name, [
  {title:"📋 TO DO", headFill:"#DDE3EC", fill:T.status.todo[0], stroke:T.status.todo[1], cards:["Task A\n👤 Name  📅 Fri"]},
  {title:"🔨 IN PROGRESS (max 2/person)", headFill:"#FFE9A8", fill:T.status.wip[0], stroke:T.status.wip[1], cards:["Task B\n👤 Dev  📅 Wed"]},
  {title:"⛔ BLOCKED", headFill:"#F6C6C6", fill:T.status.blocked[0], stroke:T.status.blocked[1], cards:[]},
  {title:"✅ DONE", headFill:"#BFE6CC", fill:T.status.done[0], stroke:T.status.done[1], cards:[]}
]);
const warnings = verify();
return { wrapperId: finish("My Board  ▸ (move/duplicate this whole block)"), warnings };
```

## FIX flow (repair an existing board)

1. `figjam_get_board_contents` (optionally `nodeTypes:["SECTION"]` first) to map what's there + node ids + positions.
2. Diagnose: overlaps, text clipping, dead space in a wrapper, misalignment, missing zones.
3. Repair with targeted `figma_execute`:
   - **Reposition/resize** a node by id: `const n=figma.currentPage.findOne(x=>x.id==="<id>"); n.x=…; n.y=…; n.resize(w,h);`
   - **Dead space in a wrapper section** (content not filling it): this is almost always the stale-bbox or origin-add trap. Fix = detach children to page (`for(const k of [...W.children]) page.appendChild(k)`), `W.remove()`, then in a **separate call** re-measure and re-wrap (or paste the kit and call `finish()` after recording rects).
   - **Never** realign a wrapper by setting `W.x/W.y` — that drags its children. Detach → fix → reattach.
4. Re-screenshot to confirm.

## FigJam gotchas (the non-negotiables — see [[reference_figjam_section_coords]])

- `section.appendChild(node)` **adds the section's origin** to the child's coords. Build free on the page; let `finish()` reparent + convert (`n.x -= W.x`).
- `node.absoluteBoundingBox` is **stale ~1 tick after reparent**. Never size a wrapper from it mid-call — use recorded/intended coords, or measure in a fresh call.
- `figma.createPage()` **throws in FigJam**. Build on `currentPage` + one wrapper section.
- Setting `section.x/.y` **moves all children**. Resize edges or detach-fix-reattach instead.
- `figma_capture_screenshot` caps the longest side at 1568px — fine for review; for high-detail crops capture a sub-zone by its node id.

## Conventions (what a good board looks like)

- **Zones**, left→right / top→bottom: North Star → The Map (parts) → This Week (kanban) → Next/Backlog → Decisions + Archive → Parking Lot; explainer/legend in a right-hand column.
- **Card line format**: `Title\n👤 Owner   📅 Due   🔗 link`. Status by color: To Do gray, In Progress yellow, Blocked red, Done green (`T.status.*`).
- **One owner, one due date per card.** Keep text short — if `verify()` flags OVERFLOW, cut words or grow the card.
- **Wrapper name** ends with `▸ (move/duplicate this whole block)` so the user knows it's one unit.
- **Colors**: `figjam-kit.js` ships a light professional palette. For brand work , pull real tokens from the project's design system or Figma variables instead of the defaults — don't invent brand hexes.

## Files
- `figjam-kit.js` — the pasteable engine (tokens, zone/card/text/kanban/row, verify, finish). Read it and paste in full per build.
