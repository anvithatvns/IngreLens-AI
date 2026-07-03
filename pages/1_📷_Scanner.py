"""IngreLens AI — 📷 Scanner · Camera Barcode + Upload + Paste"""
import streamlit as st, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_ui import (inject_css, init_state, render_sidebar, render_page_header, add_history,
                        full_analysis_display, get_logo_b64, SAGE,
                        cached_analyze, cached_ocr_extract, log_activity)
from backend.services.analysis_service import IngredientAnalysisService
from backend.services.product_service import ProductFetchService
from backend.services.ocr_service import OCRService

st.set_page_config(page_title="Scanner · IngreLens AI", page_icon="📷", layout="wide")
inject_css(); init_state(); render_sidebar()

@st.cache_resource(show_spinner=False)
def get_svc(): return IngredientAnalysisService(), ProductFetchService(), OCRService()
svc, prod_svc, ocr = get_svc()

render_page_header("📷", "Ingredient Scanner",
    "Scan a barcode with your camera, upload a label image, or paste ingredients")

# ── Session state init ────────────────────────────────────────────────────────
def clear_scanner_state():
    for k in ["ocr_extracted","ocr_result","ocr_result_name","ocr_prod_name_saved","ocr_image_hash",
              "barcode_result","barcode_prod","paste_result","paste_result_name",
              "paste_text","paste_name","selected_barcode","cam_detected_bc"]:
        st.session_state.pop(k, None)

# ── Read barcode from query params (set by JS) ────────────────────────────────
qp = st.query_params
if "bc" in qp and qp["bc"] and not st.session_state.get("barcode_result"):
    detected_bc = qp["bc"]
    st.session_state["cam_detected_bc"] = detected_bc
    # Clear from URL immediately
    st.query_params.clear()

tab1, tab2, tab3 = st.tabs(["📷 Scan / Upload Label", "🔢 Barcode Lookup", "✍️ Paste Ingredients"])


