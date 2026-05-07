"""
Import 408 TOC files into notion-lite as page hierarchies.

Parses os_toc_ocr.txt → 408/操作系统/...
Parses cs_toc_ocr.txt → 408/计算机组成原理/...

Hierarchy:
  ### 第X章       → Chapter page
  X.Y title      → Section page (child of chapter)
  - 一、title    → Topic page (child of section) — exercises go here later
    - （一）sub  → Block in topic page
    - 【补充】   → Block in topic page
"""
import json
import re
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


def parse_toc(filepath):
    """Parse TOC file into nested structure.
    Returns list of chapters: [{title, sections: [{title, topics: [{title, blocks: [str]}]}]}]
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chapters = []
    current_chapter = None
    current_section = None
    current_topic = None

    for line in lines:
        line = line.rstrip("\r\n")
        if not line.strip():
            continue

        # ### 第X章 ...
        m = re.match(r"^###\s+(.+)$", line)
        if m:
            current_chapter = {"title": m.group(1).strip(), "sections": []}
            chapters.append(current_chapter)
            current_section = None
            current_topic = None
            continue

        # X.Y title
        m = re.match(r"^(\d+\.\d+)\s+(.+)$", line)
        if m:
            if current_chapter is None:
                continue
            title = f"{m.group(1)} {m.group(2).strip()}"
            current_section = {"title": title, "topics": []}
            current_chapter["sections"].append(current_section)
            current_topic = None
            continue

        # - 一、title
        m = re.match(r"^-\s+([一二三四五六七八九十]+)[、，]\s*(.+)$", line)
        if m:
            if current_section is None:
                continue
            title = f"{m.group(1)}、{m.group(2).strip()}"
            current_topic = {"title": title, "blocks": []}
            current_section["topics"].append(current_topic)
            continue

        #   - （一）sub  or   - 【补充】sub
        clean = line.strip()
        if clean.startswith("-") and current_topic is not None:
            sub = re.sub(r"^-\s*", "", clean).strip()
            current_topic["blocks"].append(sub)

    return chapters


def import_toc(filepath, parent_page_id):
    """Import a TOC file under a parent page."""
    chapters = parse_toc(filepath)
    total = sum(len(ch["sections"]) for ch in chapters)
    section_count = 0

    for ch in chapters:
        print(f"  📁 {ch['title']}")
        ch_page = api("POST", "/pages", {
            "title": ch["title"],
            "icon": "📁",
            "parent_page_id": parent_page_id,
        })

        for sec in ch["sections"]:
            sec_page = api("POST", "/pages", {
                "title": sec["title"],
                "icon": "📄",
                "parent_page_id": ch_page["id"],
            })

            for topic in sec["topics"]:
                topic_page = api("POST", "/pages", {
                    "title": topic["title"],
                    "parent_page_id": sec_page["id"],
                })

                # Create child pages for sub-topics
                for sub in topic["blocks"]:
                    api("POST", "/pages", {
                        "title": sub,
                        "parent_page_id": topic_page["id"],
                    })

            section_count += 1
            if section_count % 10 == 0:
                print(f"    [{section_count}/{total}] sections done")

    return section_count


def main():
    print("=== Importing 408 TOC files ===")

    # Create 408 root
    p408 = api("POST", "/pages", {"title": "408", "icon": "📘"})
    print(f"408 root: {p408['id']}")

    # OS
    print("\n--- 操作系统 ---")
    os_page = api("POST", "/pages", {
        "title": "操作系统",
        "icon": "💻",
        "parent_page_id": p408["id"],
    })
    os_count = import_toc("/mnt/d/study/408/os_toc_ocr.txt", os_page["id"])

    # CS
    print("\n--- 计算机组成原理 ---")
    cs_page = api("POST", "/pages", {
        "title": "计算机组成原理",
        "icon": "🖥️",
        "parent_page_id": p408["id"],
    })
    cs_count = import_toc("/mnt/d/study/408/cs_toc_ocr.txt", cs_page["id"])

    print(f"\n✅ Done! OS: {os_count} sections, CS: {cs_count} sections")


if __name__ == "__main__":
    main()
