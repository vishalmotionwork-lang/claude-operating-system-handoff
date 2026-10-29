# Board engine — creator TEARDOWN (Mode B)

A teardown board for ONE video: two analysis panels (strategy + "how we position as same"),
a source block (YouTube embed + direct full video), and a row of labeled story-beat clips with
connectors fanning from the source. Mirror an existing reference board's exact node style rather
than the figjam-kit card style.

## Reference node style (match whatever board you're extending)
White `SHAPE_WITH_TEXT` shapeType `SQUARE`, fill `#FFFFFF`, stroke `#757575` weight 4, cornerRadius 6.
Panel titles Inter Bold 48 `#1E1E1E`. Clip labels Inter Medium 30–32. Body text Inter Regular ~14.
Inspect the reference with a quick figma_execute that reads `.fills/.strokes/.fontName/.fontSize`.

## Build (one figma_execute) — fetch long text + thumbnail via CORS (zero context cost)
Write the two analysis panels to `panel-A.md` / `panel-B.md`, the thumbnail to `thumb.jpg`, serve
with `cors_server.py`, then:
```js
const page=figma.currentPage;
await Promise.all(["Regular","Medium","Bold"].map(s=>figma.loadFontAsync({family:"Inter",style:s})));
const solid=h=>{h=h.replace('#','');return[{type:"SOLID",color:{r:parseInt(h.slice(0,2),16)/255,g:parseInt(h.slice(2,4),16)/255,b:parseInt(h.slice(4,6),16)/255}}];};
const sq=(x,y,w,h)=>{const s=figma.createShapeWithText();s.shapeType="SQUARE";page.appendChild(s);s.resize(w,h);s.x=x;s.y=y;s.fills=solid("#FFFFFF");s.strokes=solid("#757575");s.strokeWeight=4;s.cornerRadius=6;s.text.characters="";return s;};
const txt=(x,y,w,str,sz,st)=>{const t=figma.createText();page.appendChild(t);t.fontName={family:"Inter",style:st};t.fontSize=sz;t.textAutoResize="HEIGHT";t.characters=str;t.resize(w,t.height);t.x=x;t.y=y;t.fills=solid("#1E1E1E");return t;};
const clean=md=>md.replace(/```/g,'').replace(/^#{1,6}\s*/gm,'').replace(/\*\*(.+?)\*\*/g,'$1').replace(/^\s*-\s+/gm,'•  ').replace(/^\s*>\s?/gm,'').replace(/\n{3,}/g,'\n\n').trim();
const A=clean(await(await fetch("http://localhost:9230/panel-A.md")).text());
const B=clean(await(await fetch("http://localhost:9230/panel-B.md")).text());
let thumbHash=null; try{const ab=await(await fetch("http://localhost:9230/thumb.jpg")).arrayBuffer();thumbHash=figma.createImage(new Uint8Array(ab)).hash;}catch(e){}
// LEFT panel (strategy): build card behind, size to text. RIGHT panel (position) same, offset right.
// Source: title + thumbnail square (image fill) centered over the clip row.
// 5 clip slots (633x408) in a row + Medium-32 labels below + connectors source->each clip.
// (see the Mode-B walkthrough in SKILL.md for the full coordinate math)
```

## Video into the teardown board
- **Story-beat clips** (5 cuts of the opening beats): cut with ffmpeg, paste via `set_clipboard.sh`
  then scripted `Cmd+V` (or have the user Cmd+V), detect the new `MEDIA` node, resize ~577×325 and
  center it in its 633×408 slot. One at a time so each maps to the right slot.
- **Source link**: `paste_url_embed.sh <url>` → position the `EMBED` widget above the center.
- **Direct full video** (optional, playable inline): FigJam media import is capped — **32 MB / 360p
  imported OK, 66 MB / 480p FAILED ("Files failed to import")**. Compress the full episode to
  ≤ ~35 MB (`scale=-2:360 -crf 33 -b:a 64k`) before pasting. The embed is the reliable full-length link.

## Story beats to isolate (typical creator vlog)
preview/hook · intro+credentials · what they're building · how they got the idea · team assembly.
Mirror whatever beat set the reference board used.
