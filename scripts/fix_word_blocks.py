"""
Fix words with incomplete blocks (from old import script).
Re-imports only words that have < 3 content nodes in their block.
"""
import json
import urllib.request

BASE = "http://localhost:8123/api"
with open("/mnt/d/study/kaoyan-english/data/words.json") as f:
    words_data = {w["word"]: w for w in json.load(f)}


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        if resp.status == 204:
            return None
        return json.loads(resp.read().decode())


def mt(text):
    return {"type": "text", "text": text}


def word_to_doc(w):
    nodes = []
    ph = w.get("phonetic", "")
    ps = w.get("pos", "")
    header = f"{ph}  {ps}".strip()
    if header:
        nodes.append({"type": "heading", "attrs": {"level": 3}, "content": [mt(header)]})
    cm = w.get("chinese_meaning", "")
    if cm:
        nodes.append({"type": "paragraph", "content": [mt(f"🇨🇳 {cm}")]})
    em = w.get("english_meaning", "")
    if em:
        nodes.append({"type": "paragraph", "content": [mt(f"🇬🇧 {em}")]})
    if cm or em:
        nodes.append({"type": "horizontalRule"})
    syns = w.get("synonyms", [])
    if syns:
        nodes.append({"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [mt(f"📎 同义词: {', '.join(syns)}")]}]}
        ]})
    ants = w.get("antonyms", [])
    if ants:
        nodes.append({"type": "bulletList", "content": [
            {"type": "listItem", "content": [{"type": "paragraph", "content": [mt(f"🚫 反义词: {', '.join(ants)}")]}]}
        ]})
    examples = w.get("example_sentences", [])
    if examples:
        nodes.append({"type": "heading", "attrs": {"level": 3}, "content": [mt("📝 例句")]})
        for ex in examples[:5]:
            nodes.append({"type": "blockquote", "content": [{"type": "paragraph", "content": [mt(ex)]}]})
    colls = w.get("collocations", [])
    if colls:
        nodes.append({"type": "heading", "attrs": {"level": 3}, "content": [mt("🔗 搭配")]})
        for col in colls[:5]:
            nodes.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": [mt(col)]}]}
            ]})
    root = w.get("root_affix", "")
    if root:
        nodes.append({"type": "paragraph", "content": [mt(f"📐 词根词缀: {root}")]})
    freq = w.get("exam_frequency", 0)
    if freq:
        nodes.append({"type": "paragraph", "content": [mt(f"📊 考频: {freq}")]})
    if not nodes:
        nodes.append({"type": "paragraph", "content": [mt("(无数据)")]})
    return {"type": "doc", "content": nodes}


# Get all word pages under 还没学习
vocab_id = "5945d45968a1"
notyet = [p for p in api("GET", "/pages/tree") if p["title"] == "201"]
if notyet:
    for c in notyet[0].get("children", []):
        if c["title"] == "单词模块":
            for cc in c.get("children", []):
                if cc["title"] == "还没学习":
                    notyet_id = cc["id"]
                    break

# Actually, let's query by parent_page_id directly
# Get all pages under 还没学习
import sys

all_pages = api("GET", "/pages/tree")
notyet_id = None
for p in all_pages:
    if p["title"] == "201":
        for c in p.get("children", []):
            if c["title"] == "单词模块":
                for cc in c.get("children", []):
                    if cc["title"] == "还没学习":
                        notyet_id = cc["id"]

if not notyet_id:
    print("ERROR: 还没学习 folder not found")
    sys.exit(1)

# Get all word pages
word_pages = []
for p in all_pages:
    if p["title"] == "201":
        for c in p.get("children", []):
            if c["title"] == "单词模块":
                for cc in c.get("children", []):
                    if cc["title"] == "还没学习":
                        word_pages = cc.get("children", [])
                        break

print(f"Checking {len(word_pages)} words in 还没学习...")
fixed = 0
for wp in word_pages:
    blocks = api("GET", f"/pages/{wp['id']}/blocks")
    if not blocks:
        continue
    nodes = blocks[0].get("content", {}).get("content", [])
    
    # Check if word has enough content
    has_cn = any(n.get("type") == "paragraph" and 
                 any(c.get("text","").startswith("🇨🇳") for c in (n.get("content") or []))
                 for n in nodes)
    
    if not has_cn and wp["title"] in words_data:
        # Fix: delete existing blocks, recreate
        for b in blocks:
            api("DELETE", f"/pages/{wp['id']}/blocks/{b['id']}")
        doc = word_to_doc(words_data[wp["title"]])
        api("POST", f"/pages/{wp['id']}/blocks", {"type": "paragraph", "content": doc})
        fixed += 1
        if fixed % 50 == 0:
            print(f"  Fixed {fixed} words...")

print(f"Fixed {fixed} words with incomplete blocks")