# ══════════════════════════════════════════════════════════════════
# TAB 1 — CAMERA SCANNER + UPLOAD
# ══════════════════════════════════════════════════════════════════
with tab1:

    # If we have a barcode to process (from camera detection)
    if st.session_state.get("cam_detected_bc"):
        detected_bc = st.session_state["cam_detected_bc"]

        st.success(f"🎯 Barcode detected: **{detected_bc}**")

        c1, c2 = st.columns([1,1])
        with c1:
            if st.button("🔍 Fetch & Analyze Product", type="primary",
                         key="btn_fetch_detected", use_container_width=True):
                with st.spinner(f"Fetching product {detected_bc} from Open Food Facts…"):
                    prod = prod_svc.fetch_by_barcode(detected_bc)

                if prod and prod.get("ingredients_text"):
                    with st.spinner("🤖 Running 5-agent analysis…"):
                        result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=detected_bc)
                    st.session_state["barcode_result"] = result
                    st.session_state["barcode_prod"]   = prod
                    st.session_state.pop("cam_detected_bc", None)
                    add_history(prod["name"], result.overall_vegan, prod["ingredients_text"], result, barcode=detected_bc)
                    log_activity("Barcode Scan", "Scanner")
                    st.rerun()
                elif prod:
                    st.warning(f"Found **{prod['name']}** but no ingredient data available.")
                else:
                    st.error(
                        f"❌ Barcode **{detected_bc}** not found on Open Food Facts.\n\n"
                        "This product may not be in the database yet. "
                        "Try the **Paste Ingredients** tab to enter ingredients manually."
                    )
        with c2:
            if st.button("🔄 Scan Another", key="btn_scan_again_top",
                         use_container_width=True):
                st.session_state.pop("cam_detected_bc", None)
                st.rerun()

    # Show analysis result
    elif st.session_state.get("barcode_result"):
        prod   = st.session_state.get("barcode_prod", {})
        result = st.session_state["barcode_result"]
        st.markdown(f"## 📋 {prod.get('name', 'Product')}")
        if prod.get("image"):
            ci, _ = st.columns([1, 4])
            with ci:
                st.image(prod["image"], width=110)
        full_analysis_display(result, prod)
        if st.button("🔄 Clear & Scan Again", key="btn_clear_bc_result", type="secondary"):
            clear_scanner_state()
            st.rerun()

    elif st.session_state.get("ocr_result"):
        st.markdown(f"## 📋 {st.session_state.get('ocr_result_name','Scanned Product')}")
        full_analysis_display(st.session_state["ocr_result"])
        if st.button("🔄 Clear & Scan Again", key="btn_ocr_clear_result", type="secondary"):
            clear_scanner_state()
            st.rerun()

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
    border:2.5px solid #6aab9b; border-radius:10px;
    box-shadow:0 0 0 9999px rgba(0,0,0,0.4);
    pointer-events:none;
  }}
  #scanLine {{
    position:absolute; left:4px; right:4px; top:50%;
    height:2px; background:linear-gradient(90deg,transparent,#6aab9b,transparent);
    animation:scan 1.5s ease-in-out infinite;
  }}
  @keyframes scan {{ 0%,100%{{top:10%}} 50%{{top:85%}} }}
  #statusBar {{
    position:absolute; bottom:10px; left:50%; transform:translateX(-50%);
    background:rgba(0,0,0,0.7); color:white; padding:5px 16px;
    border-radius:99px; font-size:12px; white-space:nowrap; transition:all 0.3s;
  }}
  .statusOk {{ background:rgba(30,132,73,0.9) !important; }}
  .btn-row {{ display:flex; gap:8px; margin-bottom:10px; }}
  .btn-primary {{
    flex:1; background:linear-gradient(135deg,#2d4a3e,#4a7c6f); color:white;
    border:none; border-radius:10px; padding:12px; font-size:14px; font-weight:600;
    cursor:pointer; font-family:inherit;
  }}
  .btn-secondary {{
    background:rgba(45,74,62,0.1); color:#2d4a3e; border:1.5px solid #c5dcd7;
    border-radius:10px; padding:12px 16px; font-size:13px; cursor:pointer; font-family:inherit;
  }}
  .btn-primary:hover {{ opacity:0.9; }} .btn-secondary:hover {{ opacity:0.75; }}
  .btn-primary:disabled {{ opacity:0.5; cursor:not-allowed; }}
  #captureArea {{ display:none; }}
  #capturedImg {{ width:100%; border-radius:10px; border:2px solid #c5dcd7; margin-bottom:8px; }}
  #bcBox {{
    background:#e2f0ec; border:1.5px solid #6aab9b; border-radius:10px;
    padding:12px 16px; margin-bottom:10px; display:none;
  }}
  #bcLabel {{ font-size:11px; font-weight:700; color:#2d4a3e; margin-bottom:3px; }}
  #bcValue {{ font-size:20px; font-weight:700; color:#1e4d3d; font-family:monospace; letter-spacing:1px; }}
  #analyzeBtn {{
    width:100%; background:linear-gradient(135deg,#1e4d3d,#4a7c6f); color:white;
    border:none; border-radius:10px; padding:13px; font-size:15px; font-weight:700;
    cursor:pointer; font-family:inherit; margin-bottom:6px;
  }}
  #analyzeBtn:hover {{ opacity:0.9; }}
  #rescanBtn {{
    width:100%; background:transparent; color:#4a7c6f; border:1.5px solid #c5dcd7;
    border-radius:10px; padding:10px; font-size:13px; cursor:pointer; font-family:inherit;
  }}
  .err {{ background:#fde8e5; border:1px solid #f0bdb5; border-radius:8px; padding:10px 14px; font-size:13px; color:#8b2a1e; margin-bottom:8px; }}
  #supportNote {{ font-size:11px; color:#888; text-align:center; margin-top:4px; }}
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
  ctx.strokeStyle = "#6aab9b";
  ctx.lineWidth = 5;
  ctx.strokeRect(box.x, box.y, box.width, box.height);
  // Label
  ctx.fillStyle = "#6aab9b";
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
                with st.spinner(f"🔍 Fetching barcode {bc_clean} from Open Food Facts…"):
                    prod = prod_svc.fetch_by_barcode(bc_clean)

                if prod and prod.get("ingredients_text"):
                    st.success(f"✅ Found: **{prod['name']}** by {prod.get('brand','—')}")
                    if prod.get("image"):
                        ci_img, _ = st.columns([1,4])
                        ci_img.image(prod["image"], width=100)
                    with st.spinner("🤖 Running 5-agent analysis…"):
                        result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=bc_clean)
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
                        st.success(f"✅ Found (alternate format): **{found['name']}**")
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
                            "→ Use **Paste Ingredients** tab to enter ingredients manually\n"
                            "→ Try **Barcode Lookup** tab for verified demo barcodes"
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
                        st.warning("Could not extract text. Try better lighting or use Paste Ingredients tab.")

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
                        st.warning("Could not extract text. Try better lighting or use Paste Ingredients tab.")

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
                        if st.button("🔄 Scan Again", key="btn_ocr_rescan",
                                     use_container_width=True):
                            clear_scanner_state()
                            st.rerun()


# ══════════════════════════════════════════════════════════════════
# TAB 2 — BARCODE LOOKUP (manual + 12 verified demos)
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 🔢 Lookup by Barcode (EAN / UPC)")

    if st.session_state.get("barcode_result"):
        prod   = st.session_state.get("barcode_prod", {})
        result = st.session_state["barcode_result"]
        st.markdown(f"## 📋 {prod.get('name','Product')}")
        if prod.get("image"):
            ci2, _ = st.columns([1, 4])
            with ci2:
                st.image(prod["image"], width=100)
        full_analysis_display(result, prod)
        if st.button("🔄 Clear & Lookup Again", key="btn_bc_clear", type="secondary"):
            clear_scanner_state()
            st.rerun()
    else:
        bc1, bc2 = st.columns([4, 1])
        with bc1:
            barcode = st.text_input(
                "Barcode", placeholder="e.g. 3017624010701",
                label_visibility="collapsed", key="barcode_input",
            )
        with bc2:
            bc_go = st.button("Lookup →", type="primary",
                              use_container_width=True, key="bc_go_btn")

        st.markdown(
            f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:{SAGE["stone"]};margin:12px 0 6px">'
            f'✅ Verified barcodes — click to load</div>',
            unsafe_allow_html=True,
        )

        DEMOS = [
            ("🍫 Nutella","3017624010701","Not Vegan"),
            ("🍪 Oreo","7622300416981","Vegan"),
            ("🌾 Alpro Oat","5411188131335","Vegan"),
            ("🍦 Ben & Jerry's","8714100735688","Non-Veg"),
            ("🌿 Impossible","0085239026700","Uncertain"),
            ("🥛 Whey Protein","0041570050699","Vegetarian"),
            ("🍬 Kit Kat","4000539400404","Vegetarian"),
            ("🥤 Coca-Cola","5449000000996","Uncertain"),
            ("🌰 Pringles","5053990109204","Uncertain"),
            ("🍊 Tropicana OJ","0048500206867","Vegan"),
            ("🫐 Innocent Smoothie","5038862263887","Vegan"),
            ("🥜 Nutri-Grain","0038000845826","Vegetarian"),
        ]
        DC = {"Vegan":"#1e8449","Vegetarian":"#27ae60","Eggetarian":"#e67e22",
              "Non-Veg":"#c0392b","Uncertain":"#f39c12","Not Vegan":"#c0392b"}

        for row in range(0, len(DEMOS), 4):
            row_items = DEMOS[row:row+4]
            cols = st.columns(4)
            for ci, (lbl, bc, exp) in enumerate(row_items):
                with cols[ci]:
                    st.markdown(
                        f'<div style="font-size:0.62rem;color:{DC.get(exp,"#888")};'
                        f'font-weight:600;text-align:center;margin-bottom:2px">{exp}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(lbl, key=f"dbc_{bc}", use_container_width=True):
                        st.session_state["selected_barcode"] = bc
                        st.rerun()

        active_bc = st.session_state.get("selected_barcode", barcode)
        if st.session_state.get("selected_barcode"):
            st.info(f"📦 Selected: **{active_bc}** — click Lookup →")
            bc_go = True
            barcode = active_bc

        if bc_go and barcode:
            st.session_state.pop("selected_barcode", None)
            bc_clean = barcode.strip()
            with st.spinner(f"🔍 Fetching {bc_clean} from Open Food Facts…"):
                prod = prod_svc.fetch_by_barcode(bc_clean)
            if not prod:
                st.error(
                    f"❌ **{bc_clean}** not found. Try a demo barcode above, "
                    "or use Paste Ingredients to enter manually."
                )
            elif not prod.get("ingredients_text"):
                st.warning(f"Found **{prod['name']}** but no ingredient data available.")
            else:
                st.success(f"✅ Found: **{prod['name']}** · {prod.get('brand','—')}")
                if prod.get("image"):
                    ci3, _ = st.columns([1, 4])
                    with ci3:
                        st.image(prod["image"], width=100)
                with st.spinner("🤖 Analyzing…"):
                    result = cached_analyze(svc, prod["ingredients_text"], prod["name"], barcode=bc_clean)
                st.session_state["barcode_result"] = result
                st.session_state["barcode_prod"]   = prod
                add_history(prod["name"], result.overall_vegan, prod["ingredients_text"], result, barcode=bc_clean)
                log_activity("Barcode Scan", "Scanner")
                st.rerun()


# ══════════════════════════════════════════════════════════════════
# TAB 3 — PASTE INGREDIENTS
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ✍️ Paste or type ingredient list")

    if st.session_state.get("paste_result"):
        result = st.session_state["paste_result"]
        st.markdown(f"## 📋 {st.session_state.get('paste_result_name','Custom Product')}")
        full_analysis_display(result)
        if st.button("🔄 Clear & Scan Again", key="btn_paste_clear", type="secondary"):
            clear_scanner_state()
            st.rerun()
    else:
        EXAMPLES = [
            ("🍫 Nutella","Nutella","Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa, Soya lecithin, Vanillin"),
            ("🍪 Oreo","Oreo","Unbleached enriched flour, Sugar, Palm oil, Cocoa powder, High fructose corn syrup, Soy lecithin, Vanillin"),
            ("🥛 Whey","Whey Protein","Whey protein isolate, Whey protein concentrate, Cocoa powder, Natural flavors, Soy lecithin"),
            ("🌾 Oat Milk","Alpro Oat Milk","Water, Oat (10%), Sunflower oil, Calcium carbonate, Sea salt, Riboflavin B2, Vitamin B12, Vitamin D2"),
            ("🌿 Impossible","Impossible Burger","Water, Soy protein concentrate, Coconut oil, Sunflower oil, Natural flavors, Potato protein, Yeast extract, Salt"),
            ("🍦 Ben & Jerry","Ben & Jerry's","Cream, Skimmed milk, Sugar, Egg yolk, Vanilla extract, Guar gum, Carrageenan"),
            ("🍬 Red Candy","Red Candy","Sugar, Glucose syrup, Citric acid, Carmine (E120), Beeswax (E901)"),
            ("🍗 Butter Chkn","Butter Chicken","Chicken breast, Butter, Cream, Onion, Tomato, Garlic, Ginger, Salt"),
            ("🥚 Egg Rice","Egg Fried Rice","Cooked rice, Eggs, Soy sauce, Sesame oil, Spring onion, Salt, Pepper"),
            ("🍕 Pizza","Cheese Pizza","Wheat flour, Mozzarella cheese, Tomato sauce, Olive oil, Yeast, Salt"),
            ("🌱 Vegan Bar","Vegan Protein Bar","Dates, Almonds, Pea protein, Cocoa powder, Coconut oil, Maple syrup, Chia seeds"),
            ("🍷 Wine","Red Wine","Cabernet Sauvignon grape juice, Sulphur dioxide, Isinglass"),
        ]

        st.markdown(
            f'<div style="font-size:0.65rem;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;color:{SAGE["stone"]};margin-bottom:6px">Load a demo example</div>',
            unsafe_allow_html=True,
        )
        ec = st.columns(4)
        for i, (lbl, name, _) in enumerate(EXAMPLES):
            with ec[i % 4]:
                if st.button(lbl, key=f"ex_{i}", use_container_width=True):
                    st.session_state["paste_text"] = EXAMPLES[i][2]
                    st.session_state["paste_name"] = name
                    st.rerun()

        def_t = st.session_state.get("paste_text", "")
        def_n = st.session_state.get("paste_name", "")

        ma, mb = st.columns([3, 1])
        with ma:
            raw = st.text_area(
                "Ingredient list", value=def_t, height=130,
                placeholder="Paste ingredient list here…",
                label_visibility="collapsed", key="paste_raw",
            )
        with mb:
            pname = st.text_input(
                "Product name", value=def_n, placeholder="e.g. Nutella",
                label_visibility="collapsed", key="paste_name_input",
            )
            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
            go = st.button("🧬 Analyze", type="primary",
                           use_container_width=True, key="paste_go")

        if go and raw:
            with st.spinner("🤖 Running 5-agent analysis pipeline…"):
                result = svc.analyze(raw, pname or "Custom Product")
            st.session_state["paste_result"] = result
            st.session_state["paste_result_name"] = pname or "Custom Product"
            st.session_state.pop("paste_text", None)
            st.session_state.pop("paste_name", None)
            add_history(pname or "Custom Product", result.overall_vegan, raw, result)
            st.rerun()
        elif go:
            st.warning("⚠️ Please enter or paste an ingredient list first.")
