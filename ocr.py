"""
Budgit — OCR receipt parser using Google Cloud Vision API.

Supports Spanish supermarkets: Mercadona, Lidl, Carrefour, Dia, Al Campo, Aldi.

Since Vision reads receipts in unpredictable column orders, this parser:
1. Extracts ALL valid prices from the receipt
2. Extracts ALL product name lines from the receipt
3. Anchors to the product section (between Descripcion and TOTAL)
4. Matches cart items to receipt prices using price as primary key
   (name similarity used only as tiebreaker when prices clash)
"""

import json
import os
import re
from difflib import SequenceMatcher

from google.cloud import vision
from google.oauth2 import service_account


# ---------------------------------------------------------------------------
# Client setup
# ---------------------------------------------------------------------------
def _get_vision_client():
    raw = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or \
          os.environ.get("FIREBASE_KEY_JSON")
    if raw:
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return vision.ImageAnnotatorClient(credentials=creds)
    return vision.ImageAnnotatorClient()


# ---------------------------------------------------------------------------
# Noise patterns — lines to discard entirely
# ---------------------------------------------------------------------------
_NOISE_RE = re.compile(
    r"^(total|subtotal|iva|base|cuota|4%|10%|21%"
    r"|p\.?\s*unit|importe|descripci[oó]n"
    r"|mercadona|lidl|carrefour|d[ií]a|alcampo|aldi"
    r"|c\/|avda|calle|tel[eé]f|www\.|http|cif|nif"
    r"|op:|factura|simplificada|tarjeta|bancaria|efectivo|cambio"
    r"|puntos|socio|cliente|gracias|ticket|alginet|bosch|elvira"
    r"|teléfono|imponible|s\.a\.|cuota"
    r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"  # dates
    r"|\d{2}:\d{2}"                          # times
    r"|\d{9,}"                               # long numbers/barcodes
    r"|a-\d+)",
    re.IGNORECASE,
)

_PRICE_RE = re.compile(r"^(\d{1,3})[.,](\d{2})$")

# Known product section boundaries
_SECTION_START_RE = re.compile(r"descripci[oó]n", re.IGNORECASE)
_SECTION_END_RE   = re.compile(r"^(total\b|tarjeta|efectivo|importe)", re.IGNORECASE)


def _parse_price(text: str) -> float | None:
    m = _PRICE_RE.match(text.strip())
    if not m:
        return None
    try:
        val = float(f"{m.group(1)}.{m.group(2)}")
        return val if 0.10 <= val <= 200.0 else None
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# OCR — plain text extraction
# ---------------------------------------------------------------------------
def extract_text_from_image(image_bytes: bytes) -> str:
    client = _get_vision_client()
    image  = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")
    texts = response.text_annotations
    return texts[0].description if texts else ""


