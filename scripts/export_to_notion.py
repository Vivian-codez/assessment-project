#!/usr/bin/env python3
"""Verism AI -> Notion Workspace Automated Exporter

This script parses all structured Markdown documentation files in `notion_docs/`
and automatically creates a nested Notion documentation hub in your Notion workspace
using the official Notion REST API.

Features:
  - Supports native Notion blocks: Tables, Callouts, Headings, Code blocks, Dividers,
    Bulleted lists, Numbered lists, and Rich Text with bold/inline code formatting.
  - Automatically creates a top-level workspace page if no parent page is provided.
  - Handles Notion API 100-block payload chunking & exponential backoff on rate limits.
"""

import os
import sys
import re
import json
import time
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

NOTION_VERSION = "2022-06-28"

DOCS_DIR = Path(__file__).resolve().parent.parent / "notion_docs"


def clean_page_id(raw_id: str) -> str:
    """Extract and format a UUID from raw ID or full Notion URL."""
    raw_id = raw_id.strip()
    if "/" in raw_id:
        raw_id = raw_id.split("/")[-1].split("?")[0]
    match = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F-]{36})", raw_id)
    if match:
        clean = match.group(1).replace("-", "")
        return f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"
    return raw_id


def notion_api_call(endpoint: str, token: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"https://api.notion.com/v1/{endpoint.lstrip('/')}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    for attempt in range(6):
        try:
            with urllib.request.urlopen(req) as resp:
                res_body = resp.read().decode("utf-8")
                return json.loads(res_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            if e.code == 429:
                wait_time = (attempt + 1) * 2.5
                print(f"  ⏳ Notion API rate limited. Backing off for {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            raise RuntimeError(f"Notion API error [{e.code}]: {err_body}") from e
        except Exception as e:
            if attempt < 5:
                time.sleep(2)
                continue
            raise e
    raise RuntimeError("Failed after multiple attempts to communicate with Notion API.")


def parse_inline_formatting(text: str) -> List[Dict[str, Any]]:
    """Parse text with bold (**text**), inline code (`code`), or links into rich_text elements."""
    if not text:
        return []
    text = text[:1990]  # Notion 2000 character limit

    # Regex to split on bold or inline code
    pattern = re.compile(r"(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))")
    parts = pattern.split(text)
    rich_text_list: List[Dict[str, Any]] = []

    for part in parts:
        if not part:
            continue
        # Bold
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            content = part[2:-2]
            rich_text_list.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"bold": True}
            })
        # Inline code
        elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
            content = part[1:-1]
            rich_text_list.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True}
            })
        # Link [text](url)
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            link_match = re.match(r"^\[(.*?)\]\((.*?)\)$", part)
            if link_match:
                anchor_text, link_url = link_match.group(1), link_match.group(2)
                # If local file link, just show text without broken local scheme
                if link_url.startswith("file://") or link_url.endswith(".md"):
                    rich_text_list.append({
                        "type": "text",
                        "text": {"content": anchor_text},
                        "annotations": {"bold": True}
                    })
                else:
                    rich_text_list.append({
                        "type": "text",
                        "text": {"content": anchor_text, "link": {"url": link_url}}
                    })
            else:
                rich_text_list.append({"type": "text", "text": {"content": part}})
        else:
            rich_text_list.append({"type": "text", "text": {"content": part}})

    return rich_text_list if rich_text_list else [{"type": "text", "text": {"content": text}}]


def is_table_divider(line: str) -> bool:
    """Check if line is a markdown table separator (e.g. | :--- | :--- |)."""
    cleaned = line.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    return len(cleaned) == 0 and ("-" in line)


