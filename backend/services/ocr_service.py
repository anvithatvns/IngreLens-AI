"""
IngreLens AI — OCR Service v4
Fast: early-exit on high-confidence result, tiered crop strategy.
Accurate: score by ingredient-signal keywords, not by text length.
Dark-bg: adaptive inversion for white-on-dark labels.
"""
from __future__ import annotations
import re, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Ingredient signal words (presence = real ingredient text) ────────────────
_INGREDIENT_SIGNALS = [
    "flour","sugar","salt","water","oil","milk","butter","cream","starch",
    "wheat","corn","soy","soya","egg","gelatin","gelatine","enzyme",
    "vinegar","yeast","pork","beef","chicken","pepperoni","cheese","whey",
    "casein","lactose","emulsifier","preservative","natural flavor",
    "citric acid","lactic acid","sodium","calcium","niacin","riboflavin",
    "thiamine","folic acid","ferrous","mozzarella","cheddar","cultures",
    "mono","diglyceride","lecithin","carrageenan","guar gum","xanthan",
    "dextrose","maltodextrin","potassium","phosphate","sulfate","nitrate",
    "annatto","turmeric","paprika","garlic","onion","spice","herb",
    "enriched","bleached","unbleached","modified","hydrolyzed",
    "ingredients","contains","allergen",
]

# Score threshold considered "high confidence" → triggers early exit
_HIGH_SCORE   = 6   # stop as soon as we find this many signals
_MIN_SCORE    = 2   # minimum to be considered a valid result at all


def _score_text(text: str) -> int:
    t = text.lower()
    return sum(1 for sig in _INGREDIENT_SIGNALS if sig in t)


