"""Markdown ↔️ TipTap JSON conversion utilities.

Export:  blocks (DB rows) → Markdown string
Import:  Markdown string → list of block dicts (type + TipTap JSON content)
"""

import re


def json_to_text(content: dict) -> str:
    """Extract plain text from TipTap JSON."""
    if not content or not isinstance(content, dict):
        return ""
    nodes = content.get("content", [])
    if not nodes:
        return ""
    texts = []
    for node in nodes:
        if node.get("type") == "text":
            texts.append(node.get("text", ""))
        elif node.get("content"):
            texts.append(json_to_text(node))
    return "".join(texts)


def text_to_tiptap_json(text: str, node_type: str = "paragraph") -> dict:
    """Wrap plain text in a minimal TipTap JSON document structure."""
    return {
        "type": "doc",
        "content": [
            {
                "type": node_type,
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def blocks_to_markdown(blocks: list) -> str:
    """Convert a list of Block ORM objects to a Markdown string.

    Each block has: .type (str), .content (dict — TipTap JSON)
    """
    lines: list[str] = []
    for block in blocks:
        text = json_to_text(block.content)
        bt = block.type

        if bt == "heading_1":
            lines.append(f"# {text}")
        elif bt == "heading_2":
            lines.append(f"## {text}")
        elif bt == "heading_3":
            lines.append(f"### {text}")
        elif bt == "bullet_list":
            lines.append(f"- {text}")
        elif bt == "numbered_list":
            lines.append(f"1. {text}")
        elif bt == "code":
            lines.append("```")
            lines.append(text)
            lines.append("```")
        elif bt == "quote":
            lines.append(f"> {text}")
        elif bt == "divider":
            lines.append("---")
        else:  # paragraph
            lines.append(text)

        lines.append("")  # blank line between blocks

    return "\n".join(lines).rstrip("\n") + "\n"


def markdown_to_blocks(md_text: str) -> list[dict]:
    """Parse Markdown text into a list of block dicts.

    Returns list of dicts like: {"type": "heading_1", "content": {...}}
    """
    blocks: list[dict] = []
    lines = md_text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip empty lines
        if not line.strip():
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            node_type = {"p": "paragraph"}.get(
                f"h{level}", f"heading_{level}"
            )
            # heading_1/2/3 → the tiptap node type is "heading"
            blocks.append({
                "type": f"heading_{level}",
                "content": text_to_tiptap_json(text, "heading"),
            })
            i += 1
            continue

        # Bullet list
        if re.match(r"^[-*+]\s+", line):
            text = re.sub(r"^[-*+]\s+", "", line)
            blocks.append({
                "type": "bullet_list",
                "content": text_to_tiptap_json(text, "bulletList"),
            })
            i += 1
            continue

        # Numbered list
        if re.match(r"^\d+\.\s+", line):
            text = re.sub(r"^\d+\.\s+", "", line)
            blocks.append({
                "type": "numbered_list",
                "content": text_to_tiptap_json(text, "orderedList"),
            })
            i += 1
            continue

        # Blockquote
        if line.startswith("> "):
            text = line[2:].strip()
            blocks.append({
                "type": "quote",
                "content": text_to_tiptap_json(text, "blockquote"),
            })
            i += 1
            continue

        # Divider
        if re.match(r"^[-*_]{3,}$", line.strip()):
            blocks.append({
                "type": "divider",
                "content": {"type": "doc", "content": [{"type": "horizontalRule"}]},
            })
            i += 1
            continue

        # Code block
        if line.strip().startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing ```
            code_text = "\n".join(code_lines)
            blocks.append({
                "type": "code",
                "content": text_to_tiptap_json(code_text, "codeBlock"),
            })
            continue

        # Paragraph (default)
        blocks.append({
            "type": "paragraph",
            "content": text_to_tiptap_json(line.strip()),
        })
        i += 1

    return blocks
