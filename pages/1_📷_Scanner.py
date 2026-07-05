"""IngreLens AI — 📷 Scanner · Camera Barcode + Upload"""
import streamlit as st, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_top_nav, render_page_header, add_history,
                        full_analysis_display, get_logo_b64, SAGE,
                        cached_analyze, cached_ocr_extract, log_activity, enter_page)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService

st.set_page_config(page_title="Scanner · IngreLens AI", page_icon="📷", layout="wide")
inject_css(); init_state(); render_top_nav()
enter_page("scanner")

@st.cache_resource(show_spinner=False)
def get_svc(): return IngredientAnalysisService(), ProductFetchService(), OCRService()
svc, prod_svc, ocr = get_svc()

render_page_header("📷", "Ingredient Scanner",
    "Scan a barcode with your camera or upload a label image")

# ── Session state init ────────────────────────────────────────────────────────
def clear_scanner_state():
    for k in ["ocr_extracted","ocr_result","ocr_result_name","ocr_prod_name_saved","ocr_image_hash",
              "barcode_result","barcode_prod","cam_detected_bc","scan_mode_radio"]:
        st.session_state.pop(k, None)

# ── Read barcode from query params (set by JS) ────────────────────────────────
qp = st.query_params
if "bc" in qp and qp["bc"] and not st.session_state.get("barcode_result"):
    detected_bc = qp["bc"]
    st.session_state["cam_detected_bc"] = detected_bc
    # Clear from URL immediately
    st.query_params.clear()


# ══════════════════════════════════════════════════════════════════
# CAMERA-DETECTED BARCODE — Scan → Fetch & Analyze → Results (single step)
# ══════════════════════════════════════════════════════════════════
if st.session_state.get("cam_detected_bc"):
    detected_bc = st.session_state["cam_detected_bc"]

    with st.spinner(f"🔍 Fetching & analyzing barcode {detected_bc}…"):
        prod = prod_svc.fetch_by_barcode(detected_bc)
        result = None
        if prod and prod.get("ingredients_text"):
            result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=detected_bc)

    if result:
        st.session_state["barcode_result"] = result
        st.session_state["barcode_prod"]   = prod
        st.session_state.pop("cam_detected_bc", None)
        add_history(prod["name"], result.overall_vegan, prod["ingredients_text"], result, barcode=detected_bc)
        log_activity("Barcode Scan", "Scanner")
        st.rerun()
    elif prod:
        st.warning(f"Found **{prod['name']}** but no ingredient data available.")
        if st.button("🔄 Re-Scan", key="btn_rescan_nodata", use_container_width=True):
            clear_scanner_state()
            st.rerun()
    else:
        st.error(
            f"❌ Barcode **{detected_bc}** not found on Open Food Facts.\n\n"
            "This product may not be in the database yet. "
            "Try the **Barcode Lookup** page to enter ingredients manually."
        )
        if st.button("🔄 Re-Scan", key="btn_rescan_notfound", use_container_width=True):
            clear_scanner_state()
            st.rerun()

# ══════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════
elif st.session_state.get("barcode_result"):
    prod   = st.session_state.get("barcode_prod", {})
    result = st.session_state["barcode_result"]
    st.markdown(f"## 📋 {prod.get('name', 'Product')}")
    if prod.get("image"):
        ci, _ = st.columns([1, 4])
        with ci:
            st.image(prod["image"], width=110)
    full_analysis_display(result, prod, key_suffix="scanner_barcode")
    if st.button("🔄 Re-Scan", key="btn_clear_bc_result", type="secondary"):
        clear_scanner_state()
        st.rerun()

elif st.session_state.get("ocr_result"):
    st.markdown(f"## 📋 {st.session_state.get('ocr_result_name','Scanned Product')}")
    full_analysis_display(st.session_state["ocr_result"], key_suffix="scanner_ocr")
    if st.button("🔄 Re-Scan", key="btn_ocr_clear_result", type="secondary"):
        clear_scanner_state()
        st.rerun()

