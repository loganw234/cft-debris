# l_media.py - cft-debris (DEBRIS-L): the frames, the screenshots, the video (ffmpeg, libx264, -threads 2) and the live display
# (one HTML file, data inline, no network access) from l_prop.py's states. Everything goes to the ledger's debris-l\ (the
# pictures and the video show positions derived from open orbit data); the repository gets this script only.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23.
#
#   python -I -B l_media.py --ledger DIR --scratch DIR --ffmpeg EXE --logs DIR --keep DIR --cpu TSV
# Writes: scratch/frames/f0000.png .. f0180.png; scratch/work/pix.npz (the pixel each object was drawn at, per frame and view);
#   ledger/debris-l/{screenshots/*.png, video.mp4, live_display.html} each with a <name>.sidecar.json naming the SHA-256 of the data
#   (states.npy, groups.npy, the seed) and of this script.
import argparse
import base64
import datetime
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import k_lib as K  # noqa: E402
import l_draw as D  # noqa: E402
import l_lib as L  # noqa: E402
import l_png  # noqa: E402

SCRIPT = os.path.abspath(__file__)
CRITERIA = """
M1 every coordinate of every frame is under 10,000 km in size (the display stores 16-bit integers of km);
M2 every frame is 1,280 x 720 and its PNG is read back by l_png.read_png with every CRC good and the same pixels;
M3 the video has 181 frames at 30 a second: the stderr of ffmpeg's null-output decode of it says 181 frames, and its stream
   line names h264 and 1280x720;
M4 the display's file holds no network address (no 'http' and no 'src=' or 'href=' outside its own text), 181 x 2,688 x 3
   16-bit values and 2,688 group bytes, and decoding its base64 gives back round(position in km) for every value;
M5 every picture, the video and the display have a sidecar naming the SHA-256 of the data and of the scripts.
"""
CAPTION = "POSITIONS ARE M1'S PROPAGATION OF DEBRIS-H'S SEED, NOT OBSERVATIONS"
T0 = datetime.datetime(2026, 11, 18, 22, 50, 0)


