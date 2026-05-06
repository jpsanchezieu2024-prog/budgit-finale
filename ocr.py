"""
Budgit — OCR receipt parser using Google Cloud Vision API.

Supports Spanish supermarkets: Mercadona, Lidl, Carrefour, Dia, Al Campo, Aldi.

Flow:
    1. Receive image bytes from Streamlit file_uploader
    2. Send to Google Vision API (TEXT_DETECTION)
    3. Parse the raw text into (name, price) pairs
    4. Fuzzy-match against the user's cart items
    5. Return matched and unmatched results for UI display
"""

import io
import json
import os
import re
from difflib import SequenceMatcher

from google.cloud import vision
from google.oauth2 import service_account


# ---------------------------------------------------------------------------
# Client setup — reuse the same FIREBASE_KEY_JSON credential
# ---------------------------------------------------------------------------
def _get_vision_client():
    """
    Build a Vision API client from the same service account used for
    Firebase. Tries GOOGLE_APPLICATION_CREDENTIALS_JSON first (Railway),
    then falls back to FIREBASE_KEY_JSON, then to ADC.
    """
    raw = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON") or \
          os.environ.get("FIREBASE_KEY_JSON")

    if raw:
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return vision.ImageAnnotatorClient(credentials=creds)

    # Local dev: use application default credentials
    return vision.ImageAnnotatorClient()


# ---------------------------------------------------------------------------
# Core OCR call
# ---------------------------------------------------------------------------
def extract_text_from_image(image_bytes: bytes) -> str:
    """
    Send image bytes to Google Vision and return the raw detected text.
    Raises RuntimeError if the API call fails.
    """
    client = _get_vision_client()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    texts = response.text_annotations
    if not texts:
        return ""

    # The first annotation is the full document text
    return texts[0].description


# ---------------------------------------------------------------------------
# Receipt line parser
#
# Spanish supermarket receipts generally follow one of two layouts:
#
#   PRODUCT NAME          1,29
#   PRODUCT NAME   1 x   1,29
#
# Prices use comma as decimal separator (European format).
# We ignore lines that look like totals, taxes, headers, or store metadata.
# ---------------------------------------------------------------------------

# Lines to skip — common receipt noise in Spanish supermarkets
_SKIP_PATTERNS = [
    r"^(total|subtotal|iva|imp|ticket|factura|gracias|fecha|hora|cajero"
    r"|tarjeta|efectivo|cambio|cif|nif|tel[eé]fono|www\.|http"
    r"|mercadona|lidl|carrefour|d[ií]a|alcampo|al campo|aldi"
    r"|supermercado|hipermercado|c\/|avda|calle|plaza"
    r"|visa|mastercard|contactless|n[uú]mero|referencia"
    r"|op\.|terminal|aut\.|importe|entregado|devuelto"
    r"|puntos|socio|cliente|member)",
    r"^\*+$",
    r"^-+$",
    r"^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}",   # dates
    r"^\d{2}:\d{2}",                            # times
    r"^\d{10,}",                                # barcodes / long numbers
]
_SKIP_RE = re.compile("|".join(_SKIP_PATTERNS), re.IGNORECASE)

# Price pattern: optional qty, optional "x", then the price
# Handles: 1,29 / 1.29 / 2 x 1,29 / 1 ud 0,99
_PRICE_RE = re.compile(
    r"(?:(\d+)\s*[xXuU][dD]?\s*)?"   # optional qty like "2 x" or "1 ud"
    r"(\d{1,3}[.,]\d{2})"            # price like 1,29 or 12.99
    r"\s*(?:€|eur?)?\s*$",
    re.IGNORECASE,
)