# ══════════════════════════════════════════════════════════════════
# SCAN — camera or upload
# ══════════════════════════════════════════════════════════════════
else:
    # ── Mode selector ─────────────────────────────────────────────────────
    scan_mode = st.radio(
        "Choose input method:",
        ["📷 Camera — Scan Barcode or Label", "🖼️ Upload Image File"],
        horizontal=True, key="scan_mode_radio",
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ════════════════════════════════════════════════════
    # CAMERA MODE
    # ════════════════════════════════════════════════════
    if "Camera" in scan_mode:
        prod_name_cam = st.text_input(
            "Product name (optional)", placeholder="e.g. Chobani Yogurt",
            key="cam_prod_name",
        )

        # The key insight: JS needs to communicate the barcode to Python.
        # We use URL query params — JS updates window.location with ?bc=BARCODE
        # then Streamlit reads st.query_params on next run.
        # This is the most reliable cross-browser approach without extra packages.

        CURRENT_URL = "http://localhost:8501/Scanner"

        CAMERA_JS = f"""
<style>
  body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:transparent; }}
  #wrap {{ max-width:700px; }}
  .cam-container {{
    position:relative; background:#0a0a0a; border-radius:14px; overflow:hidden;
    margin-bottom:10px; box-shadow:0 4px 20px rgba(0,0,0,0.3);
  }}
  video {{ width:100%; display:block; max-height:420px; object-fit:cover; }}
  canvas#overlay {{
    position:absolute; top:0; left:0; width:100%; height:100%;
    pointer-events:none;
  }}
  #scanFrame {{
    position:absolute; top:50%; left:50%; transform:translate(-50%,-60%);
    width:220px; height:110px;
    border:2.5px solid {SAGE['accent']}; border-radius:10px;
    box-shadow:0 0 0 9999px rgba(0,0,0,0.4);
    pointer-events:none;
  }}
  #scanLine {{
    position:absolute; left:4px; right:4px; top:50%;
    height:2px; background:linear-gradient(90deg,transparent,{SAGE['accent']},transparent);
    animation:scan 1.5s ease-in-out infinite;
  }}
  @keyframes scan {{ 0%,100%{{top:10%}} 50%{{top:85%}} }}
  #statusBar {{
    position:absolute; bottom:10px; left:50%; transform:translateX(-50%);
    background:rgba(0,0,0,0.7); color:white; padding:5px 16px;
    border-radius:99px; font-size:12px; white-space:nowrap; transition:all 0.3s;
  }}
  .statusOk {{ background:rgba(46,204,113,0.9) !important; }}
  .btn-row {{ display:flex; gap:8px; margin-bottom:10px; }}
  .btn-primary {{
    flex:1; background:linear-gradient(135deg,{SAGE['mid']},{SAGE['accent']}); color:#04140f;
    border:none; border-radius:10px; padding:12px; font-size:14px; font-weight:700;
    cursor:pointer; font-family:inherit;
  }}
  .btn-secondary {{
    background:rgba(255,255,255,0.06); color:{SAGE['charcoal']}; border:1.5px solid {SAGE['pale']};
    border-radius:10px; padding:12px 16px; font-size:13px; cursor:pointer; font-family:inherit;
  }}
  .btn-primary:hover {{ opacity:0.9; }} .btn-secondary:hover {{ opacity:0.75; }}
  .btn-primary:disabled {{ opacity:0.5; cursor:not-allowed; }}
  #captureArea {{ display:none; }}
  #capturedImg {{ width:100%; border-radius:10px; border:2px solid {SAGE['pale']}; margin-bottom:8px; }}
  #bcBox {{
    background:rgba(23,201,168,0.14); border:1.5px solid {SAGE['mid']}; border-radius:10px;
    padding:12px 16px; margin-bottom:10px; display:none;
  }}
  #bcLabel {{ font-size:11px; font-weight:700; color:{SAGE['charcoal']}; margin-bottom:3px; }}
  #bcValue {{ font-size:20px; font-weight:700; color:{SAGE['light']}; font-family:monospace; letter-spacing:1px; }}
  #analyzeBtn {{
    width:100%; background:linear-gradient(135deg,{SAGE['mid']},{SAGE['accent']}); color:#04140f;
    border:none; border-radius:10px; padding:13px; font-size:15px; font-weight:700;
    cursor:pointer; font-family:inherit; margin-bottom:6px;
  }}
  #analyzeBtn:hover {{ opacity:0.9; }}
  #rescanBtn {{
    width:100%; background:transparent; color:{SAGE['mid']}; border:1.5px solid {SAGE['pale']};
    border-radius:10px; padding:10px; font-size:13px; cursor:pointer; font-family:inherit;
  }}
  .err {{ background:rgba(229,88,74,0.14); border:1px solid rgba(229,88,74,0.4); border-radius:8px; padding:10px 14px; font-size:13px; color:#ff9686; margin-bottom:8px; }}
  #supportNote {{ font-size:11px; color:{SAGE['stone']}; text-align:center; margin-top:4px; }}
</style>

<div id="wrap">
  <!-- Camera view -->
  <div id="cameraSection">
    <div class="cam-container" id="camContainer">
      <video id="camFeed" autoplay playsinline muted></video>
      <canvas id="overlay"></canvas>
      <div id="scanFrame"><div id="scanLine"></div></div>
      <div id="statusBar">📷 Starting camera…</div>
    </div>
    <div class="btn-row">
      <button class="btn-primary" onclick="captureFrame()">📸 Capture Frame</button>
      <button class="btn-secondary" onclick="flipCamera()">🔄 Flip</button>
    </div>
    <div id="supportNote"></div>
  </div>

  <!-- Captured result -->
  <div id="captureArea">
    <img id="capturedImg" />
    <div id="bcBox">
      <div id="bcLabel">🎯 Barcode Detected!</div>
      <div id="bcValue"></div>
    </div>
    <button id="analyzeBtn" onclick="sendBarcodeToStreamlit()">🧬 Analyze This Product</button>
    <button id="rescanBtn" onclick="resetToCamera()">← Scan Again</button>
  </div>
</div>

<script>
let stream = null;
let facingMode = "environment";
let barcodeReader = null;
let scanInterval = null;
let detectedBarcode = null;

const camFeed   = document.getElementById("camFeed");
const overlay   = document.getElementById("overlay");
const statusBar = document.getElementById("statusBar");

// ── Start camera ──────────────────────────────────────────────────────────────
async function startCamera() {{
  try {{
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = await navigator.mediaDevices.getUserMedia({{
      video: {{ facingMode: facingMode, width:{{ideal:1280}}, height:{{ideal:720}} }}
    }});
    camFeed.srcObject = stream;
    await new Promise(r => camFeed.onloadedmetadata = r);
    camFeed.play();
    statusBar.textContent = "📷 Point at barcode or ingredient label";
    statusBar.className = "";
    startBarcodeDetection();
  }} catch(e) {{
    statusBar.textContent = "⚠️ Camera unavailable — use Upload Image below";
    statusBar.style.background = "rgba(180,60,40,0.85)";
    // Show fallback message
    document.getElementById("cameraSection").innerHTML +=
      '<div class="err" style="margin-top:8px">Camera access denied or not available in this browser.<br>Please use the <b>Upload Image File</b> mode instead.</div>';
  }}
}}

function flipCamera() {{
  facingMode = (facingMode === "environment") ? "user" : "environment";
  stopBarcodeDetection();
  startCamera();
}}

// ── BarcodeDetector ───────────────────────────────────────────────────────────
async function startBarcodeDetection() {{
  const note = document.getElementById("supportNote");
  if (!("BarcodeDetector" in window)) {{
    note.textContent = "ℹ️ Auto barcode detection not supported in this browser — capture and enter barcode manually below.";
    return;
  }}
  note.textContent = "🔍 Auto-scanning for barcodes (EAN, UPC, QR)…";
  try {{
    barcodeReader = new BarcodeDetector({{
      formats: ["ean_13","ean_8","upc_a","upc_e","code_128","code_39","qr_code"]
    }});
    scanInterval = setInterval(async () => {{
      if (camFeed.readyState < camFeed.HAVE_ENOUGH_DATA) return;
      try {{
        const codes = await barcodeReader.detect(camFeed);
        if (codes.length > 0) {{
          const bc = codes[0];
          detectedBarcode = bc.rawValue;
          drawBox(bc.boundingBox);
          statusBar.textContent = "✅ Barcode: " + detectedBarcode;
          statusBar.className = "statusOk";
          note.textContent = "✅ Barcode detected! Click Capture Frame to confirm.";
          stopBarcodeDetection();
        }}
      }} catch(err) {{}}
    }}, 250);
  }} catch(e) {{
    note.textContent = "ℹ️ Barcode detection unavailable — capture frame and enter manually.";
  }}
}}

function stopBarcodeDetection() {{
  if (scanInterval) {{ clearInterval(scanInterval); scanInterval = null; }}
}}

function drawBox(box) {{
  overlay.width  = camFeed.videoWidth;
  overlay.height = camFeed.videoHeight;
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0,0,overlay.width,overlay.height);
  ctx.strokeStyle = "{SAGE['accent']}";
  ctx.lineWidth = 5;
  ctx.strokeRect(box.x, box.y, box.width, box.height);
  // Label
  ctx.fillStyle = "{SAGE['accent']}";
  ctx.fillRect(box.x, box.y - 24, box.width, 24);
  ctx.fillStyle = "white";
  ctx.font = "bold 14px sans-serif";
  ctx.fillText(detectedBarcode, box.x + 4, box.y - 6);
}}

// ── Capture ───────────────────────────────────────────────────────────────────
function captureFrame() {{
  stopBarcodeDetection();

  const captureCanvas = document.createElement("canvas");
  captureCanvas.width  = camFeed.videoWidth  || 640;
  captureCanvas.height = camFeed.videoHeight || 480;
  captureCanvas.getContext("2d").drawImage(camFeed, 0, 0);

  document.getElementById("capturedImg").src = captureCanvas.toDataURL("image/jpeg",0.9);
  document.getElementById("cameraSection").style.display = "none";
  document.getElementById("captureArea").style.display   = "block";

  if (detectedBarcode) {{
    document.getElementById("bcBox").style.display  = "block";
    document.getElementById("bcValue").textContent  = detectedBarcode;
    document.getElementById("analyzeBtn").textContent = "🧬 Analyze: " + detectedBarcode;
  }} else {{
    document.getElementById("bcBox").style.display = "none";
    document.getElementById("analyzeBtn").textContent = "🧬 No barcode detected — enter manually below";
    document.getElementById("analyzeBtn").onclick = showManualEntry;
  }}
}}

function resetToCamera() {{
  detectedBarcode = null;
  document.getElementById("cameraSection").style.display = "block";
  document.getElementById("captureArea").style.display   = "none";
  const ctx = overlay.getContext("2d");
  ctx.clearRect(0,0,overlay.width,overlay.height);
  statusBar.textContent = "📷 Point at barcode or ingredient label";
  statusBar.className   = "";
  startBarcodeDetection();
}}

// ── THE KEY FIX: send barcode to Streamlit via URL query param ────────────────
function sendBarcodeToStreamlit() {{
  if (!detectedBarcode) {{ showManualEntry(); return; }}

  const btn = document.getElementById("analyzeBtn");
  btn.textContent = "⏳ Loading — please wait…";
  btn.disabled = true;

  // Use parent window to set query params — this triggers Streamlit rerun
  try {{
    const url = new URL(window.parent.location.href);
    url.searchParams.set("bc", detectedBarcode);
    window.parent.history.pushState(null, "", url.toString());
    // Force Streamlit to pick up the change
    window.parent.location.search = url.search;
  }} catch(e) {{
    // Cross-origin fallback: write to the text input below
    const inp = window.parent.document.querySelector('input[aria-label="Detected barcode — press Enter to analyze"]');
    if (inp) {{
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
      nativeInputValueSetter.call(inp, detectedBarcode);
      inp.dispatchEvent(new Event("input", {{bubbles:true}}));
      inp.dispatchEvent(new KeyboardEvent("keydown",{{key:"Enter",keyCode:13,bubbles:true}}));
    }}
  }}
}}

function showManualEntry() {{
  // Scroll to the manual input below the component
  const inp = window.parent.document.querySelector('input[placeholder="Enter barcode manually…"]');
  if (inp) inp.focus();
}}

// Start
startCamera();
</script>
"""

        # Render camera component
        st.components.v1.html(CAMERA_JS, height=560, scrolling=False)

        st.markdown("---")
        st.markdown(
            f'<div style="font-size:0.82rem;font-weight:600;color:{SAGE["charcoal"]};'
            f'margin-bottom:6px">📋 After capturing, confirm barcode here:</div>',
            unsafe_allow_html=True,
        )

        # ── THE BRIDGE: Streamlit text input that JS can target ────────────
        # Also picks up query param detection from above
        default_bc = st.session_state.get("cam_detected_bc", "")

        bc_col1, bc_col2 = st.columns([3, 1])
        with bc_col1:
            manual_bc = st.text_input(
                "Detected barcode — press Enter to analyze",
                value=default_bc,
                placeholder="Enter barcode manually…",
                key="manual_bc_input",
                label_visibility="collapsed",
            )
        with bc_col2:
            analyze_bc = st.button(
                "🔍 Fetch & Analyze", type="primary",
                key="btn_analyze_manual_bc", use_container_width=True,
            )

        if analyze_bc and manual_bc:
            bc_clean = manual_bc.strip()
            with st.spinner(f"🔍 Fetching & analyzing {bc_clean}…"):
                prod = prod_svc.fetch_by_barcode(bc_clean)
                result = None
                if prod and prod.get("ingredients_text"):
                    result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=bc_clean)

            if result:
                st.session_state["barcode_result"] = result
                st.session_state["barcode_prod"]   = prod
                st.session_state.pop("cam_detected_bc", None)
                add_history(prod["name"], result.overall_vegan, prod["ingredients_text"], result, barcode=bc_clean)
                log_activity("Barcode Scan", "Scanner")
                st.rerun()
            elif prod:
                st.warning(f"Found **{prod['name']}** but no ingredient data on Open Food Facts.")
            else:
                # Try alternate formats (strip leading zeros etc.)
                alt_bcs = [bc_clean.lstrip("0"), "0" + bc_clean] if bc_clean else []
                found = None
                for alt in alt_bcs:
                    if alt and alt != bc_clean:
                        found = prod_svc.fetch_by_barcode(alt)
                        if found: break

                if found and found.get("ingredients_text"):
                    with st.spinner("🤖 Analyzing…"):
                        result = cached_analyze(svc, found["ingredients_text"], found["name"], barcode=found.get("barcode"))
                    st.session_state["barcode_result"] = result
                    st.session_state["barcode_prod"]   = found
                    add_history(found["name"], result.overall_vegan, found["ingredients_text"], result, barcode=found.get("barcode"))
                    log_activity("Barcode Scan", "Scanner")
                    st.rerun()
                else:
                    st.error(
                        f"❌ **Barcode {bc_clean} not found** on Open Food Facts.\n\n"
                        "**Why this happens:**\n"
                        "- Product may not be in the Open Food Facts database yet\n"
                        "- Try scanning again — barcode may have been misread\n"
                        "- Check the barcode number is correct\n\n"
                        "**What to do:**\n"
                        "→ Use the **Barcode Lookup** page to enter ingredients manually"
                    )

        # Upload fallback option
        st.markdown(
            f'<div style="text-align:center;font-size:0.75rem;color:{SAGE["stone"]};'
            f'margin:10px 0">— or upload a label image for OCR —</div>',
            unsafe_allow_html=True,
        )
        cam_upload = st.file_uploader(
            "Upload label image for OCR", type=["jpg","jpeg","png","webp","bmp"],
            key="cam_ocr_upload", label_visibility="collapsed",
        )
        if cam_upload:
            if st.button("🧬 Extract & Analyze Image", type="secondary",
                         key="btn_cam_ocr", use_container_width=True):
                pname = prod_name_cam or "Scanned Product"
                with st.spinner("🤖 OCR extracting text…"):
                    extracted, img_hash = cached_ocr_extract(ocr, cam_upload)
                if extracted and extracted.strip():
                    with st.spinner("🤖 Analyzing ingredients…"):
                        result = cached_analyze(svc, extracted, pname, image_hash=img_hash)
                    st.session_state["ocr_result"] = result
                    st.session_state["ocr_result_name"] = pname
                    add_history(pname, result.overall_vegan, extracted, result, image_hash=img_hash)
                    log_activity("Image Upload", "Scanner")
                    st.rerun()
                else:
                    st.warning("Could not extract text. Try better lighting or use the Barcode Lookup page's Paste Ingredients tab.")

    # ════════════════════════════════════════════════════
    # UPLOAD IMAGE MODE
    # ════════════════════════════════════════════════════
    else:
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("### Upload ingredient label photo")
            uploaded = st.file_uploader(
                "Drag & drop or click to upload",
                type=["jpg","jpeg","png","webp","bmp"],
                key="ocr_uploader",
            )
            prod_name_img = st.text_input(
                "Product name (optional)", placeholder="e.g. Nutella",
                key="ocr_prod_name",
            )
        with c2:
            st.markdown("### Tips for best results")
            for tip in ["📐 Flatten the label","💡 Even lighting, no shadows",
                        "🔍 Label fills frame","📷 Hold camera still",
                        "🔤 Text sharp and readable"]:
                st.markdown(
                    f'<div style="font-size:0.83rem;padding:3px 0;color:{SAGE["stone"]}">{tip}</div>',
                    unsafe_allow_html=True,
                )
            if not ocr.available:
                st.warning("⚠️ Tesseract not installed.\n`brew install tesseract` (Mac)")

        if uploaded:
            ci, _ = st.columns([1, 2])
            with ci:
                st.image(uploaded, caption="Uploaded", use_container_width=True)

            if st.button("🔍 Extract Text from Image", type="primary", key="btn_extract"):
                with st.spinner("🤖 OCR extracting ingredients…"):
                    extracted, img_hash = cached_ocr_extract(ocr, uploaded)
                if extracted and extracted.strip():
                    st.session_state["ocr_extracted"] = extracted
                    st.session_state["ocr_image_hash"] = img_hash
                    st.session_state["ocr_prod_name_saved"] = prod_name_img or "Scanned Product"
                    log_activity("Image Upload", "Scanner")
                    st.rerun()
                else:
                    st.warning("Could not extract text. Try better lighting or use the Barcode Lookup page's Paste Ingredients tab.")

            if st.session_state.get("ocr_extracted"):
                st.success("✅ Text extracted! Edit if needed, then Analyze.")
                edited = st.text_area(
                    "Extracted ingredients:",
                    value=st.session_state["ocr_extracted"],
                    height=110, key="ocr_edited_text",
                )
                ca, cb, cc = st.columns([2, 2, 2])
                with ca:
                    if st.button("🧬 Analyze", type="primary",
                                 key="btn_ocr_analyze", use_container_width=True):
                        pname = st.session_state.get("ocr_prod_name_saved",
                                                     prod_name_img or "Scanned Product")
                        img_hash = st.session_state.get("ocr_image_hash")
                        with st.spinner("🤖 Running 5-agent analysis…"):
                            result = cached_analyze(svc, edited, pname, image_hash=img_hash)
                        st.session_state["ocr_result"] = result
                        st.session_state["ocr_result_name"] = pname
                        add_history(pname, result.overall_vegan, edited, result, image_hash=img_hash)
                        st.rerun()
                with cb:
                    if st.button("✕ Clear text", key="btn_ocr_clear_text",
                                 use_container_width=True):
                        st.session_state.pop("ocr_extracted", None)
                        st.rerun()
                with cc:
                    if st.button("🔄 Re-Scan", key="btn_ocr_rescan",
                                 use_container_width=True):
                        clear_scanner_state()
                        st.rerun()