# ---------------------------------------------------------------------------
# Parse: extract product names and prices separately then reconcile
# ---------------------------------------------------------------------------
def parse_receipt_lines(raw_text: str) -> list[dict]:
    """
    Robust parser for Spanish supermarket receipts.

    Because Vision reads two-column receipts unpredictably, we:
    1. Find the product section (Descripción → TOTAL)
    2. Collect product name lines and standalone price lines separately
    3. Zip them positionally within the section

    This works whether Vision reads all names then all prices,
    or interleaves them in chunks.
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # -----------------------------------------------------------------------
    # Step 1: find section boundaries
    # -----------------------------------------------------------------------
    start_idx = 0
    end_idx   = len(lines)

    for i, line in enumerate(lines):
        if _SECTION_START_RE.search(line):
            start_idx = i + 1
        if i > start_idx and _SECTION_END_RE.match(line):
            end_idx = i
            break

    section = lines[start_idx:end_idx]

    # -----------------------------------------------------------------------
    # Step 2: separate product lines from price lines
    # -----------------------------------------------------------------------
    _QTY_PRODUCT_RE = re.compile(r"^(\d+)\s+(.{2,})$")
    _PURE_NUMBER_RE = re.compile(r"^\d+$")

    product_lines: list[str] = []
    price_values:  list[float] = []

    for line in section:
        # Skip noise
        if _NOISE_RE.match(line):
            continue

        # Is it a standalone price?
        price = _parse_price(line)
        if price is not None:
            price_values.append(price)
            continue

        # Is it a line of ONLY numbers (qty digits floating alone)?
        if _PURE_NUMBER_RE.match(line):
            continue

        # Very short lines are noise
        if len(line) < 3:
            continue

        product_lines.append(line)

    # -----------------------------------------------------------------------
    # Step 3: zip products with prices by position
    # -----------------------------------------------------------------------
    items: list[dict] = []
    for product_line, price in zip(product_lines, price_values):
        qty     = 1
        name_raw = product_line

        m_qty = _QTY_PRODUCT_RE.match(product_line)
        if m_qty:
            qty      = int(m_qty.group(1))
            name_raw = m_qty.group(2)

        # Strip leading item codes
        name_raw = re.sub(r"^\d{4,}\s*", "", name_raw)
        name     = name_raw.strip().lower()

        if len(name) < 2:
            continue

        items.append({"name": name, "price": price, "qty": qty})

    return items


# ---------------------------------------------------------------------------
# Matching: cart items vs receipt items
#
# Primary key  = price (must be within €0.15)
# Secondary key = name similarity (tiebreaker only)
#
# When two cart items share a price, the one whose name is most similar
# to the receipt line wins. This covers the edge case of identical prices.
# ---------------------------------------------------------------------------
def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_receipt_to_cart(
    receipt_items: list[dict],
    cart_items:    list[dict],
    price_tolerance: float = 0.15,
    name_threshold:  float = 0.20,
) -> dict:
    verified          = []
    unmatched_receipt = []
    matched_cart_keys: set[str] = set()

    for r_item in receipt_items:
        candidates = []

        for c_item in cart_items:
            c_key = c_item["name"].lower().strip()
            if c_key in matched_cart_keys:
                continue

            price_diff = abs(r_item["price"] - float(c_item["price"]))
            if price_diff > price_tolerance:
                continue

            name_score = _similarity(r_item["name"], c_key)
            candidates.append((name_score, price_diff, c_item))

        if not candidates:
            unmatched_receipt.append(r_item)
            continue

        # Sort by name similarity DESC, then price diff ASC
        candidates.sort(key=lambda t: (-t[0], t[1]))
        best_name_score, _, best_cart = candidates[0]

        # Accept if name has any similarity OR if it's the only price match
        if best_name_score >= name_threshold or len(candidates) == 1:
            matched_cart_keys.add(best_cart["name"].lower().strip())
            verified.append({
                "cart_name":    best_cart["name"],
                "receipt_name": r_item["name"],
                "price":        r_item["price"],
                "qty":          r_item["qty"],
            })
        else:
            unmatched_receipt.append(r_item)

    unmatched_cart = [
        c for c in cart_items
        if c["name"].lower().strip() not in matched_cart_keys
    ]

    return {
        "verified":          verified,
        "unmatched_receipt": unmatched_receipt,
        "unmatched_cart":    unmatched_cart,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def process_receipt(image_bytes: bytes, cart_items: list[dict]) -> dict:
    try:
        raw_text = extract_text_from_image(image_bytes)
    except Exception as e:
        return {
            "error": str(e), "raw_text": "", "receipt_items": [],
            "verified": [], "unmatched_receipt": [], "unmatched_cart": cart_items,
        }

    if not raw_text:
        return {
            "error": "No text detected in image.", "raw_text": "", "receipt_items": [],
            "verified": [], "unmatched_receipt": [], "unmatched_cart": cart_items,
        }

    receipt_items = parse_receipt_lines(raw_text)
    result        = match_receipt_to_cart(receipt_items, cart_items)
    result["raw_text"]      = raw_text
    result["receipt_items"] = receipt_items
    result["error"]         = None
    return result