# Board engine — edited-segment GRID (Mode A)

All board work goes through the **figma-console** MCP (`figma_execute` + `figma_capture_screenshot`).
Connect first: `figma_get_status({probe:true})` → if not connected, tell the user to open
**Figma Desktop → a FigJam file → Plugins → Development → Figma Desktop Bridge → Run**.
Build in a CLEAR zone (scan existing nodes, offset below/right of everything). FigJam `createPage`
throws — build on `currentPage`; the user can right-click the result → Move to page.

The grid is **65-ish small video cells in timeline order**, colored A=teal / B=amber, with the
source-video embed pinned on top. Three figma_execute passes + one scripted-paste loop.

---

## PASS 1 — build empty cells (slots + labels), fetch labels via CORS
Run `cors_server.py <dir>` first so the plan CSV is fetchable.

```js
const page=figma.currentPage;
await Promise.all(["Regular","Medium","Bold"].map(s=>figma.loadFontAsync({family:"Inter",style:s})));
const solid=h=>{h=h.replace('#','');return[{type:"SOLID",color:{r:parseInt(h.slice(0,2),16)/255,g:parseInt(h.slice(2,4),16)/255,b:parseInt(h.slice(4,6),16)/255}}];};
const csv=await(await fetch("http://localhost:9230/plan_merged.csv")).text();
const segs=csv.trim().split("\n").slice(1).map(l=>{const c=l.split(",");return{seg:+c[0],cls:c[1],stc:c[5],etc:c[6],dur:Math.round(+c[4])};});
const OX=-1664, OY=2600, cols=8, cw=360, ch=203, gx=60, lh=66, gy=72, px=cw+gx, py=ch+lh+gy;
const slot=(x,y,stroke)=>{const s=figma.createShapeWithText();s.shapeType="SQUARE";page.appendChild(s);s.resize(cw,ch);s.x=x;s.y=y;s.fills=solid("#F2F4F7");s.strokes=solid(stroke);s.strokeWeight=3;s.cornerRadius=6;s.text.characters="";return s;};
const txt=(x,y,str,sz,st,col)=>{const t=figma.createText();page.appendChild(t);t.fontName={family:"Inter",style:st};t.fontSize=sz;t.textAutoResize="HEIGHT";t.characters=str;t.resize(cw,t.height);t.x=x;t.y=y;t.fills=solid(col);return t;};
segs.forEach((s,i)=>{const col=i%cols,row=(i/cols)|0,x=OX+col*px,y=OY+row*py;
  const stroke=s.cls==="B"?"#E0A43A":"#2BB0A6";
  slot(x,y,stroke);
  txt(x,y+ch+8,`seg${String(s.seg).padStart(2,'0')}  ·  ${s.cls}  ·  ${s.stc}–${s.etc}  ·  ${s.dur}s`,16,"Medium",s.cls==="B"?"#9A6B12":"#1A6E68");});
return {cells:segs.length};
```

## PASS 2 — auto-paste all clips (scripted Cmd+V), no manual clicking
The plugin CANNOT create video. Paste at OS level. Clips are named segNN_… so `ls|sort` = timeline order.
Run in batches of ~16 (recoverable if a paste is dropped):
```bash
bash scripts/paste_batch.sh <clipsdir> 0 16     # then 16,16 / 32,16 / 48,16 ...
```
After each batch, run PASS 3 (idempotent) to position whatever has landed.

## PASS 3 — position pasted media into cells by id order (idempotent, self-correcting)
Pasted videos arrive as `type:"MEDIA"`. Their node-id order == paste order == segment order.
Re-running positions ALL of them by rank, so a re-run fixes any drift. Exclude media from OTHER
boards on the page.
```js
const KNOWN=new Set([/* media ids of unrelated boards on this page */]);
const media=figma.currentPage.children.filter(n=>n.type==="MEDIA"&&!KNOWN.has(n.id))
  .sort((a,b)=>parseInt(a.id.split(":")[1])-parseInt(b.id.split(":")[1]));
const OX=-1664,OY=2600,px=420,py=341,cw=360,ch=203,cols=8;
media.forEach((m,k)=>{const x=OX+(k%cols)*px,y=OY+((k/cols)|0)*py;m.resize(cw,ch);m.x=x;m.y=y;});
return {placed:media.length};
```
NOTE px/py here (420/341) = cw+gx / ch+lh+gy from PASS 1. Keep them in sync.