def tlabel(k):
    d = datetime.timedelta(seconds=int(L.DELTA_S * k))
    s = int(L.DELTA_S * k)
    return "%s TDB   T_S + %02d:%02d:%02d" % ((T0 + d).strftime("%Y-%m-%d %H:%M:%S"), s // 3600, (s // 60) % 60, s % 60)


def lines_for(k, n):
    return ["CFT-DEBRIS  M1 PROPAGATION  %d OBJECTS  FRAME %03d" % (n, k), tlabel(k)]


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>cft-debris tracked population</title>
<style>
body{margin:0;background:#06080f;color:#e6ebf5;font:14px/1.4 system-ui,sans-serif}
#bar{padding:8px 12px;display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center}
canvas{display:block;margin:0 auto;max-width:100%;height:auto;background:#06080f}
#cap{padding:6px 12px;color:#8c96aa;font-size:13px}
label{white-space:nowrap}
button,select{font:inherit}
</style></head><body>
<div id="bar">
<button id="play">Play</button>
<label>speed <select id="speed"><option value="5">5 frames/s</option><option value="10" selected>10 frames/s</option><option value="30">30 frames/s</option></select></label>
<label>view <select id="view"><option value="top">top (north pole)</option><option value="edge">edge-on</option></select></label>
<span id="groups"></span>
<input type="range" id="slider" min="0" max="__NF1__" value="0" style="width:240px">
<span id="tl"></span>
</div>
<canvas id="cv" width="760" height="760"></canvas>
<div id="cap">cft-debris, MIT licence. Positions are M1's propagation of DEBRIS-H's seed (inertial frame), rounded to 1 km, not observations. __N__ objects, one frame every __DELTA__ s. The Earth is a disc of 6378.137 km. No network access.</div>
<script>
"use strict";
const NF=__NF__, N=__N__, DELTA=__DELTA__, RE=6378.137;
const NAMES=__NAMES__, COLORS=__COLORS__, T0=Date.UTC(2026,10,18,22,50,0);
function dec(b64){const s=atob(b64),u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u;}
const gb=dec("__GB64__"), pb=dec("__PB64__");
const pos=new Int16Array(NF*N*3);
for(let i=0;i<pos.length;i++){let v=pb[2*i]|(pb[2*i+1]<<8);pos[i]=v>=32768?v-65536:v;}
const cv=document.getElementById("cv"),cx=cv.getContext("2d");
const S=cv.width/2/8000;
const on=NAMES.map(()=>true);
const gdiv=document.getElementById("groups");
NAMES.forEach((nm,g)=>{const l=document.createElement("label");const c=document.createElement("input");c.type="checkbox";c.checked=true;
 c.addEventListener("change",()=>{on[g]=c.checked;draw();});l.appendChild(c);
 const sw=document.createElement("span");sw.textContent=" \u25A0 ";sw.style.color=COLORS[g];l.appendChild(sw);l.appendChild(document.createTextNode(nm));gdiv.appendChild(l);});
let k=0,playing=false,last=0,acc=0;
function stamp(k){const d=new Date(T0+k*DELTA*1000);const p=x=>String(x).padStart(2,"0");
 const s=k*DELTA;return d.getUTCFullYear()+"-"+p(d.getUTCMonth()+1)+"-"+p(d.getUTCDate())+" "+p(d.getUTCHours())+":"+p(d.getUTCMinutes())+":"+p(d.getUTCSeconds())+" TDB, T_s + "+p(Math.floor(s/3600))+":"+p(Math.floor(s/60)%60)+":"+p(s%60)+" (frame "+k+")";}
function draw(){
 const view=document.getElementById("view").value, W=cv.width, c=W/2;
 cx.fillStyle="#06080f";cx.fillRect(0,0,W,W);
 cx.fillStyle="#163468";cx.beginPath();cx.arc(c,c,RE*S,0,6.2831853);cx.fill();
 cx.strokeStyle="#4678c8";cx.lineWidth=1.5;cx.stroke();
 const re2=RE*RE, base=k*N*3;
 for(let g=0;g<NAMES.length;g++){ if(!on[g])continue; cx.fillStyle=COLORS[g];
  for(let i=0;i<N;i++){ if(gb[i]!==g)continue;
   const x=pos[base+3*i],y=pos[base+3*i+1],z=pos[base+3*i+2];
   let v,hid;
   if(view==="top"){v=y;hid=z<0&&x*x+y*y<re2;}else{v=z;hid=y>0&&x*x+z*z<re2;}
   if(hid)continue;
   cx.fillRect(Math.floor(c+x*S+0.5)-1,Math.floor(c-v*S+0.5)-1,3,3);}}
 document.getElementById("tl").textContent=stamp(k);
 document.getElementById("slider").value=k;
}
function tick(ts){if(!playing)return;if(!last)last=ts;acc+=(ts-last)/1000*Number(document.getElementById("speed").value);last=ts;
 if(acc>=1){const n=Math.floor(acc);acc-=n;k=(k+n)%NF;draw();}requestAnimationFrame(tick);}
document.getElementById("play").addEventListener("click",e=>{playing=!playing;e.target.textContent=playing?"Pause":"Play";last=0;acc=0;if(playing)requestAnimationFrame(tick);});
document.getElementById("view").addEventListener("change",draw);
document.getElementById("slider").addEventListener("input",e=>{k=Number(e.target.value);draw();});
draw();
</script></body></html>
"""


def sidecar(path, data_files, scripts, extra=None):
    d = {"file": os.path.basename(path), "sha256": K.sha256(path), "bytes": os.path.getsize(path),
         "data": {os.path.basename(p): K.sha256(p) for p in data_files},
         "scripts": {os.path.basename(p): K.sha256(p) for p in scripts},
         "made": "DEBRIS-L, cft-debris tests/l_media.py; positions are M1's propagation of DEBRIS-H's seed, not observations"}
    if extra:
        d.update(extra)
    if os.path.exists(path + ".sidecar.json"):
        os.remove(path + ".sidecar.json")  # this script's own earlier sidecar
    with open(path + ".sidecar.json", "x", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, indent=1, sort_keys=True)
        f.write("\n")
    return d


def main():
    ap = argparse.ArgumentParser()
    for o in ("--ledger", "--scratch", "--ffmpeg", "--logs", "--keep", "--cpu"):
        ap.add_argument(o, required=True)
    a = ap.parse_args()
    L.set_roots(scratch=a.scratch, ledger=a.ledger, repo=L.HERE_REPO, ffmpeg=a.ffmpeg, msys="C:/msys64")
    cpu = K.CpuAccount("l_media", a.cpu)
    W = os.path.join(a.scratch, "work")
    FR = os.path.join(a.scratch, "frames")
    os.makedirs(FR, exist_ok=True)
    out = os.path.join(a.ledger, "debris-l")
    os.makedirs(os.path.join(out, "screenshots"), exist_ok=True)
    mods = [os.path.join(L.TESTS, f) for f in ("l_lib.py", "l_draw.py", "l_png.py", "l_font.py")]
    log = L.Log("l_media", a.logs, SCRIPT, CRITERIA, a.keep, detail_dir=os.path.join(out, "logs"), modules=mods)
    st = np.load(os.path.join(W, "states.npy"))
    gi = np.load(os.path.join(W, "groups.npy"))
    nf, n = st.shape[0], st.shape[1]
    kmpos = st[:, :, :3] / 1000.0
    mx = float(np.abs(kmpos).max())
    log.check(nf == L.NFRAMES and n == 2688 and mx < 10000.0, "M1 %d frames, %d objects, largest coordinate %.1f km (< 10,000)" % (nf, n, mx))
    counts = [int((gi == k).sum()) for k in range(len(L.GROUPS))]
    data_files = [os.path.join(W, "states.npy"), os.path.join(W, "groups.npy")]
    scripts = [SCRIPT] + mods
    # the frames
    pix = {"top_col": np.zeros((nf, n), np.int16), "top_row": np.zeros((nf, n), np.int16), "top_drawn": np.zeros((nf, n), bool),
           "edge_col": np.zeros((nf, n), np.int16), "edge_row": np.zeros((nf, n), np.int16), "edge_drawn": np.zeros((nf, n), bool)}
    good = True
    for k in range(nf):
        img, info = D.render(kmpos[k], gi, "both", lines_for(k, n), CAPTION, counts=counts)
        b = l_png.write_png(os.path.join(FR, "f%04d.png" % k), img, 1)
        if k in (0, 90, 180):
            back, ch = l_png.read_png(os.path.join(FR, "f%04d.png" % k))
            good &= bool(back.shape == (720, 1280, 3) and (back == img).all() and all(c[2] for c in ch))
        for v in ("top", "edge"):
            pix[v + "_col"][k] = info[v]["col"]
            pix[v + "_row"][k] = info[v]["row"]
            pix[v + "_drawn"][k] = info[v]["drawn"]
    np.savez(os.path.join(W, "pix.npz"), **pix)
    for v in ("top", "edge"):
        dr = pix[v + "_drawn"]
        log.w("# %s view: objects drawn in frame 0 / frame 90 / frame 180: %d / %d / %d of %d (the rest are behind the Earth's disc or off the picture)" % (
            v, int(dr[0].sum()), int(dr[90].sum()), int(dr[180].sum()), n))
    log.check(good, "M2 181 frames of 1,280 x 720 written; frames 0, 90 and 180 read back equal, every CRC good")
    # the screenshots
    shots = []
    for name, layout, k in (("shot_both_k000", "both", 0), ("shot_both_k180", "both", 180), ("shot_top_k000", "top", 0), ("shot_edge_k000", "edge", 0)):
        img, _ = D.render(kmpos[k], gi, layout, lines_for(k, n), CAPTION, counts=counts)
        p = os.path.join(out, "screenshots", name + ".png")
        l_png.write_png(p, img, 6)
        back, ch = l_png.read_png(p)
        log.check(back.shape == (720, 1280, 3) and (back == img).all(), "M2 %s read back equal" % name)
        sidecar(p, data_files, scripts, {"frame": k, "layout": layout})
        shots.append(p)
    # the video
    vp = os.path.join(out, "video.mp4")
    if os.path.exists(vp):
        os.remove(vp)  # my own earlier output of this script
    rc, so, se = K.run([a.ffmpeg, "-y", "-hide_banner", "-threads", "2", "-framerate", "30", "-i", os.path.join(FR, "f%04d.png"), "-c:v", "libx264",
                        "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", vp], log, check=False)
    log.check(rc == 0 and os.path.exists(vp), "ffmpeg exit %d, %s bytes" % (rc, os.path.getsize(vp) if os.path.exists(vp) else "no file"))
    rc2, so2, se2 = K.run([a.ffmpeg, "-hide_banner", "-threads", "2", "-i", vp, "-f", "null", "-"], log, check=False)
    txt = se2.decode("utf-8", "replace")
    fr = re.findall(r"frame=\s*(\d+)", txt)
    stream = [ln for ln in txt.splitlines() if "Video:" in ln]
    log.check(rc2 == 0 and fr and int(fr[-1]) == 181 and stream and "h264" in stream[0] and "1280x720" in stream[0],
              "M3 decode of the video: frames %s; stream line: %s" % (fr[-1] if fr else "none", re.sub(r"\s+", " ", stream[0])[:110] if stream else "none"))
    sidecar(vp, data_files + [os.path.join(FR, "f0000.png")], scripts, {"frames": 181, "fps": 30})
    # the display
    pb = np.round(kmpos).astype("<i2")
    assert pb.shape == (nf, n, 3)
    names = [L.GROUP_LABEL[g].title() for g in L.GROUPS]
    colors = ["#%02x%02x%02x" % L.GROUP_COLOR[g] for g in L.GROUPS]
    html = (HTML.replace("__NF1__", str(nf - 1)).replace("__NF__", str(nf)).replace("__N__", str(n)).replace("__DELTA__", str(int(L.DELTA_S)))
            .replace("__NAMES__", json.dumps(names)).replace("__COLORS__", json.dumps(colors))
            .replace("__GB64__", base64.b64encode(gi.astype(np.uint8).tobytes()).decode()).replace("__PB64__", base64.b64encode(pb.tobytes()).decode()))
    dp = os.path.join(out, "live_display.html")
    if os.path.exists(dp):
        os.remove(dp)
    with open(dp, "xb") as f:
        f.write(html.encode("utf-8"))
    # M4: re-read the file's text, decode its base64 back
    txt = open(dp, "r", encoding="utf-8").read()
    pbd = np.frombuffer(base64.b64decode(re.search(r'const gb=dec\("([A-Za-z0-9+/=]+)"\), pb=dec\("([A-Za-z0-9+/=]+)"\)', txt).group(2)), dtype="<i2")
    gbd = np.frombuffer(base64.b64decode(re.search(r'const gb=dec\("([A-Za-z0-9+/=]+)"', txt).group(1)), dtype=np.uint8)
    net = [m for m in re.findall(r"(?i)https?:|\bsrc\s*=|\bhref\s*=|fetch\(|XMLHttpRequest|import\(", txt)]
    log.check(pbd.size == nf * n * 3 and gbd.size == n and (pbd.reshape(nf, n, 3).astype(float) == np.round(kmpos)).all() and (gbd == gi).all() and not net,
              "M4 display: %d values, %d group bytes, base64 decodes to round(km), %d network patterns, %d bytes" % (pbd.size, gbd.size, len(net), os.path.getsize(dp)))
    sidecar(dp, data_files, scripts, {"frames": nf, "objects": n, "rounding_km": 1})
    log.check(all(os.path.exists(p + ".sidecar.json") for p in shots + [vp, dp]), "M5 sidecars written for %d files" % (len(shots) + 2))
    c = cpu.close("l_media log %03d" % log.n)
    log.w("# CPU: %.2f s by cycles / 2.5e9 (this script and every process it started)" % c)
    return log.close()


if __name__ == "__main__":
    sys.exit(main())
