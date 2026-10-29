// ============================================================================
//  FIGJAM BOARD KIT  v1
//  Paste this ENTIRE block at the top of a single figma_execute() call, then
//  write your layout below it using zone()/card()/text()/kanban(), then:
//      const warnings = verify();
//      return { wrapperId: finish("My Board"), warnings };
//  Screenshot the wrapperId in a SEPARATE figma_execute/capture call.
//
//  WHY this exists (the 3 FigJam coordinate traps it neutralizes):
//   1. section.appendChild ADDS the section's origin to a child's x/y. Build
//      every node FREE on the page at absolute coords; only finish() reparents,
//      and it converts coords back (n.x -= W.x) right after appending.
//   2. absoluteBoundingBox is STALE for ~1 tick after a reparent. finish()
//      never reads it — it computes the wrapper bbox from recorded rects.
//   3. figma.createPage() throws in FigJam. We build on currentPage in empty
//      space (clearOrigin) and wrap in ONE section the user can Move to page.
// ============================================================================

const page = figma.currentPage;
await Promise.all(["Regular","Medium","Semi Bold","Bold"]
  .map(s => figma.loadFontAsync({ family:"Inter", style:s })));

function rgb(hex){const h=hex.replace('#','');return {r:parseInt(h.slice(0,2),16)/255,g:parseInt(h.slice(2,4),16)/255,b:parseInt(h.slice(4,6),16)/255};}
function solid(hex){return [{type:"SOLID",color:rgb(hex)}];}

// ---- design tokens (swap zone/status hexes for real brand tokens when needed) ----
const T = {
  bg:"#F7F8FB", ink:"#1A1A2E", sub:"#5A5A72", line:"#D6DCE4", white:"#FFFFFF",
  zone:{ gold:"#FFF4D6", blue:"#E8F0FE", green:"#E6F7EE", purple:"#F3EEFB",
         pink:"#FDEEF2", gray:"#ECEFF3", cream:"#FFF6E6", slate:"#EEF2F6",
         teal:"#EAF6F8", lilac:"#F1F0FA", mint:"#EFF6EE" },
  // [fill, stroke]
  status:{ todo:["#EDEFF2","#C9D0DA"], wip:["#FFF3CC","#E9C94A"],
           blocked:["#FBD9D9","#E59A9A"], done:["#D8F0DE","#8FD0A6"] }
};

// ---- board state (records intended absolute rects — the source of truth) ----
const B = { nodes:[], rects:[] };
function rec(node,x,y,w,h,zone,fs){
  B.nodes.push(node);
  B.rects.push({ name:(node.name||node.type).slice(0,24), x,y,w,h, zone:zone||null,
    kind:node.type, fs:fs||null,
    chars:((node.text&&node.text.characters)||node.characters||"") });
  return node;
}

// ---- find empty canvas to the RIGHT of all existing content (never clobber) ----
function clearOrigin(gap){
  let maxX=-Infinity, has=false;
  for(const n of page.children){ if(typeof n.x==="number"){ has=true; maxX=Math.max(maxX,n.x+(n.width||0)); } }
  return has ? Math.round(maxX + (gap||400)) : 0;
}

// ---- ZONE: a visual section placed FREE at absolute coords ----
function zone(name,x,y,w,h,fill){
  const s=figma.createSection(); page.appendChild(s);
  s.name=name; s.x=x; s.y=y; s.resizeWithoutConstraints(w,h); s.fills=solid(fill||T.zone.slate);
  return rec(s,x,y,w,h,null);
}

// ---- CARD: rounded shape-with-text at absolute coords ----
function card(x,y,w,h,text,fill,stroke,fs,align,zoneName){
  const sh=figma.createShapeWithText(); sh.shapeType="ROUNDED_RECTANGLE"; page.appendChild(sh);
  sh.resize(w,h); sh.x=x; sh.y=y; sh.fills=solid(fill||T.white);
  if(stroke){ sh.strokes=solid(stroke); sh.strokeWeight=2; }
  sh.text.characters=text||""; sh.text.fontSize=fs||15;
  if(align) sh.text.textAlignHorizontal=align;
  return rec(sh,x,y,w,h,zoneName,fs||15);
}

// ---- TEXT: wrapped paragraph at absolute coords ----
function text(x,y,w,str,size,style,color,lh,zoneName){
  const t=figma.createText(); page.appendChild(t);
  t.fontName={family:"Inter",style:style||"Regular"}; t.fontSize=size||16;
  t.textAutoResize="HEIGHT"; t.characters=str; t.resize(w,t.height);
  if(lh) t.lineHeight={value:lh,unit:"PERCENT"};
  t.x=x; t.y=y; if(color) t.fills=solid(color);
  return rec(t,x,y,w,t.height,zoneName,size||16);
}

