import streamlit as st
import tempfile, os, math
import numpy as np
from PIL import Image

# Real libraries try
try:
    import ezdxf
    HAS_DXF = True
except: HAS_DXF = False

try:
    import cv2
    HAS_CV2 = True
except: HAS_CV2 = False

st.set_page_config(page_title="ATELIER - Real", layout="wide")
st.markdown("<style>.stApp{background:#080808;color:white} h1{letter-spacing:8px;font-weight:200;text-align:center}</style>", unsafe_allow_html=True)
st.markdown("<h1>ATELIER</h1><p style='text-align:center;opacity:0.4'>REAL Parser - DXF + PNG</p>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1,1.8,1])

with col2:
    uploaded = st.file_uploader("DXF / PNG / JPG Upload Karo", type=['dxf','png','jpg','jpeg','pdf'])
    
    real_features = []
    real_dims = {"w":0,"d":0,"h":20}
    
    if uploaded:
        ext = uploaded.name.split('.')[-1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(uploaded.getbuffer())
            tmp_path = tmp.name

        if ext == 'dxf' and HAS_DXF:
            try:
                doc = ezdxf.readfile(tmp_path)
                msp = doc.modelspace()
                xs, ys = [], []
                for e in msp:
                    if e.dxftype() == 'LINE':
                        xs.extend([e.dxf.start.x, e.dxf.end.x])
                        ys.extend([e.dxf.start.y, e.dxf.end.y])
                    elif e.dxftype() == 'CIRCLE':
                        xs.append(e.dxf.center.x)
                        ys.append(e.dxf.center.y)
                        real_features.append({"name":f"Hole dia {e.dxf.radius*2:.1f}","type":"hole","dim":f"dia:{e.dxf.radius*2:.1f}"})
                if xs and ys:
                    real_dims["w"] = max(xs)-min(xs)
                    real_dims["d"] = max(ys)-min(ys)
                    real_features.insert(0, {"name":f"Outline {real_dims['w']:.1f} x {real_dims['d']:.1f}","type":"sketch","dim":f"w:{real_dims['w']:.1f} d:{real_dims['d']:.1f}"})
                    st.success(f"REAL DXF Parsed! Size: {real_dims['w']:.1f} x {real_dims['d']:.1f}")
                else:
                    st.warning("DXF khali hai")
            except Exception as ex:
                st.error(f"DXF Error: {ex}")

        elif ext in ['png','jpg','jpeg'] and HAS_CV2:
            try:
                img = cv2.imread(tmp_path)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    biggest = max(contours, key=cv2.contourArea)
                    x,y,w,h = cv2.boundingRect(biggest)
                    real_dims["w"] = w
                    real_dims["d"] = h
                    # holes count
                    holes = len([c for c in contours if cv2.contourArea(c) > 100 and cv2.contourArea(c) < cv2.contourArea(biggest)*0.5])
                    real_features.append({"name":f"Outline {w} x {h} px","type":"sketch","dim":f"w:{w} d:{h}"})
                    if holes>0:
                        real_features.append({"name":f"{holes} Holes Detected","type":"hole","dim":f"count:{holes}"})
                    real_features.append({"name":"Base Extrude","type":"extrude","dim":"h:20mm"})
                    st.image(img, caption=f"Detected: {w}x{h}, Holes:{holes}", use_column_width=True)
                    st.success(f"REAL PNG Parsed! {w}x{h} px, {holes} holes")
            except Exception as ex:
                st.error(f"PNG Error: {ex}")
        else:
            st.error("Library missing. requirements.txt check karo")

        os.unlink(tmp_path)

with col1:
    st.markdown("### REAL FEATURES")
    if real_features:
        for f in real_features:
            st.markdown(f"<div style='background:rgba(255,255,255,0.06);padding:12px;border-radius:10px;margin-top:8px'><b>{f['name']}</b><br><span style='opacity:0.5'>{f['type']} {f['dim']}</span></div>", unsafe_allow_html=True)
    else:
        st.info("File upload karo to real features yahan ayenge")

with col3:
    st.markdown("### EXPORT")
    if real_features and real_dims["w"]>0:
        # Real STEP with real dims
        step_txt = f"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ATELIER Real from {uploaded.name} - {real_dims["w"]}x{real_dims["d"]}'),'2;1');
ENDSEC;
DATA;
#1 = CARTESIAN_POINT('Origin',(0,0,0));
#10 = BLOCK('RealBlock',#1,{real_dims['w']:.2f},{real_dims['d']:.2f},{real_dims['h']:.2f});
ENDSEC;
END-ISO-10303-21;
"""
        st.download_button("Download REAL STEP", step_txt, file_name=f"{uploaded.name}.step", mime="application/step", type="primary", use_container_width=True)
        st.caption(f"Real size: {real_dims['w']:.1f} x {real_dims['d']:.1f} - Ab ye fake nahi hai")
    else:
        st.button("Download STEP", disabled=True, use_container_width=True)