def parse_table_row(line: str) -> List[str]:
    """Split a markdown table row line into cells."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return cells


def markdown_to_blocks(md_content: str) -> List[Dict[str, Any]]:
    """Convert a markdown document into Notion API block objects."""
    blocks: List[Dict[str, Any]] = []
    lines = md_content.splitlines()
    in_code_block = False
    code_lang = "plain text"
    code_lines: List[str] = []

    # Table accumulation
    in_table = False
    table_rows: List[List[str]] = []

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        
        # Calculate max columns
        width = max(len(r) for r in table_rows)
        if width == 0:
            in_table = False
            table_rows = []
            return

        # Build Notion table_row blocks
        row_blocks = []
        for r in table_rows:
            # Pad row to table width
            padded = r + [""] * (width - len(r))
            cells = [parse_inline_formatting(cell) for cell in padded]
            row_blocks.append({
                "type": "table_row",
                "table_row": {"cells": cells}
            })

        blocks.append({
            "object": "block",
            "type": "table",
            "table": {
                "table_width": width,
                "has_column_header": True,
                "has_row_header": False,
                "children": row_blocks
            }
        })
        in_table = False
        table_rows = []

    idx = 0
    total_lines = len(lines)

    while idx < total_lines:
        line = lines[idx]
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith("```"):
            if in_table:
                flush_table()

            if in_code_block:
                full_code = "\n".join(code_lines)[:1990]
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": full_code}}],
                        "language": code_lang,
                    }
                })
                in_code_block = False
                code_lines = []
            else:
                in_code_block = True
                raw_lang = stripped[3:].strip().lower()
                lang_map = {
                    "python": "python",
                    "py": "python",
                    "javascript": "javascript",
                    "js": "javascript",
                    "typescript": "typescript",
                    "ts": "typescript",
                    "json": "json",
                    "sql": "sql",
                    "bash": "bash",
                    "sh": "bash",
                    "shell": "bash",
                    "yaml": "yaml",
                    "yml": "yaml",
                    "dockerfile": "dockerfile",
                    "html": "html",
                    "css": "css",
                    "mermaid": "mermaid",
                    "markdown": "markdown",
                }
                code_lang = lang_map.get(raw_lang, "plain text")
            idx += 1
            continue

        if in_code_block:
            code_lines.append(line)
            idx += 1
            continue

        # Check for Markdown Table lines (starts and ends with |)
        if stripped.startswith("|") and stripped.endswith("|"):
            if is_table_divider(stripped):
                # Ignore table alignment divider
                idx += 1
                continue
            in_table = True
            table_rows.append(parse_table_row(stripped))
            idx += 1
            continue
        elif in_table:
            flush_table()

        if not stripped:
            idx += 1
            continue

        # Skip top-level H1 heading as it's set as the page title
        if stripped.startswith("# ") and len(blocks) == 0:
            idx += 1
            continue

        # Headings
        if stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": parse_inline_formatting(stripped[4:])}
            })
        elif stripped.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": parse_inline_formatting(stripped[3:])}
            })
        elif stripped.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": parse_inline_formatting(stripped[2:])}
            })
        # Horizontal Divider
        elif stripped in ("---", "***", "___"):
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
        # Callouts / Blockquotes
        elif stripped.startswith("> "):
            callout_text = stripped[2:].strip()
            # Select relevant emoji
            icon = "💡"
            if "🛡️" in callout_text or "FERPA" in callout_text or "Security" in callout_text:
                icon = "🛡️"
            elif "⚠️" in callout_text or "Warning" in callout_text:
                icon = "⚠️"
            elif "📌" in callout_text:
                icon = "📌"
            elif "🏷️" in callout_text:
                icon = "🏷️"
            elif "🎯" in callout_text:
                icon = "🎯"
            elif "⚡" in callout_text:
                icon = "⚡"

            blocks.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": parse_inline_formatting(callout_text),
                    "icon": {"type": "emoji", "emoji": icon}
                }
            })
        # Bullet Lists
        elif stripped.startswith("- ") or stripped.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_inline_formatting(stripped[2:])}
            })
        # Numbered Lists
        elif re.match(r"^\d+\.\s+", stripped):
            item_text = re.sub(r"^\d+\.\s+", "", stripped)
            blocks.append({
                "object": "block",
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": parse_inline_formatting(item_text)}
            })
        # Fallback paragraph
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": parse_inline_formatting(stripped)}
            })

        idx += 1

    if in_table:
        flush_table()

    return blocks


def create_notion_page(token: str, parent_spec: Dict[str, Any], title: str, blocks: List[Dict[str, Any]], icon: str = "📄") -> str:
    """Create a page in Notion, uploading blocks in chunks to adhere to Notion's API limits."""
    # Notion allows max 100 blocks on creation
    initial_chunk = blocks[:90]
    remaining_chunks = blocks[90:]

    payload = {
        "parent": parent_spec,
        "icon": {"type": "emoji", "emoji": icon},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        "children": initial_chunk
    }

    resp = notion_api_call("pages", token, method="POST", payload=payload)
    page_id = resp["id"]

    # Append any remaining blocks in batches of 90
    while remaining_chunks:
        chunk = remaining_chunks[:90]
        remaining_chunks = remaining_chunks[90:]
        time.sleep(0.4)
        notion_api_call(
            f"blocks/{page_id}/children",
            token,
            method="PATCH",
            payload={"children": chunk}
        )

    return page_id