// ---- KANBAN: even columns + stacked cards inside a zone region ----
// cols: [{title, headFill, fill, stroke, cards:[str,...]}]
function kanban(zx,zy,zw, zoneName, cols, opts){
  const o=opts||{}; const top=o.top!=null?o.top:60; const cg=o.colGap||25;
  const rg=o.rowGap||16; const hH=o.headH||58; const cH=o.cardH||110; const fs=o.fs||15;
  const n=cols.length; const colW=Math.floor((zw-40-cg*(n-1))/n);
  cols.forEach((c,i)=>{
    const x=zx+20+i*(colW+cg);
    card(x, zy+top, colW, hH, c.title, c.headFill||T.zone.slate, null, 17, "CENTER", zoneName);
    (c.cards||[]).forEach((t,j)=>{
      card(x, zy+top+hH+rg+j*(cH+rg), colW, cH, t, c.fill||T.white, c.stroke||T.line, fs, null, zoneName);
    });
  });
}

// ---- ROW: evenly spaced cards across a width (e.g. The Map, backlog) ----
function row(zx,zy,zw, zoneName, items, opts){
  const o=opts||{}; const top=o.top!=null?o.top:60; const g=o.gap||20; const h=o.h||130; const fs=o.fs||15;
  const n=items.length; const w=Math.floor((zw-2*(o.pad||30)-g*(n-1))/n);
  items.forEach((it,i)=>{
    const x=zx+(o.pad||30)+i*(w+g);
    card(x, zy+top, w, h, typeof it==="string"?it:it.text, (it.fill)||T.white, (it.stroke)||T.line, fs, it.align||null, zoneName);
  });
}

// ---- VERIFY: catch overlaps, out-of-zone, likely text overflow ----
function verify(){
  const warn=[];
  const zones=B.rects.filter(r=>r.kind==="SECTION");
  const items=B.rects.filter(r=>r.kind!=="SECTION");
  for(let i=0;i<items.length;i++)for(let j=i+1;j<items.length;j++){
    const a=items[i],b=items[j]; if(a.zone!==b.zone) continue;
    if(a.x<b.x+b.w && a.x+a.w>b.x && a.y<b.y+b.h && a.y+a.h>b.y)
      warn.push(`OVERLAP: "${a.chars.slice(0,18)}" ∩ "${b.chars.slice(0,18)}"`);
  }
  for(const it of items){ if(!it.zone) continue;
    const z=zones.find(z=>z.name===it.zone)||zones.find(z=>z.name.includes(it.zone));
    if(!z) continue;
    if(it.x<z.x-2||it.y<z.y-2||it.x+it.w>z.x+z.w+2||it.y+it.h>z.y+z.h+2)
      warn.push(`OUT-OF-ZONE: "${it.chars.slice(0,18)}" spills "${z.name.slice(0,16)}"`);
  }
  for(const it of items){
    if(it.kind!=="SHAPE_WITH_TEXT"||!it.chars||!it.fs) continue;
    const cap=Math.floor((it.w/(it.fs*0.55))*(it.h/(it.fs*1.35))*0.85);
    if(it.chars.length>cap)
      warn.push(`OVERFLOW?: "${it.chars.slice(0,22)}" (${it.chars.length} ch in ${it.w}×${it.h}@${it.fs})`);
  }
  return warn;
}

// ---- FINISH: wrap everything in ONE movable section. Bbox from records (no stale bbox). ----
function finish(title){
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
  for(const r of B.rects){ minX=Math.min(minX,r.x); minY=Math.min(minY,r.y); maxX=Math.max(maxX,r.x+r.w); maxY=Math.max(maxY,r.y+r.h); }
  const pL=60,pT=90,pR=60,pB=70;
  const W=figma.createSection(); page.appendChild(W);
  W.name=title||"Board  ▸ (move/duplicate this whole block)";
  W.x=minX-pL; W.y=minY-pT; W.resizeWithoutConstraints((maxX-minX)+pL+pR,(maxY-minY)+pT+pB);
  W.fills=solid(T.bg);
  for(const n of B.nodes) W.appendChild(n);
  for(const n of W.children){ if(typeof n.x==="number"){ n.x-=W.x; n.y-=W.y; } } // undo origin-add
  return W.id;
}
