#!/usr/bin/env python3
# Docstring explaining Verism AI -> Notion Workspace Automated Exporter
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

# Import module os
import os
# Import module sys
import sys
# Import module re
import re
# Import module json
import json
# Import module time
import time
# Import module argparse
import argparse
# Import module urllib.request
import urllib.request
# Import module urllib.error
import urllib.error
# Import Path from pathlib
from pathlib import Path
# Import List, Dict, Any, Optional, Tuple from typing
from typing import List, Dict, Any, Optional, Tuple

# Check if condition: sys.platform == "win32"
if sys.platform == "win32":
    # Import module io
    import io
    # Set sys.stdout to io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    # Set sys.stderr to io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Set NOTION_VERSION to "2022-06-28"
NOTION_VERSION = "2022-06-28"

# Set DOCS_DIR to Path(__file__).resolve().parent.parent / "notion_docs"
DOCS_DIR = Path(__file__).resolve().parent.parent / "notion_docs"


# Define function clean_page_id
def clean_page_id(raw_id: str) -> str:
    # Docstring explaining Extract and format a UUID from raw ID or full Notion URL.
    """Extract and format a UUID from raw ID or full Notion URL."""
    # Set raw_id to raw_id.strip()
    raw_id = raw_id.strip()
    # Check if condition: "/" in raw_id
    if "/" in raw_id:
        # Set raw_id to raw_id.split("/")[-1].split("?")[0]
        raw_id = raw_id.split("/")[-1].split("?")[0]
    # Set match to re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F-]{36})", raw_id)
    match = re.search(r"([0-9a-fA-F]{32}|[0-9a-fA-F-]{36})", raw_id)
    # Check if condition: match
    if match:
        # Set clean to match.group(1).replace("-", "")
        clean = match.group(1).replace("-", "")
        # Return value: f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"
        return f"{clean[0:8]}-{clean[8:12]}-{clean[12:16]}-{clean[16:20]}-{clean[20:32]}"
    # Return value: raw_id
    return raw_id