def extract_title_and_icon(md_content: str, fallback_title: str) -> Tuple[str, str]:
    """Extract page title and leading emoji from first markdown H1 line."""
    for line in md_content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            raw = line[2:].strip()
            # Check for leading emoji
            match = re.match(r"^([\U00010000-\U0010ffff]|\u26a0|\u2705|\u274c|\ud83c[\udf00-\udfff]|\ud83d[\udc00-\ude4f]|\ud83e[\udd00-\udfff])\s*", raw)
            if match:
                icon = match.group(1)
                title = raw[len(match.group(0)):].strip()
                return title, icon
            return raw, "📄"
    return fallback_title, "📄"


def main():
    parser = argparse.ArgumentParser(description="Export Verism AI documentation to Notion Workspace")
    parser.add_argument("--token", default=os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN"), help="Notion Integration Token")
    parser.add_argument("--parent-page", default=os.getenv("NOTION_PAGE_ID"), help="Target Parent Page ID in Notion (Optional)")
    token = args.token or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")

    if not token:
        print("❌ Error: Missing Notion Integration Token.")
        sys.exit(1)

    print("🔑 Authenticating with Notion API...")

    # Determine parent target (Top-level workspace or specific page)
    if args.parent_page and args.parent_page.lower() != "workspace":
        parent_id = clean_page_id(args.parent_page)
        print(f"🎯 Target parent page provided: {parent_id}")
        parent_spec = {"page_id": parent_id}
    else:
        print("🌐 Creating documentation hub directly at top-level workspace...")
        parent_spec = {"type": "workspace", "workspace": True}

    md_files = sorted(DOCS_DIR.glob("*.md"))
    if not md_files:
        print(f"❌ No markdown files found in {DOCS_DIR}")
        sys.exit(1)

    # 1. Create Root Hub Page
    hub_file = DOCS_DIR / "00_NOTION_WORKSPACE_HUB.md"
    sub_files = [f for f in md_files if f.name != "00_NOTION_WORKSPACE_HUB.md"]

    if hub_file.exists():
        hub_content = hub_file.read_text(encoding="utf-8")
        hub_title, hub_icon = extract_title_and_icon(hub_content, "Verism AI — Engineering & Product Workspace")
        hub_blocks = markdown_to_blocks(hub_content)
        print(f"\n📦 Creating Workspace Hub: {hub_icon} {hub_title} ({len(hub_blocks)} blocks)...")
        hub_page_id = create_notion_page(token, parent_spec, hub_title, hub_blocks, icon=hub_icon)
        print(f"   ✅ Created Hub Page: https://notion.so/{hub_page_id.replace('-', '')}")
    else:
        raise FileNotFoundError("00_NOTION_WORKSPACE_HUB.md is required as root hub.")

    # 2. Upload all subpages nested under the Hub
    subpage_parent = {"page_id": hub_page_id}
    print(f"\n📂 Uploading {len(sub_files)} sub-pages under Hub...")

    for idx, f in enumerate(sub_files, 1):
        content = f.read_text(encoding="utf-8")
        title, icon = extract_title_and_icon(content, f.stem)
        blocks = markdown_to_blocks(content)
        print(f" [{idx}/{len(sub_files)}] Uploading {icon} {title} ({len(blocks)} blocks)...")
        try:
            sub_id = create_notion_page(token, subpage_parent, title, blocks, icon=icon)
            print(f"       ↳ Page created: https://notion.so/{sub_id.replace('-', '')}")
        except Exception as e:
            print(f"       ⚠️ Error uploading {f.name}: {e}")
        time.sleep(0.5)

    print("\n" + "=" * 70)
    print("🎉 SUCCESS! Verism AI project documentation is now live in Notion!")
    print(f"🔗 Master Workspace Hub URL: https://notion.so/{hub_page_id.replace('-', '')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
