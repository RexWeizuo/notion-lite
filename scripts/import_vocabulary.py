"""
Import 3742 vocabulary words into notion-lite.

Hierarchy:
  201 (top-level)
    └─ 单词模块
         ├─ 📖 A  (word pages)
         ├─ 📖 B
         └─ ... 📖 Z

Each word = one Page with one Block containing all content as a single TipTap doc.
"""
import json
import sys
import time
import urllib.request
import urllib.error

BASE = "http://localhost:8123/api"


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status == 204:
                return None
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()[:200]
        print(f"  ERROR {method} {path}: {e.code} {err_body}")
        raise


def make_text_node(text):
    """Create a TipTap text node."""
    return {"type": "text", "text": text}


def make_heading(text, level=3):
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [make_text_node(text)],
    }


def make_paragraph(text):
    return {
        "type": "paragraph",
        "content": [make_text_node(text)],
    }


def make_bullet(text):
    return {
        "type": "bulletList",
        "content": [{"type": "listItem", "content": [{"type": "paragraph", "content": [make_text_node(text)]}]}],
    }


def make_blockquote(text):
    return {
        "type": "blockquote",
        "content": [{"type": "paragraph", "content": [make_text_node(text)]}],
    }


def word_to_doc(w):
    """Convert a word dict to a single TipTap doc with all content nodes."""
    nodes = []

    # Phonetic + POS as heading
    phonetic = w.get("phonetic", "")
    pos = w.get("pos", "")
    header = f"{phonetic}  {pos}".strip()
    if header:
        nodes.append(make_heading(header, 3))

    # Chinese meaning
    cm = w.get("chinese_meaning", "")
    if cm:
        nodes.append(make_paragraph(f"🇨🇳 {cm}"))

    # English meaning
    em = w.get("english_meaning", "")
    if em:
        nodes.append(make_paragraph(f"🇬🇧 {em}"))

    # Divider
    if cm or em:
        nodes.append({"type": "horizontalRule"})

    # Synonyms
    syns = w.get("synonyms", [])
    if syns:
        nodes.append(make_bullet(f"📎 同义词: {', '.join(syns)}"))

    # Antonyms
    ants = w.get("antonyms", [])
    if ants:
        nodes.append(make_bullet(f"🚫 反义词: {', '.join(ants)}"))

    # Example sentences
    examples = w.get("example_sentences", [])
    if examples:
        nodes.append(make_heading("📝 例句", 3))
        for ex in examples[:5]:
            nodes.append(make_blockquote(ex))

    # Collocations
    colls = w.get("collocations", [])
    if colls:
        nodes.append(make_heading("🔗 搭配", 3))
        for col in colls[:5]:
            nodes.append(make_bullet(col))

    # Root/affix
    root = w.get("root_affix", "")
    if root:
        nodes.append(make_paragraph(f"📐 词根词缀: {root}"))

    # Exam frequency
    freq = w.get("exam_frequency", 0)
    if freq:
        nodes.append(make_paragraph(f"📊 考频: {freq}"))

    if not nodes:
        nodes.append(make_paragraph("(无数据)"))

    return {"type": "doc", "content": nodes}


def main():
    with open("/mnt/d/study/kaoyan-english/data/words.json", "r") as f:
        words = json.load(f)

    print(f"Loaded {len(words)} words")

    # --- Step 1: Create hierarchy ---
    print("Creating folder structure...")
    proj_201 = api("POST", "/pages", {"title": "201", "icon": "📘"})
    print(f"  201: {proj_201['id']}")

    vocab_module = api("POST", "/pages", {
        "title": "单词模块",
        "icon": "📖",
        "parent_page_id": proj_201["id"],
    })
    print(f"  单词模块: {vocab_module['id']}")

    # Create 26 letter folders under 单词模块
    letter_pages = {}
    for code in range(ord('A'), ord('Z') + 1):
        letter = chr(code)
        page = api("POST", "/pages", {
            "title": f"📖 {letter}",
            "icon": "📖",
            "parent_page_id": vocab_module["id"],
        })
        letter_pages[letter] = page["id"]

    print(f"  26 letter folders created under 单词模块")

    # --- Step 2: Import words ---
    total = len(words)
    batch_start = time.time()
    errors = 0

    print(f"Importing {total} words...")

    for i, w in enumerate(words):
        word_text = w["word"]
        first_char = word_text[0].upper()
        if first_char < 'A' or first_char > 'Z':
            first_char = 'A'

        parent_id = letter_pages.get(first_char, letter_pages['A'])

        try:
            # Create page
            page = api("POST", "/pages", {
                "title": word_text,
                "parent_page_id": parent_id,
            })
            pid = page["id"]

            # Create ONE block with all content
            doc = word_to_doc(w)
            api("POST", f"/pages/{pid}/blocks", {
                "type": "paragraph",
                "content": doc,
            })

            # Progress every 100 words
            if (i + 1) % 100 == 0:
                elapsed = time.time() - batch_start
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{total}] {word_text}  ({rate:.0f} w/s, ETA {remaining:.0f}s)")

        except Exception as e:
            errors += 1
            print(f"  FAILED [{i+1}] {word_text}: {e}")
            if errors > 20:
                print("Too many errors, aborting.")
                sys.exit(1)

    elapsed = time.time() - batch_start
    print(f"\n✅ Done! {total} words in {elapsed:.0f}s ({total/elapsed:.1f} w/s)")
    if errors:
        print(f"⚠️  {errors} errors")


if __name__ == "__main__":
    main()
