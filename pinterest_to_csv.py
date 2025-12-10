
import csv
import re
import ast
import unicodedata
from pathlib import Path

# Input/Output files (same directory as this script)
INPUT_FILE = Path(__file__).with_name("pinterest_updated.txt")
OUTPUT_FILE = Path(__file__).with_name("pins.csv")

# ---- Emoji handling ----

def is_emoji_char(ch: str) -> bool:
    """
    Heuristic to detect emoji-like characters without external packages.
    Covers common emoji blocks and symbols. Not perfect, but robust for typical emoji.
    """
    if not ch:
        return False
    cp = ord(ch)

    # Variation selector & joiner used in emoji sequences; treat them as emoji for replacement
    if cp in (0x200D, 0xFE0E, 0xFE0F):
        return True

    # Skin tone modifiers
    if 0x1F3FB <= cp <= 0x1F3FF:
        return True

    # Emoticons, transport, map symbols, pictographs, supplemental symbols
    emoji_blocks = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Misc Symbols & Pictographs
        (0x1F680, 0x1F6FF),  # Transport & Map
        (0x1F900, 0x1F9FF),  # Supplemental Symbols & Pictographs
        (0x1FA00, 0x1FAFF),  # Symbols & Pictographs Extended-A
        (0x1F1E6, 0x1F1FF),  # Regional Indicator Symbols (flags)
        (0x2600,  0x26FF),   # Misc Symbols (includes ☀️ etc.)
        (0x2700,  0x27BF),   # Dingbats
    ]
    for start, end in emoji_blocks:
        if start <= cp <= end:
            return True

    # Fallback: other symbols (So) in higher planes often used for emoji-like glyphs
    if unicodedata.category(ch) == "So" and cp >= 0x1F000:
        return True

    return False

def replace_emojis_with_space(s: str) -> str:
    """Replace any emoji-like character with a single space and collapse multiple spaces."""
    if not s:
        return ""
    # Replace emoji chars with space
    out = "".join((" " if is_emoji_char(ch) else ch) for ch in s)
    # Collapse consecutive spaces
    out = re.sub(r"\s+", " ", out).strip()
    return out

# ---- Sanitizers ----

def strip_trailing_commas(s: str) -> str:
    """Remove any commas/spaces at the very end of the string."""
    if s is None:
        return ""
    return re.sub(r"[,\s]+$", "", s)

def remove_all_commas(s: str) -> str:
    """Remove ALL commas from the string (for CSV safety)."""
    if s is None:
        return ""
    return s.replace(",", "")

def to_na_if_empty(s: str) -> str:
    """Return 'NA' if empty, else the string as-is."""
    if s is None:
        return "NA"
    s = s.strip()
    return "NA" if s == "" else s

def sanitize_value(s: str) -> str:
    """
    Sanitization pipeline:
      1) Emoji → " "
      2) Trim
      3) Remove trailing commas
      4) Convert 'No data' -> 'NA'
      5) Remove ALL commas
      6) Collapse whitespace
      7) If empty, -> 'NA'
    """
    if s is None:
        return "NA"
    s = replace_emojis_with_space(s)
    s = strip_trailing_commas(s.strip())
    if s.lower() == "no data":
        return "NA"
    s = remove_all_commas(s)
    s = re.sub(r"\s+", " ", s).strip()
    return to_na_if_empty(s)

def parse_bool(s: str) -> str:
    """
    Normalize booleans:
      - 'True' -> 'true'
      - 'False' -> 'false'
      - Anything else (including 'No data' or blank) -> 'NA'
    Also removes commas, emojis, trailing commas, and collapses spaces.
    """
    if s is None:
        return "NA"
    s = replace_emojis_with_space(s)
    s = strip_trailing_commas(s).strip()
    s = remove_all_commas(s).lower()
    if s == "true":
        return "true"
    if s == "false":
        return "false"
    return "NA"

def parse_story_pin_media(s: str) -> str:
    """
    Accepts:
      - 'No data'
      - Literal list like: [{'image': '...'}, {'image': '...'}]
    Returns:
      - Pipe-separated image ids: "id1|id2|id3"
      - 'NA' if none
    """
    if s is None:
        return "NA"
    s = replace_emojis_with_space(s)
    s = strip_trailing_commas(s).strip()
    if s.lower() == "no data":
        return "NA"

    # Try to extract the Python-literal list block safely
    try:
        m = re.search(r"(\[.*\])", s, flags=re.DOTALL)
        if m:
            data = ast.literal_eval(m.group(1))
            if isinstance(data, list):
                images = []
                for item in data:
                    if isinstance(item, dict) and "image" in item:
                        img = sanitize_value(str(item["image"]))
                        if img != "NA":
                            images.append(img)
                return "|".join(images) if images else "NA"
    except Exception:
        # Fallback: continue below
        pass

    # Fallback path only if the literal_eval failed or no list was found
    imgs = re.findall(r"'image':\s*'([^']+)'", s)
    imgs = [sanitize_value(i) for i in imgs if i]
    imgs = [i for i in imgs if i != "NA"]
    if imgs:
        return "|".join(imgs)

    return "NA"

def normalize_field_name(name: str):
    """Map raw label to CSV column name."""
    mapping = {
        "title": "title",
        "details": "details",
        "board name": "board_name",
        "created at": "created_at",
        "alive": "alive",
    }
    return mapping.get(name.lower().strip())

CSV_FIELDS = ["title", "details", "board_name", "created_at", "alive"]

# ---- Read source text ----
if not INPUT_FILE.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    lines = f.read().strip().splitlines()

records = []
current = {f: "NA" for f in CSV_FIELDS}  # default NA for all fields

def has_data(rec: dict) -> bool:
    """Does this record have any non-NA field?"""
    return any((rec.get(k) or "NA") != "NA" for k in CSV_FIELDS)

# ---- Parse ----
for raw in lines:
    line = raw.strip()

    # Blank line = record boundary (if something accumulated)
    if not line:
        if has_data(current):
            records.append(current)
            current = {f: "NA" for f in CSV_FIELDS}
        continue

    # Parse "Key: Value"
    if ":" in line:
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        csv_key = normalize_field_name(key)
        if not csv_key:
            # Unknown key: ignore
            continue

        # If a new Title starts but we already have data, flush previous record first
        if csv_key == "title" and has_data(current):
            records.append(current)
            current = {f: "NA" for f in CSV_FIELDS}

        if csv_key == "alive":
            current[csv_key] = parse_bool(val)
        elif csv_key == "story_pin_media":
            current[csv_key] = parse_story_pin_media(val)
        else:
            current[csv_key] = sanitize_value(val)

    else:
        # Non "Key: Value" line — treat as continuation of Details if Details already started
        if current["details"] != "NA":
            current["details"] = sanitize_value(f"{current['details']} {line}")

# Push the final record if anything is present
if has_data(current):
    records.append(current)

# ---- Write CSV ----
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    writer.writeheader()
    for rec in records:
        safe = {}
        for k in CSV_FIELDS:
            v = rec.get(k, "NA")
            val = v if isinstance(v, str) else ("" if v is None else str(v))
            # Final safety: emoji → space, strip trailing commas, remove commas, NA if empty
            val = replace_emojis_with_space(val)
            val = strip_trailing_commas(val)
            val = remove_all_commas(val)
            val = to_na_if_empty(val)
            safe[k] = val
        writer.writerow(safe)

print(f"✅ Wrote {OUTPUT_FILE} with {len(records)} rows. Emojis replaced by space; missing fields set to 'NA'; no commas inside cells.")