# Define function notion_api_call
def notion_api_call(endpoint: str, token: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Set url to f"https://api.notion.com/v1/{endpoint.lstrip('/')}"
    url = f"https://api.notion.com/v1/{endpoint.lstrip('/')}"
    # Set headers to {
    headers = {
        # Define field entry: "Authorization": f"Bearer {token}"
        "Authorization": f"Bearer {token}",
        # Define field entry: "Notion-Version": NOTION_VERSION
        "Notion-Version": NOTION_VERSION,
        # Define field entry: "Content-Type": "application/json"
        "Content-Type": "application/json",
    }
    # Set data to json.dumps(payload).encode("utf-8") if payload is not None else None
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    # Set req to urllib.request.Request(url, data=data, headers=headers, method=method)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    # Loop over items: attempt in range(6)
    for attempt in range(6):
        # Begin try block to handle operations safely
        try:
            # Manage execution context with urllib.request.urlopen(req) as resp
            with urllib.request.urlopen(req) as resp:
                # Set res_body to resp.read().decode("utf-8")
                res_body = resp.read().decode("utf-8")
                # Return value: json.loads(res_body)
                return json.loads(res_body)
        # Handle exception during execution: except urllib.error.HTTPError as e
        except urllib.error.HTTPError as e:
            # Set err_body to e.read().decode("utf-8")
            err_body = e.read().decode("utf-8")
            # Check if condition: e.code == 429
            if e.code == 429:
                # Set wait_time to (attempt + 1) * 2.5
                wait_time = (attempt + 1) * 2.5
                # Print console output: print(f"  ⏳ Notion API rate limited. Backing off for {wait_time:.1f}s...")
                print(f"  ⏳ Notion API rate limited. Backing off for {wait_time:.1f}s...")
                # Execute statement: time.sleep(wait_time)
                time.sleep(wait_time)
                # Continue to next loop iteration
                continue
            # Raise exception: RuntimeError(f"Notion API error [{e.code}]: {err_body}") from e
            raise RuntimeError(f"Notion API error [{e.code}]: {err_body}") from e
        # Handle exception during execution: except Exception as e
        except Exception as e:
            # Check if condition: attempt < 5
            if attempt < 5:
                # Execute statement: time.sleep(2)
                time.sleep(2)
                # Continue to next loop iteration
                continue
            # Raise exception: e
            raise e
    # Raise exception: RuntimeError("Failed after multiple attempts to communicate with Notion API.")
    raise RuntimeError("Failed after multiple attempts to communicate with Notion API.")


# Define function parse_inline_formatting
def parse_inline_formatting(text: str) -> List[Dict[str, Any]]:
    # Docstring explaining Parse text with bold (**text**), inline code (`code`), or li
    """Parse text with bold (**text**), inline code (`code`), or links into rich_text elements."""
    # Check if condition: not text
    if not text:
        # Return value: []
        return []
    # Set text to text[:1990]  # Notion 2000 character limit
    text = text[:1990]  # Notion 2000 character limit

    # Regex to split on bold or inline code
    pattern = re.compile(r"(\*\*.*?\*\*|`.*?`|\[.*?\]\(.*?\))")
    # Set parts to pattern.split(text)
    parts = pattern.split(text)
    # Set rich_text_list: List[Dict[str, Any]] to []
    rich_text_list: List[Dict[str, Any]] = []

    # Loop over items: part in parts
    for part in parts:
        # Check if condition: not part
        if not part:
            # Continue to next loop iteration
            continue
        # Bold
        if part.startswith("**") and part.endswith("**") and len(part) >= 4:
            # Set content to part[2:-2]
            content = part[2:-2]
            # Execute statement: rich_text_list.append({
            rich_text_list.append({
                # Define field entry: "type": "text"
                "type": "text",
                # Define field entry: "text": {"content": content}
                "text": {"content": content},
                # Execute statement: "annotations": {"bold": True}
                "annotations": {"bold": True}
            # Execute statement: })
            })
        # Inline code
        elif part.startswith("`") and part.endswith("`") and len(part) >= 2:
            # Set content to part[1:-1]
            content = part[1:-1]
            # Execute statement: rich_text_list.append({
            rich_text_list.append({
                # Define field entry: "type": "text"
                "type": "text",
                # Define field entry: "text": {"content": content}
                "text": {"content": content},
                # Execute statement: "annotations": {"code": True}
                "annotations": {"code": True}
            # Execute statement: })
            })
        # Link [text](url)
        elif part.startswith("[") and "](" in part and part.endswith(")"):
            # Set link_match to re.match(r"^\[(.*?)\]\((.*?)\)$", part)
            link_match = re.match(r"^\[(.*?)\]\((.*?)\)$", part)
            # Check if condition: link_match
            if link_match:
                # Set anchor_text, link_url to link_match.group(1), link_match.group(2)
                anchor_text, link_url = link_match.group(1), link_match.group(2)
                # If local file link, just show text without broken local scheme
                if link_url.startswith("file://") or link_url.endswith(".md"):
                    # Execute statement: rich_text_list.append({
                    rich_text_list.append({
                        # Define field entry: "type": "text"
                        "type": "text",
                        # Define field entry: "text": {"content": anchor_text}
                        "text": {"content": anchor_text},
                        # Execute statement: "annotations": {"bold": True}
                        "annotations": {"bold": True}
                    # Execute statement: })
                    })
                # Execute alternate fallback branch
                else:
                    # Execute statement: rich_text_list.append({
                    rich_text_list.append({
                        # Define field entry: "type": "text"
                        "type": "text",
                        # Execute statement: "text": {"content": anchor_text, "link": {"url": link_url}}
                        "text": {"content": anchor_text, "link": {"url": link_url}}
                    # Execute statement: })
                    })
            # Execute alternate fallback branch
            else:
                # Execute statement: rich_text_list.append({"type": "text", "text": {"content": part}})
                rich_text_list.append({"type": "text", "text": {"content": part}})
        # Execute alternate fallback branch
        else:
            # Execute statement: rich_text_list.append({"type": "text", "text": {"content": part}})
            rich_text_list.append({"type": "text", "text": {"content": part}})

    # Return value: rich_text_list if rich_text_list else [{"type": "text", "text": {"content": text}}]
    return rich_text_list if rich_text_list else [{"type": "text", "text": {"content": text}}]


# Define function is_table_divider
def is_table_divider(line: str) -> bool:
    # Docstring explaining Check if line is a markdown table separator (e.g. | :--- | :
    """Check if line is a markdown table separator (e.g. | :--- | :--- |)."""
    # Set cleaned to line.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    cleaned = line.replace("|", "").replace("-", "").replace(":", "").replace(" ", "")
    # Return value: len(cleaned) == 0 and ("-" in line)
    return len(cleaned) == 0 and ("-" in line)


# Define function parse_table_row
def parse_table_row(line: str) -> List[str]:
    # Docstring explaining Split a markdown table row line into cells.
    """Split a markdown table row line into cells."""
    # Set cells to [c.strip() for c in line.strip().strip("|").split("|")]
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    # Return value: cells
    return cells


# Define function markdown_to_blocks
def markdown_to_blocks(md_content: str) -> List[Dict[str, Any]]:
    # Docstring explaining Convert a markdown document into Notion API block objects.
    """Convert a markdown document into Notion API block objects."""
    # Set blocks: List[Dict[str, Any]] to []
    blocks: List[Dict[str, Any]] = []
    # Set lines to md_content.splitlines()
    lines = md_content.splitlines()
    # Set in_code_block to False
    in_code_block = False
    # Set code_lang to "plain text"
    code_lang = "plain text"
    # Set code_lines: List[str] to []
    code_lines: List[str] = []

    # Table accumulation
    in_table = False
    # Set table_rows: List[List[str]] to []
    table_rows: List[List[str]] = []

    # Define function flush_table
    def flush_table():
        # Execute statement: nonlocal in_table, table_rows
        nonlocal in_table, table_rows
        # Check if condition: not table_rows
        if not table_rows:
            # Set in_table to False
            in_table = False
            # Return from function
            return
        
        # Calculate max columns
        width = max(len(r) for r in table_rows)
        # Check if condition: width == 0
        if width == 0:
            # Set in_table to False
            in_table = False
            # Set table_rows to []
            table_rows = []
            # Return from function
            return

        # Build Notion table_row blocks
        row_blocks = []
        # Loop over items: r in table_rows
        for r in table_rows:
            # Pad row to table width
            padded = r + [""] * (width - len(r))
            # Set cells to [parse_inline_formatting(cell) for cell in padded]
            cells = [parse_inline_formatting(cell) for cell in padded]
            # Execute statement: row_blocks.append({
            row_blocks.append({
                # Define field entry: "type": "table_row"
                "type": "table_row",
                # Execute statement: "table_row": {"cells": cells}
                "table_row": {"cells": cells}
            # Execute statement: })
            })

        # Execute statement: blocks.append({
        blocks.append({
            # Define field entry: "object": "block"
            "object": "block",
            # Define field entry: "type": "table"
            "type": "table",
            # Execute statement: "table": {
            "table": {
                # Define field entry: "table_width": width
                "table_width": width,
                # Define field entry: "has_column_header": True
                "has_column_header": True,
                # Define field entry: "has_row_header": False
                "has_row_header": False,
                # Execute statement: "children": row_blocks
                "children": row_blocks
            }
        # Execute statement: })
        })
        # Set in_table to False
        in_table = False
        # Set table_rows to []
        table_rows = []

    # Set idx to 0
    idx = 0
    # Set total_lines to len(lines)
    total_lines = len(lines)

    # Loop while condition holds: idx < total_lines
    while idx < total_lines:
        # Set line to lines[idx]
        line = lines[idx]
        # Set stripped to line.strip()
        stripped = line.strip()

        # Handle Code Blocks
        if stripped.startswith("```"):
            # Check if condition: in_table
            if in_table:
                # Execute statement: flush_table()
                flush_table()

            # Check if condition: in_code_block
            if in_code_block:
                # Set full_code to "\n".join(code_lines)[:1990]
                full_code = "\n".join(code_lines)[:1990]
                # Execute statement: blocks.append({
                blocks.append({
                    # Define field entry: "object": "block"
                    "object": "block",
                    # Define field entry: "type": "code"
                    "type": "code",
                    # Execute statement: "code": {
                    "code": {
                        # Define field entry: "rich_text": [{"type": "text", "text": {"content": full_code}}]
                        "rich_text": [{"type": "text", "text": {"content": full_code}}],
                        # Define field entry: "language": code_lang
                        "language": code_lang,
                    }
                # Execute statement: })
                })
                # Set in_code_block to False
                in_code_block = False
                # Set code_lines to []
                code_lines = []
            # Execute alternate fallback branch
            else:
                # Set in_code_block to True
                in_code_block = True
                # Set raw_lang to stripped[3:].strip().lower()
                raw_lang = stripped[3:].strip().lower()
                # Set lang_map to {
                lang_map = {
                    # Define field entry: "python": "python"
                    "python": "python",
                    # Define field entry: "py": "python"
                    "py": "python",
                    # Define field entry: "javascript": "javascript"
                    "javascript": "javascript",
                    # Define field entry: "js": "javascript"
                    "js": "javascript",
                    # Define field entry: "typescript": "typescript"
                    "typescript": "typescript",
                    # Define field entry: "ts": "typescript"
                    "ts": "typescript",
                    # Define field entry: "json": "json"
                    "json": "json",
                    # Define field entry: "sql": "sql"
                    "sql": "sql",
                    # Define field entry: "bash": "bash"
                    "bash": "bash",
                    # Define field entry: "sh": "bash"
                    "sh": "bash",
                    # Define field entry: "shell": "bash"
                    "shell": "bash",
                    # Define field entry: "yaml": "yaml"
                    "yaml": "yaml",
                    # Define field entry: "yml": "yaml"
                    "yml": "yaml",
                    # Define field entry: "dockerfile": "dockerfile"
                    "dockerfile": "dockerfile",
                    # Define field entry: "html": "html"
                    "html": "html",
                    # Define field entry: "css": "css"
                    "css": "css",
                    # Define field entry: "mermaid": "mermaid"
                    "mermaid": "mermaid",
                    # Define field entry: "markdown": "markdown"
                    "markdown": "markdown",
                }
                # Set code_lang to lang_map.get(raw_lang, "plain text")
                code_lang = lang_map.get(raw_lang, "plain text")
            # Execute statement: idx += 1
            idx += 1
            # Continue to next loop iteration
            continue

        # Check if condition: in_code_block
        if in_code_block:
            # Execute statement: code_lines.append(line)
            code_lines.append(line)
            # Execute statement: idx += 1
            idx += 1
            # Continue to next loop iteration
            continue

        # Check for Markdown Table lines (starts and ends with |)
        if stripped.startswith("|") and stripped.endswith("|"):
            # Check if condition: is_table_divider(stripped)
            if is_table_divider(stripped):
                # Ignore table alignment divider
                idx += 1
                # Continue to next loop iteration
                continue
            # Set in_table to True
            in_table = True
            # Execute statement: table_rows.append(parse_table_row(stripped))
            table_rows.append(parse_table_row(stripped))
            # Execute statement: idx += 1
            idx += 1
            # Continue to next loop iteration
            continue
        # Alternative condition check: in_table
        elif in_table:
            # Execute statement: flush_table()
            flush_table()

        # Check if condition: not stripped
        if not stripped:
            # Execute statement: idx += 1
            idx += 1
            # Continue to next loop iteration
            continue

        # Skip top-level H1 heading as it's set as the page title
        if stripped.startswith("# ") and len(blocks) == 0:
            # Execute statement: idx += 1
            idx += 1
            # Continue to next loop iteration
            continue

        # Headings
        if stripped.startswith("### "):
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "heading_3"
                "type": "heading_3",
                # Execute statement: "heading_3": {"rich_text": parse_inline_formatting(stripped[4:])}
                "heading_3": {"rich_text": parse_inline_formatting(stripped[4:])}
            # Execute statement: })
            })
        # Alternative condition check: stripped.startswith("## ")
        elif stripped.startswith("## "):
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "heading_2"
                "type": "heading_2",
                # Execute statement: "heading_2": {"rich_text": parse_inline_formatting(stripped[3:])}
                "heading_2": {"rich_text": parse_inline_formatting(stripped[3:])}
            # Execute statement: })
            })
        # Alternative condition check: stripped.startswith("# ")
        elif stripped.startswith("# "):
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "heading_1"
                "type": "heading_1",
                # Execute statement: "heading_1": {"rich_text": parse_inline_formatting(stripped[2:])}
                "heading_1": {"rich_text": parse_inline_formatting(stripped[2:])}
            # Execute statement: })
            })
        # Horizontal Divider
        elif stripped in ("---", "***", "___"):
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "divider"
                "type": "divider",
                # Execute statement: "divider": {}
                "divider": {}
            # Execute statement: })
            })
        # Callouts / Blockquotes
        elif stripped.startswith("> "):
            # Set callout_text to stripped[2:].strip()
            callout_text = stripped[2:].strip()
            # Select relevant emoji
            icon = "💡"
            # Check if condition: "🛡️" in callout_text or "FERPA" in callout_text or "Security" in callout_text
            if "🛡️" in callout_text or "FERPA" in callout_text or "Security" in callout_text:
                # Set icon to "🛡️"
                icon = "🛡️"
            # Alternative condition check: "⚠️" in callout_text or "Warning" in callout_text
            elif "⚠️" in callout_text or "Warning" in callout_text:
                # Set icon to "⚠️"
                icon = "⚠️"
            # Alternative condition check: "📌" in callout_text
            elif "📌" in callout_text:
                # Set icon to "📌"
                icon = "📌"
            # Alternative condition check: "🏷️" in callout_text
            elif "🏷️" in callout_text:
                # Set icon to "🏷️"
                icon = "🏷️"
            # Alternative condition check: "🎯" in callout_text
            elif "🎯" in callout_text:
                # Set icon to "🎯"
                icon = "🎯"
            # Alternative condition check: "⚡" in callout_text
            elif "⚡" in callout_text:
                # Set icon to "⚡"
                icon = "⚡"

            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "callout"
                "type": "callout",
                # Execute statement: "callout": {
                "callout": {
                    # Define field entry: "rich_text": parse_inline_formatting(callout_text)
                    "rich_text": parse_inline_formatting(callout_text),
                    # Execute statement: "icon": {"type": "emoji", "emoji": icon}
                    "icon": {"type": "emoji", "emoji": icon}
                }
            # Execute statement: })
            })
        # Bullet Lists
        elif stripped.startswith("- ") or stripped.startswith("* "):
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "bulleted_list_item"
                "type": "bulleted_list_item",
                # Execute statement: "bulleted_list_item": {"rich_text": parse_inline_formatting(stripped[2:])}
                "bulleted_list_item": {"rich_text": parse_inline_formatting(stripped[2:])}
            # Execute statement: })
            })
        # Numbered Lists
        elif re.match(r"^\d+\.\s+", stripped):
            # Set item_text to re.sub(r"^\d+\.\s+", "", stripped)
            item_text = re.sub(r"^\d+\.\s+", "", stripped)
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "numbered_list_item"
                "type": "numbered_list_item",
                # Execute statement: "numbered_list_item": {"rich_text": parse_inline_formatting(item_text)}
                "numbered_list_item": {"rich_text": parse_inline_formatting(item_text)}
            # Execute statement: })
            })
        # Fallback paragraph
        else:
            # Execute statement: blocks.append({
            blocks.append({
                # Define field entry: "object": "block"
                "object": "block",
                # Define field entry: "type": "paragraph"
                "type": "paragraph",
                # Execute statement: "paragraph": {"rich_text": parse_inline_formatting(stripped)}
                "paragraph": {"rich_text": parse_inline_formatting(stripped)}
            # Execute statement: })
            })

        # Execute statement: idx += 1
        idx += 1

    # Check if condition: in_table
    if in_table:
        # Execute statement: flush_table()
        flush_table()

    # Return value: blocks
    return blocks


