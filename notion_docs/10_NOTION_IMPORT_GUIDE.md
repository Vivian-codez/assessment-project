# 📖 10. Notion Import Guide

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  

---

## 🚀 How to Import This Documentation into Your Notion Workspace

You have two simple options to transfer this entire documentation suite into your Notion workspace:

---

### Option A: 1-Click Native Notion Markdown Import (Recommended, No API Key Required)

Notion has built-in support for importing Markdown and maintaining folder structure:

1. **Open Notion**: Open the desktop app or navigate to [notion.so](https://notion.so) in your browser.
2. **Navigate to Desired Parent Page**: Choose your team workspace, Engineering Wiki, or create a new empty page named `Verism AI Hub`.
3. **Click Import**:
   - In the left sidebar or at the bottom of the page, click **Import** (or click the `...` menu in the top-right corner of a page and select **Import**).
   - Select **Markdown & CSV**.
4. **Select Files**:
   - Navigate to your project folder:
     `c:\Users\alice\OneDrive\Desktop\Prototype\notion_docs\`
   - Select all `.md` files (`00_NOTION_WORKSPACE_HUB.md` through `10_NOTION_IMPORT_GUIDE.md`).
5. **Organize Hierarchy**:
   - Drag pages `01` through `10` into `00_NOTION_WORKSPACE_HUB` so they become clean sub-pages in your Notion sidebar!

---

### Option B: Automated Sync via Notion REST API Script

If you prefer to automate the upload using Python, we have provided an automated exporter script in `scripts/export_to_notion.py`:

#### 1. Create a Notion Internal Integration
1. Go to [Notion Integrations](https://www.notion.so/my-integrations).
2. Click **+ New integration**.
3. Name it `Verism AI Doc Sync`, select your workspace, and copy the **Internal Integration Secret** (`secret_...`).

#### 2. Share Your Target Notion Page with the Integration
1. In Notion, open the page where you want the documentation to live.
2. Click the `...` menu in the top right -> **Add connections** (or **Connect to**).
3. Select your integration (`Verism AI Doc Sync`).
4. Copy the Page ID from the URL (the 32-character string at the end of the URL).

#### 3. Run the Python Sync Script
```bash
python scripts/export_to_notion.py --token secret_YOUR_INTEGRATION_TOKEN --parent-page YOUR_PAGE_ID
```
The script will parse all markdown files, convert them into native Notion block trees (headings, callouts, tables, code blocks, bullet points, toggles), and create the nested structure automatically.

---

## 🎨 Recommended Notion Styling & Tweaks

Once your pages are imported into Notion, here are a few recommended tweaks for a state-of-the-art look:

1. **Icons & Covers**:
   - `00_NOTION_WORKSPACE_HUB`: Icon 🏛️ (Classical Building), Cover: Abstract blue gradient.
   - `01_EXECUTIVE_SUMMARY`: Icon 🎯 (Dart)
   - `02_SYSTEM_ARCHITECTURE`: Icon 🏗️ (Architecture)
   - `03_BACKEND_SERVICE`: Icon ⚙️ (Gear)
   - `04_FRONTEND_APPLICATION`: Icon 🎨 (Palette)
   - `05_API_REFERENCE`: Icon 📡 (Satellite)
   - `06_DATABASE_SCHEMA`: Icon 🗄️ (File Cabinet)
   - `07_FERPA_SECURITY`: Icon 🛡️ (Shield)
   - `08_LOCAL_DEV`: Icon 🛠️ (Tools)
   - `09_ROADMAP`: Icon 🗺️ (Map)

2. **Full Width Layout**:
   - For pages with wide tables and diagrams (`02_SYSTEM_ARCHITECTURE`, `05_API_REFERENCE`, `06_DATABASE_SCHEMA`, `09_ROADMAP`), click the `...` menu in the top right of the page in Notion and toggle **Full width** to `ON`.

3. **Convert Roadmap Table to Kanban Board**:
   - In `09_ROADMAP_AND_SPRINT_TRACKER`, highlight the table and click **Turn into database**.
   - Add a **Board View** grouped by `Status` to get an interactive Kanban board with drag-and-drop task cards.
