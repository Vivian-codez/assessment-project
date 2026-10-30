# 🎨 04. Frontend Application Guide

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  

---

## 💻 Tech Stack & Architecture

The Verism AI frontend is a modern single-page application built on React 19 and TanStack Router / TanStack Start, prioritizing fast interactive teacher workflows.

- **Framework**: React 19, TypeScript
- **Routing**: TanStack Router (`frontend/src/routes/`)
- **Styling**: Tailwind CSS + custom design tokens, Radix UI headless primitives
- **Icons**: Lucide React
- **Build Tool**: Vite
- **Data Layer**: Supabase JS Client & Axios REST Client with Bearer Token interceptor

---

## 🗂️ Frontend Directory Hierarchy

```
frontend/
├── src/
│   ├── components/
│   │   ├── ui/                    # Button, Input, Dialog, Progress, Table, Badge primitives
│   │   ├── MatrixRubricBuilder.tsx # Dynamic 2D rubric grid builder (Criteria x Performance levels)
│   │   ├── RosterView.tsx         # Classroom roll call list & CSV student import
│   │   └── RubricsListView.tsx    # Rubric library & template picker
│   ├── routes/
│   │   ├── __root.tsx             # Root layout with navigation sidebar & header
│   │   ├── index.tsx              # Main Instructor Workspace (Dashboard, Review, Gradebook)
│   │   ├── login.tsx              # Instructor authentication & registration
│   │   ├── dashboard.assignments.$id.upload.tsx # Drag-and-drop submission uploader
│   │   └── dashboard.roster.tsx   # Student enrollment management
│   ├── lib/
│   │   ├── supabase.ts            # Supabase browser client initialization
│   │   └── utils.ts               # Classnames (cn) merger & formatting helpers
│   └── styles.css                 # Global styles, typography & color variables
├── public/                        # Static assets, logos, and icons
├── vite.config.ts                 # Vite bundle configuration
└── package.json                   # Dependencies & scripts
```

---

## 🎛️ Key Interactive Components & Views

### 1. The Instructor Workspace (`routes/index.tsx`)
The centerpiece of the application, featuring a multi-tab view for active courses:
- **Dashboard Overview**: Summary statistics showing total submissions, pending draft grades, flagged peer similarities, and class average scores.
- **Review Queue**: The "AI suggests, You stamp" review table. Instructors can expand any submission to view the AI-generated rubric marks, adjust points with instant auto-recalculation, add personalized comments, and click **"Approve & Stamp Grade"**.
- **Similarity Matrix**: Interactive list of flagged student pairs exceeding the similarity threshold. Clicking a pair opens side-by-side synchronized document viewers with verbatim matching phrases highlighted in amber.
- **Live Spreadsheet Gradebook**: Full cohort gradebook matrix with student names, submission dates, criterion marks, total percentages, and one-click **"Export to CSV"** for campus registrar integration.

### 2. Matrix Rubric Builder (`components/MatrixRubricBuilder.tsx`)
A flexible matrix editor allowing professors to define complex assessment criteria:
- Rows represent **Criteria** (e.g., "Thesis Statement", "Methodology", "Code Quality", "Grammar & Style").
- Columns represent **Performance Tiers** (e.g., "Exemplary [4 pts]", "Proficient [3 pts]", "Developing [2 pts]", "Unacceptable [0 pts]").
- Real-time row weight validation ensures all criteria sum to exactly 100 points.

### 3. Submission Batch Uploader (`dashboard.assignments.$id.upload.tsx`)
- Drag-and-drop zone supporting single PDFs, multiple files, DOCX documents, or a `.zip` archive containing the whole cohort's files.
- Client-side pre-flight checks: file size limits, MIME type validation, and student roll number parsing from filenames (e.g., `CS101_S104_TermPaper.pdf`).
- Real-time progress tracker with animated stages:
  1. *Uploading files to secure storage...*
  2. *Extracting document text & running FERPA redaction...*
  3. *Generating vector embeddings & cross-checking cohort...*
  4. *Executing Gemini rubric evaluations...*

### 4. Classroom Roster Manager (`components/RosterView.tsx`)
- View, add, edit, and delete enrolled students per classroom.
- Bulk CSV import for quickly enrolling 100+ students with student IDs, names, and university email addresses.

---

## 🎨 Design System & Theming

The user interface uses a **professional light-blue & slate theme** tailored for long grading sessions with minimal eye strain:

| Token | Class / Hex | Application |
| :--- | :--- | :--- |
| **Primary Brand** | `sky-600` / `#0284c7` | Primary buttons, active tabs, progress bars |
| **Primary Hover** | `sky-700` / `#0369a1` | Button hover states |
| **Background Tint** | `slate-50` / `#f8fafc` | Main application background |
| **Card Surface** | `white` / `#ffffff` with `border-slate-200` | Content cards, data tables, dialogs |
| **Success / Approved** | `emerald-600` / `#059669` | Approved grade badges, 100% upload completion |
| **Similarity Alert** | `amber-600` / `#d97706` | Plagiarism match badges, peer similarity warnings |
| **AI Content Alert** | `indigo-600` / `#4f46e5` | Synthetic AI stylometry probability indicator |

---

## 🔌 API Client & State Management

The frontend communicates with the backend via the centralized `api` helper:
- Automatically injects `Authorization: Bearer <token>` from `localStorage`.
- Intercepts 401 Unauthorized responses to redirect to `/login`.
- Implements optimistic UI updates: when a teacher stamps a grade, the submission immediately transitions to `APPROVED` in the local state while the background network request resolves.
