# Verism AI — Design System Specification

## 1. Guiding Philosophy
Verism AI is a single-teacher, high-density, trust-centered assessment operating system.
**Core Principle:** *"AI suggests. You stamp. Every grade waits for your approval. Grading never starts without your command."*

The UI prioritizes editorial clarity, high information density without clutter, honest metrics without artificial placeholders, and complete accessibility across all viewports from 360px mobile up to 1920px ultrawide screens.

---

## 2. Color Palette & Semantic Tokens

| Token | Class Name | Light Hex / RGBA | Role / Usage |
|---|---|---|---|
| Paper Background | `bg-paper` | `#FBFBFD` | Overall application page canvas background |
| Card Surface | `bg-card` | `#FFFFFF` | Elevated containers, modals, table surfaces |
| Primary Ink | `text-ink` | `#0F172A` | Primary typography, headers, active navigation icons |
| Muted Ink | `text-muted-ink` | `#475569` | Secondary descriptions, column headers, metadata |
| Faint Ink | `text-faint` | `#94A3B8` | Subtitles, empty states, disabled states, unread hints |
| Border Line | `border-line` | `#E2E8F0` / `rgba(15,23,42,0.08)` | Crisp, 1px structural container and table borders |
| Amber Brand / Attention | `bg-amber-soft`, `text-amber-ink` | `#FEF3C7` / `#B45309` | Unreviewed grades, drafts, AI-generated suggestions, badges |
| Sage Success / Approved | `bg-sage-soft`, `text-sage` | `#ECFDF5` / `#047857` | Approved grades, 100% rubrics, verified items, passing checks |
| Clay Warning / Flag | `bg-clay-soft`, `text-clay` | `#FEE2E2` / `#B91C1C` | Similarity collisions (>=85%), failed submissions, destructive actions |
| Lav Analytic / Neutral | `bg-lav-soft`, `text-lav-ink` | `#EEF2FF` / `#4338CA` | Histograms, metric trends, active navigation highlights |
| Blue Citation | `bg-blue-soft`, `text-blue` | `#EFF6FF` / `#1D4ED8` | Web citations, external links, documentation references |

---

## 3. Typography & Hierarchy

- **Display Serif (`font-display`):** Used for page headers, major modal titles, and KPI values. Conveys institutional authority and editorial precision.
- **System Sans (`font-sans`):** Standard clean typography used for labels, table content, forms, and general body text.
- **Monospace (`font-mono`):** Used for roll numbers, SHA-256 integrity checksums, score fractions (`94/100`), keyboard shortcut badges (`<kbd>`), and ISO-8601 timestamps.

### Heading Scale
- Page Header: `text-2xl sm:text-3xl font-display font-bold text-ink`
- Card / Section Header: `text-lg sm:text-xl font-display font-semibold text-ink`
- Eyebrow Badge: `text-[10px] sm:text-xs uppercase tracking-[0.16em] text-faint font-semibold`
- Table Header: `text-[10px] uppercase tracking-[0.14em] text-faint font-medium`

---

## 4. Spacing, Elevation & Surfaces

- **Border Radius:**
  - Micro-controls (badges, tooltips): `rounded-md` (6px)
  - Interactive elements (buttons, inputs, select menus): `rounded-lg` (8px)
  - Cards and content modules: `rounded-xl` (12px)
  - Major panels and modal dialogs: `rounded-[14px]` (14px)
- **Shadows:**
  - Standard cards: `shadow-2xs` border-matched subtle elevation.
  - Interactive hover state: `hover:shadow-xs hover:border-line/80 transition-all`.
  - Floating triggers & dialog overlays: `shadow-lg` to `shadow-2xl`.

---

## 5. Responsive Layout Architecture

The user interface is engineered and tested across 4 distinct viewport tiers:

### 1. Mobile Portrait (360px - 640px)
- Sidebar collapses into an off-canvas drawer triggered by hamburger icon.
- TopBar search width constrained (`max-w-[130px]`) alongside compact course switcher (`max-w-[140px]`) to eliminate horizontal header overflow.
- Manual student enrollment forms switch from 12-column inline grid to a vertically stacked form with touch-friendly 44px hit targets.
- Tables receive `overflow-x-auto` with sticky student identifier columns.
- Modals scale to `p-4 sm:p-6` with full viewport width (`w-[calc(100%-2rem)]`).

### 2. Tablet (641px - 1024px)
- 2-column KPI grid (`sm:grid-cols-2`).
- Collapsible icon-only sidebar option with tooltips on hover.
- Split preview panes in Review Queue collapse to tabbed or stacked layout.

### 3. Desktop (1025px - 1440px)
- Persistent 240px sidebar with 4 grouped sections: `Workspace`, `Grading`, `Insights`, `Account`.
- 4-column KPI cards (`xl:grid-cols-4`).
- Dual-pane Review Queue: Student submission text on left, live interactive rubric scoring on right.

### 4. Ultrawide (1441px - 1920px+)
- Maximum content width container (`max-w-7xl` or `max-w-screen-2xl mx-auto`) prevents uncomfortable eye travel across expansive monitors.
- Charts maintain fixed aspect ratios (`h-[240px]` to `h-[320px]`).

---

## 6. Component Guidelines

### Buttons & Interactive States
- **Primary Action:** Solid ink (`bg-ink text-white hover:bg-ink/90`).
- **Secondary / Filter:** Outline (`border border-line bg-card hover:bg-paper`).
- **Destructive:** Destructive variant (`bg-clay text-white hover:bg-clay/90` or `text-clay hover:bg-clay-soft`).
- **Disabled State:** Every disabled button MUST provide a tooltip or visual explanation stating why it is disabled (e.g. "Select at least 1 student to export", "Add a course before uploading").
- **Loading State:** Must display `<Loader2 className="animate-spin" />` with explicit progress feedback.

### Empty States
Every empty state adheres to a 3-part layout:
1. Centered icon container with subtle pastel background (`bg-lav-soft` or `bg-amber-soft`).
2. Single-sentence honest explanation of why no records exist.
3. Outcome-based Call-to-Action button (e.g., "Enroll First Student", "Create Assignment").

### Toasts & Notifications
- Managed via `showToast(message, type)`.
- Green checkmark for success outcomes (`type="success"`).
- Red alert triangle with `role="alert"` for errors (`type="error"`).
- Automatic type inference: messages containing "error" or "failed" automatically route to error styling.
- All errors display real server-reported reasons, not masked generic texts.