class OCRService:
    """
    Tiered OCR strategy:
    Tier 1 (fast path): full image + bottom_half with high_contrast, PSM 6 only.
        → If score >= _HIGH_SCORE, return immediately.
    Tier 2 (medium): add left_col, right_col + adaptive_dark strategy.
        → If score >= _MIN_SCORE, return best found so far.
    Tier 3 (exhaustive): remaining crops + strategies (only when tiers 1-2 miss).
    Hard cap: 15 seconds total — return best found so far.
    """

    # Tier 1: fast crops, single strategy, PSM 6 only
    _TIER1_CROPS  = ["full", "bottom_half"]
    _TIER1_STRATS = ["high_contrast"]
    _TIER1_PSMS   = ["6"]

    # Tier 2: add more crops + dark-bg strategy
    _TIER2_CROPS  = ["left_col", "right_col", "bottom_left", "center"]
    _TIER2_STRATS = ["adaptive_dark", "grayscale"]
    _TIER2_PSMS   = ["6", "4"]

    # Tier 3: exhaustive (only when both tiers above fail)
    _TIER3_CROPS  = ["top_half", "bottom_right"]
    _TIER3_STRATS = ["bw_otsu", "high_contrast"]
    _TIER3_PSMS   = ["3", "6"]

    _TIMEOUT_S = 15   # hard cap in seconds

    def __init__(self):
        self._tesseract_available = self._check_tesseract()

    def _check_tesseract(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR available")
            return True
        except Exception:
            logger.warning("Tesseract not installed — OCR unavailable")
            return False

    # ── Public extract entry point ───────────────────────────────────────────
    def extract_text(self, image_file) -> str:
        if not self._tesseract_available:
            return ""
        try:
            from PIL import Image
            import io
            if hasattr(image_file, "read"):
                image_file.seek(0)
                img = Image.open(image_file)
            elif isinstance(image_file, bytes):
                img = Image.open(io.BytesIO(image_file))
            else:
                img = image_file
            img = img.convert("RGB")
            return self._extract(img)
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def _extract(self, img) -> str:
        w, h = img.size
        deadline = time.monotonic() + self._TIMEOUT_S

        # Pre-build all crop regions once
        crops = {
            "full":         img,
            "top_half":     img.crop((0, 0, w, h // 2)),
            "bottom_half":  img.crop((0, h // 2, w, h)),
            "bottom_left":  img.crop((0, int(h * 0.5), int(w * 0.45), h)),
            "bottom_right": img.crop((int(w * 0.5), int(h * 0.5), w, h)),
            "left_col":     img.crop((0, 0, w // 2, h)),
            "right_col":    img.crop((w // 2, 0, w, h)),
            "center":       img.crop((int(w*0.1), int(h*0.1), int(w*0.9), int(h*0.9))),
        }

        best_score = -1
        best_text  = ""

        def try_combo(crop_name, strategy, psm) -> bool:
            """Try one combination. Returns True if we should stop (early exit)."""
            nonlocal best_score, best_text
            if time.monotonic() > deadline:
                logger.warning("OCR: timeout hit, returning best so far")
                return True
            processed = self._preprocess(crops[crop_name].copy(), strategy)
            text = self._tesseract_extract(processed, psm)
            if not text:
                return False
            score = _score_text(text)
            if score > best_score:
                best_score = score
                best_text  = text
                logger.debug(f"OCR: {crop_name}/{strategy}/psm{psm} → score={score}")
            # Early exit when confident
            if best_score >= _HIGH_SCORE:
                logger.info(f"OCR: early exit at score={best_score} ({crop_name}/{strategy}/psm{psm})")
                return True
            return False

        # ── TIER 1: fast path ────────────────────────────────────────────────
        for crop in self._TIER1_CROPS:
            for strat in self._TIER1_STRATS:
                for psm in self._TIER1_PSMS:
                    if try_combo(crop, strat, psm):
                        return self._finalize(best_text, best_score)

        # If tier 1 already gave a usable result (score >= MIN), return it
        if best_score >= _MIN_SCORE:
            logger.info(f"OCR: tier 1 sufficient (score={best_score})")
            return self._finalize(best_text, best_score)

        # ── TIER 2: add more crops + dark-bg ────────────────────────────────
        for crop in self._TIER2_CROPS:
            for strat in self._TIER2_STRATS:
                for psm in self._TIER2_PSMS:
                    if try_combo(crop, strat, psm):
                        return self._finalize(best_text, best_score)

        if best_score >= _MIN_SCORE:
            logger.info(f"OCR: tier 2 sufficient (score={best_score})")
            return self._finalize(best_text, best_score)

        # ── TIER 3: exhaustive (only when score still low) ───────────────────
        for crop in self._TIER3_CROPS:
            for strat in self._TIER3_STRATS:
                for psm in self._TIER3_PSMS:
                    if try_combo(crop, strat, psm):
                        return self._finalize(best_text, best_score)

        logger.info(f"OCR: all tiers done, best score={best_score}")
        return self._finalize(best_text, best_score)

    # ── Finalization ─────────────────────────────────────────────────────────
    def _finalize(self, text: str, score: int) -> str:
        if not text:
            return ""
        extracted = self._extract_ingredient_section(text)
        if extracted and len(extracted) > 30:
            return extracted
        if score >= _MIN_SCORE:
            return self._clean_ocr_output(text)
        return ""

    # ── Preprocessing ─────────────────────────────────────────────────────────
    def _preprocess(self, img, strategy: str):
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            import numpy as np

            img = img.convert("RGB")
            w, h = img.size

            # Upscale to minimum resolution for good OCR accuracy
            min_px = 1600   # slightly lower than v3 for speed (was 1800)
            if max(w, h) < min_px:
                scale = min_px / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

            gray = img.convert("L")
            arr  = __import__("numpy").array(gray)

            if strategy == "adaptive_dark":
                if arr.mean() < 100:       # dark background — invert
                    arr = 255 - arr
                    gray = Image.fromarray(arr)
                gray = ImageEnhance.Contrast(gray).enhance(3.0)
                gray = ImageEnhance.Sharpness(gray).enhance(3.0)
                return gray

            elif strategy == "high_contrast":
                gray = ImageEnhance.Contrast(gray).enhance(2.5)
                gray = ImageEnhance.Sharpness(gray).enhance(2.0)
                return gray

            elif strategy == "grayscale":
                gray = ImageEnhance.Contrast(gray).enhance(2.0)
                gray = gray.filter(ImageFilter.SHARPEN)
                return gray

            elif strategy == "bw_otsu":
                if arr.mean() < 128:
                    arr = 255 - arr
                threshold = int(arr.mean())
                arr = ((arr > threshold) * 255).astype("uint8")
                return Image.fromarray(arr)

            return gray
        except Exception:
            return img

    # ── Tesseract call ────────────────────────────────────────────────────────
    def _tesseract_extract(self, img, psm: str = "6") -> str:
        try:
            import pytesseract
            text = pytesseract.image_to_string(img, config=f"--psm {psm} -l eng --oem 3")
            return self._clean_ocr_output(text)
        except Exception:
            return ""

    # ── Ingredient section extraction ─────────────────────────────────────────
    def _extract_ingredient_section(self, text: str) -> str:
        if not text:
            return ""
        # Try INGREDIENTS: ... CONTAINS: anchor
        patterns = [
            r"(?i)ingredients?\s*:?\s*(.*?)(?=\bcontains\s*:\s*milk|\bnutrition\s+facts|\bbaking\s+inst|$)",
            r"(?i)ingredients?\s*:?\s*(.*?)(?=\ballergen|\bmanufactured|\bpacked|\*percent|$)",
            r"(?i)ingredients?\s*:?\s*(.*)",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
            if m:
                section = m.group(1).strip()
                if len(section) > 30:
                    cleaned = self._clean_ingredient_section(section)
                    if cleaned:
                        return cleaned
        # Backward from CONTAINS: anchor
        m2 = re.search(r"(?i)(.*?)\bcontains\s*:\s*(milk|soy|wheat|eggs|peanut)", text, re.DOTALL)
        if m2:
            before = m2.group(1)
            section = before[-1500:].strip()
            if _score_text(section) >= _MIN_SCORE:
                return self._clean_ingredient_section(section)
        return ""

    # ── Text cleaning ─────────────────────────────────────────────────────────
    def _clean_ingredient_section(self, text: str) -> str:
        text = re.sub(r"[^\x20-\x7E\n]", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n+", " ", text)
        text = re.sub(r"\b\w{1,1}\b", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip(" .,;:-")

    def _clean_ocr_output(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"[^\x20-\x7E\n]", " ", text)
        text = text.replace("|", "I").replace("  ", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 2]
        return " ".join(lines).strip()

    # ── Garbled text detection ────────────────────────────────────────────────
    def is_garbled(self, text: str) -> bool:
        """True if OCR output looks like noise rather than real ingredient text."""
        if not text or len(text) < 20:
            return True
        words = text.split()
        word_count = len(words)
        if word_count == 0:
            return True
        real_words   = [w for w in words if len(re.sub(r"[^a-zA-Z]", "", w)) >= 3]
        real_ratio   = len(real_words) / word_count
        score        = _score_text(text)
        # % after digit = percentage, not noise
        noise_chars  = re.findall(r"(?<![0-9])[%]|[}{|@#$^&*~`<>\\]", text)
        noise_ratio  = len(noise_chars) / max(len(text), 1)
        avg_word_len = sum(len(w) for w in real_words) / max(len(real_words), 1)
        garbled_pat  = re.compile(
            r"(?<![a-zA-Z0-9(])[a-z]{0,2}[}>{@#][a-z0-9}>{@#]*"
            r"|(?<![\w(])\b[a-z]\b(?![\w)])",
            re.IGNORECASE,
        )
        garbled_ratio = len(garbled_pat.findall(text)) / max(word_count, 1)

        if noise_ratio  > 0.015: return True
        if real_ratio   < 0.50:  return True
        if garbled_ratio > 0.20: return True
        if score < 2 and word_count > 15: return True
        if avg_word_len < 2.5 and word_count > 10: return True
        return False

    @property
    def available(self) -> bool:
        return self._tesseract_available