# Define function create_notion_page
def create_notion_page(token: str, parent_spec: Dict[str, Any], title: str, blocks: List[Dict[str, Any]], icon: str = "📄") -> str:
    # Docstring explaining Create a page in Notion, uploading blocks in chunks to adher
    """Create a page in Notion, uploading blocks in chunks to adhere to Notion's API limits."""
    # Notion allows max 100 blocks on creation
    initial_chunk = blocks[:90]
    # Set remaining_chunks to blocks[90:]
    remaining_chunks = blocks[90:]

    # Set payload to {
    payload = {
        # Define field entry: "parent": parent_spec
        "parent": parent_spec,
        # Define field entry: "icon": {"type": "emoji", "emoji": icon}
        "icon": {"type": "emoji", "emoji": icon},
        # Execute statement: "properties": {
        "properties": {
            # Execute statement: "title": {
            "title": {
                # Execute statement: "title": [{"type": "text", "text": {"content": title}}]
                "title": [{"type": "text", "text": {"content": title}}]
            }
        },
        # Execute statement: "children": initial_chunk
        "children": initial_chunk
    }

    # Set resp to notion_api_call("pages", token, method="POST", payload=payload)
    resp = notion_api_call("pages", token, method="POST", payload=payload)
    # Set page_id to resp["id"]
    page_id = resp["id"]

    # Append any remaining blocks in batches of 90
    while remaining_chunks:
        # Set chunk to remaining_chunks[:90]
        chunk = remaining_chunks[:90]
        # Set remaining_chunks to remaining_chunks[90:]
        remaining_chunks = remaining_chunks[90:]
        # Execute statement: time.sleep(0.4)
        time.sleep(0.4)
        # Execute statement: notion_api_call(
        notion_api_call(
            # Execute statement: f"blocks/{page_id}/children",
            f"blocks/{page_id}/children",
            # Execute statement: token,
            token,
            # Specify argument: method="PATCH"
            method="PATCH",
            # Execute statement: payload={"children": chunk}
            payload={"children": chunk}
        )

    # Return value: page_id
    return page_id


