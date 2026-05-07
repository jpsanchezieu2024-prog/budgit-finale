"""
Budgit — OCR receipt parser using Google Cloud Vision API.

Supports Spanish supermarkets: Mercadona, Lidl, Carrefour, Dia, Al Campo, Aldi.

Uses document_text_detection (not text_detection) to get bounding box
coordinates for every word. This lets us reconstruct the table structure
of a receipt — pairing each product name with the price on the same row —
regardless of the order Vision reads the columns.

Flow:
    1. Receive image bytes from Streamlit file_uploader
    2. Send to Google Vision API (DOCUMENT_TEXT_DETECTION)
    3. Extract every word with its Y midpoint coordinate
    4. Group words into rows by Y proximity
    5. Within each row: left side = product name, right side = price
    6. Filter out header/footer noise
    7. Fuzzy-match against the user's cart items by name + price
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
# Noise filters
# ---------------------------------------------------------------------------
_NOISE_RE = re.compile(
    r"^(total|subtotal|iva|base\s*imponible|cuota|4%|10%|21%"
    r"|p\.?\s*unit|importe|descripci[oó]n"
    r"|mercadona|lidl|carrefour|d[ií]a|alcampo|aldi"
    r"|c\/|avda|calle|tel[eé]f|www\.|http|cif|nif"
    r"|op:|factura|simplificada|tarjeta|bancaria|efectivo|cambio"
    r"|puntos|socio|cliente|gracias|ticket"
    r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"
    r"|\d{2}:\d{2}"
    r"|a-\d+)",
    re.IGNORECASE,
)

_PRICE_RE = re.compile(r"^\d{1,3}[.,]\d{2}$")


# ---------------------------------------------------------------------------
# Core: extract words with coordinates
# ---------------------------------------------------------------------------
def _extract_words_with_coords(image_bytes: bytes) -> list[dict]:
    """
    Call Vision document_text_detection and return a flat list of:
        {"text": "LECHE", "x": 120, "y": 340}

    x = horizontal midpoint of the word's bounding box
    y = vertical midpoint of the word's bounding box
    """
    client = _get_vision_client()
    image = vision.Image(content=image_bytes)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")

    words = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    text = "".join(s.text for s in word.symbols)
                    verts = word.bounding_box.vertices
                    xs = [v.x for v in verts]
                    ys = [v.y for v in verts]
                    x = sum(xs) / len(xs)
                    y = sum(ys) / len(ys)
                    words.append({"text": text, "x": x, "y": y})

    return words


# ---------------------------------------------------------------------------
# Group words into rows by Y proximity
# ---------------------------------------------------------------------------
def _group_into_rows(words: list[dict], y_tolerance: int = 12) -> list[list[dict]]:
    """
    Group words that share approximately the same Y coordinate into rows.
    Words within y_tolerance pixels of each other are on the same line.
    Returns rows sorted top-to-bottom, each row sorted left-to-right.
    """
    if not words:
        return []

    sorted_words = sorted(words, key=lambda w: w["y"])
    rows = []
    current_row = [sorted_words[0]]

    for word in sorted_words[1:]:
        if abs(word["y"] - current_row[-1]["y"]) <= y_tolerance:
            current_row.append(word)
        else:
            rows.append(sorted(current_row, key=lambda w: w["x"]))
            current_row = [word]

    if current_row:
        rows.append(sorted(current_row, key=lambda w: w["x"]))

    return rows


# ---------------------------------------------------------------------------
# Extract product/price pairs from rows
# ---------------------------------------------------------------------------
def _rows_to_items(rows: list[list[dict]], image_width: float) -> list[dict]:
    """
    For each row:
    - The rightmost word that looks like a price IS the price
    - Everything to the left of it is the product name
    - Skip rows that are noise (headers, totals, store info)
    """
    price_zone_x = image_width * 0.60 if image_width > 0 else float("inf")
    items = []

    for row in rows:
        price_val = None
        price_word_idx = None

        for i, word in enumerate(row):
            if _PRICE_RE.match(word["text"]) and word["x"] >= price_zone_x:
                price_str = word["text"].replace(",", ".")
                try:
                    p = float(price_str)
                    if 0.10 <= p <= 200.0:
                        # Keep the rightmost valid price
                        price_val = p
                        price_word_idx = i
                except ValueError:
                    pass

        if price_val is None:
            continue

        # Product name = all words to the left of the price word
        name_words = [w["text"] for w in row[:price_word_idx]]
        if not name_words:
            continue

        name_raw = " ".join(name_words).strip()

        # Skip noise rows
        if _NOISE_RE.match(name_raw):
            continue

        # Extract leading quantity (e.g. "2 SALSA TIKKA" → qty=2)
        qty = 1
        qty_match = re.match(r"^(\d+)\s+(.{2,})$", name_raw)
        if qty_match:
            qty = int(qty_match.group(1))
            name_raw = qty_match.group(2)

        # Remove leading item codes
        name_raw = re.sub(r"^\d{4,}\s*", "", name_raw)
        name = name_raw.strip().lower()

        if len(name) < 2:
            continue

        items.append({"name": name, "price": price_val, "qty": qty})

    return items


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------
def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match_receipt_to_cart(
    receipt_items: list[dict],
    cart_items: list[dict],
    name_threshold: float = 0.30,
    price_tolerance: float = 0.10,
) -> dict:
    """
    Match receipt items to cart items using name similarity and price proximity.
    Name threshold is kept low to handle abbreviated receipt names vs
    user-entered names (e.g. "paté r.med. salmón" vs "paté salmón").
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

            price_diff = abs(r_item["price"] - float(c_item["price"]))
            if price_diff > price_tolerance:
                continue

            name_score = _similarity(r_item["name"], c_key)
            if name_score < name_threshold:
                continue

            combined = name_score * 2 + (1.0 - price_diff)
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
# Main entry point
# ---------------------------------------------------------------------------
def process_receipt(image_bytes: bytes, cart_items: list[dict]) -> dict:
    """
    Full pipeline: image bytes → bounding box extraction → row grouping
    → product/price pairing → fuzzy match against cart.
    """
    try:
        words = _extract_words_with_coords(image_bytes)
    except Exception as e:
        return {
            "error":             str(e),
            "raw_text":          "",
            "receipt_items":     [],
            "verified":          [],
            "unmatched_receipt": [],
            "unmatched_cart":    cart_items,
        }

    if not words:
        return {
            "error":             "No text detected in image.",
            "raw_text":          "",
            "receipt_items":     [],
            "verified":          [],
            "unmatched_receipt": [],
            "unmatched_cart":    cart_items,
        }

    # Reconstruct raw text for debug display
    raw_text = " ".join(
        w["text"] for w in sorted(words, key=lambda w: (w["y"], w["x"]))
    )

    image_width = max(w["x"] for w in words) if words else 0
    rows = _group_into_rows(words)
    receipt_items = _rows_to_items(rows, image_width)

    result = match_receipt_to_cart(receipt_items, cart_items)
    result["raw_text"] = raw_text
    result["receipt_items"] = receipt_items
    result["error"] = None
    return result