## Embed the source video on top
```bash
bash scripts/paste_url_embed.sh "https://www.youtube.com/watch?v=ID"
```
Then place it (find the new `type:"EMBED"`, exclude other boards' embeds):
```js
const e=figma.currentPage.children.filter(n=>n.type==="EMBED"&&!KNOWN_EMBEDS.has(n.id))
  .sort((a,b)=>parseInt(a.id.split(":")[1])-parseInt(b.id.split(":")[1])).pop();
e.x=-1664; e.y=1960;   // above the grid title
```

## SEGREGATE by type (A block on top, B block below) — deterministic rebuild
Do NOT move slots/labels by matching positions (ambiguous once media overlap them). Instead:
delete old slots+labels, keep media, re-derive segment order from media id-sort, recompute A/B
ranks, place media + fresh slots/labels + section headers.
```js
const page=figma.currentPage;
await Promise.all(["Bold","Medium"].map(s=>figma.loadFontAsync({family:"Inter",style:s})));
const solid=h=>{h=h.replace('#','');return[{type:"SOLID",color:{r:parseInt(h.slice(0,2),16)/255,g:parseInt(h.slice(2,4),16)/255,b:parseInt(h.slice(4,6),16)/255}}];};
// 1) remove old grid slots/labels (keep media + title + embed). Tune the y-band to your grid.
for(const n of page.children.filter(n=>typeof n.y==="number"&&n.y>2560&&n.y<6000&&(n.type==="SHAPE_WITH_TEXT"||n.type==="TEXT"))) n.remove();
// 2) labels via CORS
const csv=await(await fetch("http://localhost:9230/plan_merged.csv")).text();
const meta={}; csv.trim().split("\n").slice(1).forEach(l=>{const c=l.split(",");meta[+c[0]]={cls:c[1],stc:c[5],etc:c[6],dur:Math.round(+c[4])};});
// 3) media in segment order
const KNOWN=new Set([/* other boards' media */]);
const media=page.children.filter(n=>n.type==="MEDIA"&&!KNOWN.has(n.id)).sort((a,b)=>parseInt(a.id.split(":")[1])-parseInt(b.id.split(":")[1]));
// SEQ = the A/B/C string you classified (per merged seg, C excluded so only A/B here)
const SEQ=Object.keys(meta).sort((a,b)=>a-b).map(k=>meta[k].cls).join("");
const aRank=[],bRank=[];let a=0,b=0;for(let i=0;i<SEQ.length;i++){if(SEQ[i]==="A")aRank[i]=a++;else bRank[i]=b++;}
const OX=-1664,px=420,py=341,cw=360,ch=203,OY_A=2660,OY_B=OY_A+Math.ceil(a/8)*py+120;
const COL={A:{s:"#2BB0A6",l:"#1A6E68"},B:{s:"#E0A43A",l:"#9A6B12"}};
media.forEach((m,seg)=>{const cls=meta[seg].cls,r=cls==="A"?aRank[seg]:bRank[seg],base=cls==="A"?OY_A:OY_B;
  const x=OX+(r%8)*px,y=base+((r/8)|0)*py;
  const sl=figma.createShapeWithText();sl.shapeType="SQUARE";page.insertChild(0,sl);  // behind media
  sl.resize(cw+8,ch+8);sl.x=x-4;sl.y=y-4;sl.fills=solid("#F2F4F7");sl.strokes=solid(COL[cls].s);sl.strokeWeight=3;sl.cornerRadius=8;sl.text.characters="";
  m.resize(cw,ch);m.x=x;m.y=y;
  const md=meta[seg],t=figma.createText();page.appendChild(t);t.fontName={family:"Inter",style:"Medium"};t.fontSize=16;t.textAutoResize="HEIGHT";
  t.characters=`seg${String(seg).padStart(2,'0')}  ·  ${cls}  ·  ${md.stc}–${md.etc}  ·  ${md.dur}s`;t.resize(cw,t.height);t.x=x;t.y=y+ch+8;t.fills=solid(COL[cls].l);});
const hdr=(str,y,c)=>{const t=figma.createText();page.appendChild(t);t.fontName={family:"Inter",style:"Bold"};t.fontSize=34;t.textAutoResize="HEIGHT";t.characters=str;t.resize(3300,t.height);t.x=OX;t.y=y;t.fills=solid(c);};
hdr(`A · NO TALKING HEAD — b-roll / animation / screen / charts / external clips (${a})`,OY_A-60,"#1A6E68");
hdr(`B · TALKING HEAD + OVERLAY — presenter on camera with graphics/text on top (${b})`,OY_B-60,"#9A6B12");
return {placed:media.length,nA:a,nB:b};
```

Validate after each pass with `figma_capture_screenshot({scale:1})` (full-page is downscaled to
1568px — fine for layout; pass a nodeId for detail).