def parse_receipt_lines(raw_text: str) -> list[dict]:
    """
    Parse raw OCR text from Spanish supermarket receipts.

    Strategy:
    1. Find the product section — starts after "descripcion" header,
       ends before "total"
    2. Within that section, separate product name lines from price lines
    3. Zip them together by position
    """
    _STANDALONE_PRICE_RE = re.compile(
        r"^(\d{1,3}[.,]\d{2})\s*(?:€)?$"
    )
    _PRODUCT_WITH_QTY_RE = re.compile(
        r"^(\d+)\s+(.{3,})$"
    )
    _SECTION_START_RE = re.compile(
        r"^(descripci[oó]n|description)$", re.IGNORECASE
    )
    _SECTION_END_RE = re.compile(
        r"^(total|subtotal|tarjeta|efectivo|p\.?\s*unit|importe)", re.IGNORECASE
    )
    _NOISE_RE = re.compile(
        r"^(iva|base|cuota|4%|10%|21%|p\.?\s*unit|importe|descripci|"
        r"mercadona|lidl|carrefour|d[ií]a|alcampo|aldi|"
        r"c\/|avda|calle|tel[eé]f|www\.|http|cif|nif|"
        r"op:|factura|simplificada|tarjeta|bancaria|"
        r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        re.IGNORECASE
    )

    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    # Find the product section boundaries
    start_idx = 0
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if _SECTION_START_RE.match(line):
            start_idx = i + 1
        if i > start_idx and _SECTION_END_RE.match(line):
            end_idx = i
            break

    product_section = lines[start_idx:end_idx]

    # Separate into product name lines and price lines
    product_lines = []
    price_lines = []

    for line in product_section:
        if _NOISE_RE.match(line):
            continue

        m_price = _STANDALONE_PRICE_RE.match(line)
        if m_price:
            price_str = m_price.group(1).replace(",", ".")
            try:
                price = float(price_str)
                if 0.10 <= price <= 200.0:
                    price_lines.append(price)
            except ValueError:
                pass
            continue

        # Skip very short lines or pure numbers
        if len(line) < 3 or re.match(r"^\d+$", line):
            continue

        product_lines.append(line)

    # Zip products with prices by position
    items = []
    for product_line, price in zip(product_lines, price_lines):
        qty = 1
        name_raw = product_line
        m_qty = _PRODUCT_WITH_QTY_RE.match(product_line)
        if m_qty:
            qty = int(m_qty.group(1))
            name_raw = m_qty.group(2)
        name = re.sub(r"^\d{4,}\s*", "", name_raw).strip().lower()
        if len(name) >= 2:
            items.append({"name": name, "price": price, "qty": qty})

    return items


# ---------------------------------------------------------------------------
# Fuzzy matching — receipt items vs cart items
# ---------------------------------------------------------------------------
def _similarity(a: str, b: str) -> float:
    """Return a 0-1 similarity score between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_receipt_to_cart(
    receipt_items: list[dict],
    cart_items: list[dict],
    name_threshold: float = 0.30,
    price_tolerance: float = 0.20,
) -> dict:
    """
    Fuzzy-match receipt items against cart items.

    Returns:
    {
        "verified":   [{"cart_name": ..., "receipt_name": ..., "price": ...}, ...],
        "unmatched_receipt": [...],   # on receipt but not in cart
        "unmatched_cart":   [...],    # in cart but not on receipt
    }

    A match requires:
      - Name similarity >= name_threshold  (fuzzy, handles abbreviations)
      - Price within price_tolerance (€)   (handles minor OCR digit errors)
    """
    verified = []
    unmatched_receipt = []
    matched_cart_keys = set()

    for r_item in receipt_items:
        best_score = 0.0
        best_cart = None

        for c_item in cart_items:
            c_key = c_item["name"].lower().strip()
            if c_key in matched_cart_keys:
                continue

            name_score = _similarity(r_item["name"], c_key)
            price_diff = abs(r_item["price"] - float(c_item["price"]))

            if name_score >= name_threshold and price_diff <= price_tolerance:
                combined = name_score - (price_diff * 0.1)
                if combined > best_score:
                    best_score = combined
                    best_cart = c_item

        if best_cart is not None:
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
# Main entry point called from the Shop page
# ---------------------------------------------------------------------------
def process_receipt(image_bytes: bytes, cart_items: list[dict]) -> dict:
    """
    Full pipeline: image bytes → OCR → parse → match against cart.

    Returns the same dict as match_receipt_to_cart, plus:
        "raw_text":      the full OCR string (for debug display)
        "receipt_items": all parsed receipt lines before matching
        "error":         None or an error string if something failed
    """
    try:
        raw_text = extract_text_from_image(image_bytes)
    except Exception as e:
        return {
            "error":             str(e),
            "raw_text":          "",
            "receipt_items":     [],
            "verified":          [],
            "unmatched_receipt": [],
            "unmatched_cart":    cart_items,
        }

    receipt_items = parse_receipt_lines(raw_text)
    result = match_receipt_to_cart(receipt_items, cart_items)
    result["raw_text"] = raw_text
    result["receipt_items"] = receipt_items
    result["error"] = None
    return result
