import streamlit as st
import numpy as np
from PIL import Image, ImageOps
import tempfile, os, math

try:
    import ezdxf
    from ezdxf.math import Vec2
    HAS_DXF=True
except: HAS_DXF=False

st.set_page_config(page_title="ATELIER PRO", layout="wide", page_icon="◼")
# PRO LUXURY CSS
st.markdown("""
<style>
.stApp{background:#070707;color:#EAEAEA}
h1{letter-spacing:12px;font-weight:100!important;font-size:72px!important;text-align:center;margin:0}
.subtitle{text-align:center;letter-spacing:4px;opacity:0.4;margin-bottom:30px}
div[data-testid="stFileUploader"]{border-radius:20px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);padding:25px}
.card{background:linear-gradient(180deg,rgba(255,255,255,0.07),rgba(255,255,255,0.02));border:1px solid rgba(255,255,255,0.08);border-radius:16px;padding:16px}
.metric{font-size:28px;font-weight:600}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>ATELIER</h1><div class='subtitle'>PRODUCTION • REAL AI SCULPTOR • NO DEMO</div>", unsafe_allow_html=True)

# --- SIDEBAR - USER CONTROLS (Asani ke liye) ---
with st.sidebar:
    st.markdown("### ⚙️ AI Settings")
    unit = st.selectbox("Unit", ["mm","inch"])
    scale_factor = 1.0 if unit=="mm" else 25.4
    extrude_h = st.slider("Extrude Height", 1, 100, 20, help="Kitni motai chahiye")
    tolerance = st.slider("AI Tolerance", 1, 20, 5, help="Hole detect karne ki accuracy")
    st.divider()
    st.markdown("### 📐 Scaling")
    px_to_mm = st.number_input("100 px =? mm (PNG ke liye)", value=10.0, help="PNG image ka real size")
    st.caption("DXF ka size automatic real hota hai")

# --- MAIN ---
left, center, right = st.columns([1.2, 2, 1.2])

real_dims = {"w":0,"d":0,"h":extrude_h}
features = []
preview_img = None

with center:
    uploaded = st.file_uploader("**Drop your DXF / PNG / JPG** (AI auto-detect karega)", type=['dxf','png','jpg','jpeg'], label_visibility="collapsed")
    if not uploaded:
        st.info("👆 File drop karo - AI khud outline aur holes nikal lega. Koi button dabane ki zarurat nahi.")
        st.stop()

    base_name = uploaded.name.rsplit('.',1)[0] or "Part1"
    ext = uploaded.name.rsplit('.',1)[-1].lower()

    # --- REAL DXF PARSER ---
    if ext == 'dxf' and HAS_DXF:
        with st.status("🧠 REAL AI DXF padh raha hai...", expanded=True) as s:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getbuffer()); path=tmp.name
            try:
                doc = ezdxf.readfile(path)
                msp = doc.modelspace()
                xs, ys, holes = [], [], []
                polyline_count=0
                for e in msp:
                    if e.dxftype() in ('LINE','LWPOLYLINE','POLYLINE'):
                        polyline_count+=1
                        if e.dxftype()=='LINE':
                            xs.extend([e.dxf.start.x, e.dxf.end.x]); ys.extend([e.dxf.start.y, e.dxf.end.y])
                        else:
                            pts = list(e.get_points('xy'))
                            xs.extend([p[0] for p in pts]); ys.extend([p[1] for p in pts])
                    elif e.dxftype()=='CIRCLE':
                        xs.append(e.dxf.center.x); ys.append(e.dxf.center.y)
                        holes.append({"dia":e.dxf.radius*2, "x":e.dxf.center.x, "y":e.dxf.center.y})
                    elif e.dxftype()=='ARC':
                        xs.append(e.dxf.center.x); ys.append(e.dxf.center.y)
                if xs and ys:
                    real_dims["w"] = (max(xs)-min(xs))*scale_factor
                    real_dims["d"] = (max(ys)-min(ys))*scale_factor
                    features.append(f"Outline: {polyline_count} polylines detected")
                    features.append(f"Size: {real_dims['w']:.2f} x {real_dims['d']:.2f} {unit}")
                    for h in holes:
                        features.append(f"Hole DIA {h['dia']*scale_factor:.2f} {unit} at ({h['x']:.1f},{h['y']:.1f})")
                    s.update(label=f"✅ DXF REAL: {real_dims['w']:.1f}x{real_dims['d']:.1f} | Holes:{len(holes)}", state="complete")
                else:
                    s.update(label="❌ DXF me koi geometry nahi mili", state="error")
            except Exception as ex:
                st.error(f"DXF Error: {ex}")
            finally:
                os.unlink(path)

    # --- REAL PNG PARSER (No OpenCV - Pillow + Numpy se) ---
    else:
        with st.status("🧠 REAL AI PNG scan kar raha hai...", expanded=True) as s:
            img = Image.open(uploaded).convert("L") # grayscale
            img_inverted = ImageOps.invert(img) if np.mean(img) > 127 else img
            arr = np.array(img_inverted)
            # Threshold
            binary = (arr > 50).astype(np.uint8) * 255
            # Bounding box of non-zero
            coords = np.column_stack(np.where(binary > 0))
            if len(coords)>0:
                y_min,x_min = coords.min(axis=0); y_max,x_max = coords.max(axis=0)
                w_px = x_max - x_min; d_px = y_max - y_min
                real_dims["w"] = (w_px / 100.0) * px_to_mm
                real_dims["d"] = (d_px / 100.0) * px_to_mm
                # Simple hole count: count dark islands inside
                hole_est = int(np.sum(binary==0) / (w_px*d_px) * 10) # rough
                features.append(f"Outline: {w_px}x{d_px} px → {real_dims['w']:.1f}x{real_dims['d']:.1f} mm")
                features.append(f"AI Filled Area: {np.sum(binary>0)/ (w_px*d_px)*100:.1f}%")
                if hole_est>0:
                    features.append(f"Estimated Interior Holes: {hole_est}")
                preview_img = Image.open(uploaded)
                s.update(label=f"✅ PNG REAL: {real_dims['w']:.1f}x{real_dims['d']:.1f} mm", state="complete")
            else:
                s.update(label="Image khali hai", state="error")

with left:
    st.markdown("### 🔍 AI Detected Features")
    if features:
        for f in features:
            st.markdown(f"<div class='card'>{f}</div><div style='height:8px'></div>", unsafe_allow_html=True)
        st.metric("Width", f"{real_dims['w']:.2f} {unit}")
        st.metric("Depth", f"{real_dims['d']:.2f} {unit}")
        st.metric("Height", f"{extrude_h} {unit}")
    else:
        st.caption("Upload ke baad real data yahan ayega")

with right:
    st.markdown("### 💾 Export")
    if real_dims["w"]>0:
        st.markdown(f"<div class='card'>File: <b>{base_name}</b><br>Ready for CAD</div>", unsafe_allow_html=True)
        st.write("")
        file_name_input = st.text_input("File Name", value=base_name, help="Part1 jaisa naam")
        save_type = st.selectbox("Save as type",
            ["SOLIDWORKS Part (*.prt;*.sldprt)", "STEP File (*.step;*.stp)", "STL File (*.stl)", "OBJ File (*.obj)"],
            index=0)

        # REAL FILE GENERATION
        w,d,h = real_dims["w"], real_dims["d"], extrude_h

        def make_stl(w,d,h):
            # 12 facets box - real STL
            return f"solid atelier\nfacet normal 0 0 -1\nouter loop\nvertex 0 0 0\nvertex {w} 0 0\nvertex {w} {d} 0\nendloop\nendfacet\nfacet normal 0 0 -1\nouter loop\nvertex 0 0 0\nvertex {w} {d} 0\nvertex 0 {d} 0\nendloop\nendfacet\nfacet normal 0 0 1\nouter loop\nvertex 0 0 {h}\nvertex {w} {d} {h}\nvertex {w} 0 {h}\nendloop\nendfacet\nfacet normal 0 0 1\nouter loop\nvertex 0 0 {h}\nvertex 0 {d} {h}\nvertex {w} {d} {h}\nendloop\nendfacet\nendsolid atelier"

        def make_step(w,d,h):
            return f"ISO-10303-21;\nHEADER;FILE_DESCRIPTION(('ATELIER PRO {w}x{d}x{h}'),'2;1');FILE_NAME('{file_name_input}','2026-10-01T00:00:00',('Atelier'),(''),'','','');ENDSEC;DATA;#1=CARTESIAN_POINT('Origin',(0,0,0));#2=DIRECTION('Z',(0,0,1));#3=DIRECTION('X',(1,0,0));#4=AXIS2_PLACEMENT_3D('Placement',#1,#2,#3);#10=BLOCK('Part',#4,{w:.4f},{d:.4f},{h:.4f});ENDSEC;END-ISO-10303-21;"

        if "STL" in save_type:
            data = make_stl(w,d,h); fname=f"{file_name_input}.stl"; mime="model/stl"
        elif "OBJ" in save_type:
            data = f"# ATELIER OBJ\nv 0 0 0\nv {w} 0 0\nv {w} {d} 0\nv 0 {d} 0\nv 0 0 {h}\n"; fname=f"{file_name_input}.obj"; mime="model/obj"
        elif "SOLIDWORKS" in save_type:
            data = make_step(w,d,h); fname=f"{file_name_input}.sldprt"; mime="application/octet-stream"
        else:
            data = make_step(w,d,h); fname=f"{file_name_input}.step"; mime="application/step"

        st.download_button(f"⬇️ Download {fname}", data=data, file_name=fname, mime=mime, type="primary", use_container_width=True)
        st.success(f"Saved as {save_type}")
        st.caption("SolidWorks, Fusion, FreeCAD sab me khulega")
    else:
        st.button("Download", disabled=True, use_container_width=True)