# Define function extract_title_and_icon
def extract_title_and_icon(md_content: str, fallback_title: str) -> Tuple[str, str]:
    # Docstring explaining Extract page title and leading emoji from first markdown H1 
    """Extract page title and leading emoji from first markdown H1 line."""
    # Loop over items: line in md_content.splitlines()
    for line in md_content.splitlines():
        # Set line to line.strip()
        line = line.strip()
        # Check if condition: line.startswith("# ")
        if line.startswith("# "):
            # Set raw to line[2:].strip()
            raw = line[2:].strip()
            # Check for leading emoji
            match = re.match(r"^([\U00010000-\U0010ffff]|\u26a0|\u2705|\u274c|\ud83c[\udf00-\udfff]|\ud83d[\udc00-\ude4f]|\ud83e[\udd00-\udfff])\s*", raw)
            # Check if condition: match
            if match:
                # Set icon to match.group(1)
                icon = match.group(1)
                # Set title to raw[len(match.group(0)):].strip()
                title = raw[len(match.group(0)):].strip()
                # Return value: title, icon
                return title, icon
            # Return value: raw, "📄"
            return raw, "📄"
    # Return value: fallback_title, "📄"
    return fallback_title, "📄"


# Define function main
def main():
    # Set parser to argparse.ArgumentParser(description="Export Verism AI documentation to Notion Workspace")
    parser = argparse.ArgumentParser(description="Export Verism AI documentation to Notion Workspace")
    # Execute statement: parser.add_argument("--token", default=os.getenv("NOTION_API_KEY") or os.ge
    parser.add_argument("--token", default=os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN"), help="Notion Integration Token")
    # Execute statement: parser.add_argument("--parent-page", default=os.getenv("NOTION_PAGE_ID"), h
    parser.add_argument("--parent-page", default=os.getenv("NOTION_PAGE_ID"), help="Target Parent Page ID in Notion (Optional)")
    # Set token to args.token or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    token = args.token or os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")

    # Check if condition: not token
    if not token:
        # Print console output: print("❌ Error: Missing Notion Integration Token.")
        print("❌ Error: Missing Notion Integration Token.")
        # Execute statement: sys.exit(1)
        sys.exit(1)

    # Print console output: print("🔑 Authenticating with Notion API...")
    print("🔑 Authenticating with Notion API...")

    # Determine parent target (Top-level workspace or specific page)
    if args.parent_page and args.parent_page.lower() != "workspace":
        # Set parent_id to clean_page_id(args.parent_page)
        parent_id = clean_page_id(args.parent_page)
        # Print console output: print(f"🎯 Target parent page provided: {parent_id}")
        print(f"🎯 Target parent page provided: {parent_id}")
        # Set parent_spec to {"page_id": parent_id}
        parent_spec = {"page_id": parent_id}
    # Execute alternate fallback branch
    else:
        # Print console output: print("🌐 Creating documentation hub directly at top-level workspace...")
        print("🌐 Creating documentation hub directly at top-level workspace...")
        # Set parent_spec to {"type": "workspace", "workspace": True}
        parent_spec = {"type": "workspace", "workspace": True}

    # Set md_files to sorted(DOCS_DIR.glob("*.md"))
    md_files = sorted(DOCS_DIR.glob("*.md"))
    # Check if condition: not md_files
    if not md_files:
        # Print console output: print(f"❌ No markdown files found in {DOCS_DIR}")
        print(f"❌ No markdown files found in {DOCS_DIR}")
        # Execute statement: sys.exit(1)
        sys.exit(1)

    # 1. Create Root Hub Page
    hub_file = DOCS_DIR / "00_NOTION_WORKSPACE_HUB.md"
    # Set sub_files to [f for f in md_files if f.name != "00_NOTION_WORKSPACE_HUB.md"]
    sub_files = [f for f in md_files if f.name != "00_NOTION_WORKSPACE_HUB.md"]

    # Check if condition: hub_file.exists()
    if hub_file.exists():
        # Set hub_content to hub_file.read_text(encoding="utf-8")
        hub_content = hub_file.read_text(encoding="utf-8")
        # Set hub_title, hub_icon to extract_title_and_icon(hub_content, "Verism AI — Engineering & Product Workspace")
        hub_title, hub_icon = extract_title_and_icon(hub_content, "Verism AI — Engineering & Product Workspace")
        # Set hub_blocks to markdown_to_blocks(hub_content)
        hub_blocks = markdown_to_blocks(hub_content)
        # Print console output: print(f"\n📦 Creating Workspace Hub: {hub_icon} {hub_title} ({len(hub_blocks)} blocks)...")
        print(f"\n📦 Creating Workspace Hub: {hub_icon} {hub_title} ({len(hub_blocks)} blocks)...")
        # Set hub_page_id to create_notion_page(token, parent_spec, hub_title, hub_blocks, icon=hub_icon)
        hub_page_id = create_notion_page(token, parent_spec, hub_title, hub_blocks, icon=hub_icon)
        # Print console output: print(f"   ✅ Created Hub Page: https://notion.so/{hub_page_id.replace('-', '')}")
        print(f"   ✅ Created Hub Page: https://notion.so/{hub_page_id.replace('-', '')}")
    # Execute alternate fallback branch
    else:
        # Raise exception: FileNotFoundError("00_NOTION_WORKSPACE_HUB.md is required as root hub.")
        raise FileNotFoundError("00_NOTION_WORKSPACE_HUB.md is required as root hub.")

    # 2. Upload all subpages nested under the Hub
    subpage_parent = {"page_id": hub_page_id}
    # Print console output: print(f"\n📂 Uploading {len(sub_files)} sub-pages under Hub...")
    print(f"\n📂 Uploading {len(sub_files)} sub-pages under Hub...")

    # Loop over items: idx, f in enumerate(sub_files, 1)
    for idx, f in enumerate(sub_files, 1):
        # Set content to f.read_text(encoding="utf-8")
        content = f.read_text(encoding="utf-8")
        # Set title, icon to extract_title_and_icon(content, f.stem)
        title, icon = extract_title_and_icon(content, f.stem)
        # Set blocks to markdown_to_blocks(content)
        blocks = markdown_to_blocks(content)
        # Print console output: print(f" [{idx}/{len(sub_files)}] Uploading {icon} {title} ({len(blocks)} blocks)...")
        print(f" [{idx}/{len(sub_files)}] Uploading {icon} {title} ({len(blocks)} blocks)...")
        # Begin try block to handle operations safely
        try:
            # Set sub_id to create_notion_page(token, subpage_parent, title, blocks, icon=icon)
            sub_id = create_notion_page(token, subpage_parent, title, blocks, icon=icon)
            # Print console output: print(f"       ↳ Page created: https://notion.so/{sub_id.replace('-', '')}")
            print(f"       ↳ Page created: https://notion.so/{sub_id.replace('-', '')}")
        # Handle exception during execution: except Exception as e
        except Exception as e:
            # Print console output: print(f"       ⚠️ Error uploading {f.name}: {e}")
            print(f"       ⚠️ Error uploading {f.name}: {e}")
        # Execute statement: time.sleep(0.5)
        time.sleep(0.5)

    # Print console output: print("\n" + "=" * 70)
    print("\n" + "=" * 70)
    # Print console output: print("🎉 SUCCESS! Verism AI project documentation is now live in Notion!")
    print("🎉 SUCCESS! Verism AI project documentation is now live in Notion!")
    # Print console output: print(f"🔗 Master Workspace Hub URL: https://notion.so/{hub_page_id.replace('-', '')}")
    print(f"🔗 Master Workspace Hub URL: https://notion.so/{hub_page_id.replace('-', '')}")
    # Print console output: print("=" * 70)
    print("=" * 70)


# Check if condition: __name__ == "__main__"
if __name__ == "__main__":
    # Execute statement: main()
    main()
