# Verism AI Assist

Build a polished, modern frontend prototype for an AI-powered EdTech platform called Verism AI, designed primarily for teachers.

VERY IMPORTANT — FRONTEND ONLY

Do NOT create or connect any database, Supabase, Firebase, backend, API, authentication, server, file storage, real AI service, or server-side logic.
Use only React + TypeScript + Tailwind CSS + frontend components + mock data.
All uploads, AI processing, plagiarism detection and grading must be simulated in the frontend. We will add the backend/database later.

CORE PURPOSE

The platform helps teachers:

Upload all student assignments in batch

Detect similarity between submissions, including flags such as 90%+ similarity

Show AI-generated-content probability as an indicator

Upload/create a grading rubric

Automatically generate rubric-based suggested grades

Let the teacher review/edit/approve every AI grade

Organize everything course-wise and section-wise

The key concept is:

Upload → AI Analysis → Similarity Check → AI Grading → Teacher Review → Final Approval

AI must NEVER automatically finalize a grade. The teacher is always the final decision-maker.

DESIGN

Create a premium SaaS-style EdTech dashboard:

Light theme

White/off-white background

Lavender/soft blue with subtle green accents

Dark navy text

Rounded cards and soft shadows

Clean modern typography

Minimal, elegant animations

Professional and competition-ready

Responsive desktop/tablet/mobile design

Do not make it look like a generic school LMS

NAVIGATION

Create a left sidebar:

EduCheck AI

Dashboard

My Courses

Assignments

Assessments

Similarity Check

AI Grading

Review Queue

Gradebook

Reports

Settings

Top bar:

Search

Notifications

Teacher profile

Course/section selector where relevant

DASHBOARD

Show:

Total Courses

Active Assignments

Pending Reviews

Submissions Checked

Similarity Flags

AI Grades Pending

Average Class Score

Include:

Recent Activity

Pending Reviews

Grade distribution chart

Similarity overview

"Review Now" buttons

MY COURSES

Course cards with mock data:

Data Structures — CS201 — Section A
Database Management Systems — CS202 — Section B
Object Oriented Programming — CS203 — Section A
Machine Learning — DS301 — Section A

Show student count, assignments, pending reviews and similarity alerts.

Clicking a course opens:

Overview | Assignments | Assessments | Students | Gradebook | Reports

Everything must remain separated by course and section.

BATCH ASSIGNMENT UPLOAD

Create a beautiful upload page where teacher selects:

Course

Section

Assignment

Due date

Then a large drag-and-drop area:

"Drop all student submissions here"

Support UI for PDF, DOC/DOCX, TXT, PPT/PPTX and ZIP.

Show multiple uploaded student files and progress.

Button:
Start AI Analysis

Simulate processing with an animated progress bar.

SIMILARITY CHECK

After simulated analysis show:

Total submissions

Checked

Potential similarity

High similarity

Default threshold: 90%

Use wording:
"Potential similarity detected — Teacher review required."

Never present similarity as automatic proof of plagiarism.

Create a table:

Student A | Student B | Similarity | Status | Compare

Example:
Rahul Sharma | Amit Patil | 94% | High Similarity | Compare

COMPARISON PAGE

Side-by-side Student A and Student B submissions.

Show:
Similarity Score: 94%

Highlight matching sections.

Also show separately:

Text similarity

Matching phrases

AI-generated content probability

Teacher actions:

Confirm concern

Dismiss flag

Add note

AI CONTENT DETECTION

Show a visual indicator such as:

AI-generated content probability: 72%

Add:
"AI detection is an indicator, not definitive proof. Final decisions should be made by the teacher."

RUBRIC + AI GRADING

Create a rubric setup page.

Teacher selects:
Course → Section → Assessment

Rubric table:

Criterion | Description | Weight | Max Marks

Example:

Understanding — 30%

Accuracy — 30%

Methodology — 20%

Presentation — 20%

Buttons:
Add Criterion
Start AI Grading

Simulate AI processing.

AI GRADING RESULTS

Show:

62 submissions processed
54 ready for review
8 flagged

Table:

Student | AI Score | Similarity | AI Content | Status | Review

Example:
Rahul Sharma | 82/100 | 12% | Low | Pending Review | Review

TEACHER REVIEW WORKSPACE

This is the most important page.

Three-column layout:

Left: Student submission

Center: Rubric evaluation

Understanding: 25/30
Accuracy: 27/30
Methodology: 16/20
Presentation: 14/20

Right: AI summary

Suggested Score: 82/100

AI feedback:
"Good understanding of the core concept..."

Teacher can:

Edit rubric marks

Edit feedback

Add comments

Override AI score

Approve grade

Buttons:
Approve Grade
Edit Grade

After approval show:
Teacher Approved → Final Grade

REVIEW QUEUE

Show centralized items requiring teacher action.

Categories:

AI Grading Review

Similarity Flags

AI Detection Flags

Approved

Add filters for:
Course, Section, Assignment, Status, Similarity.

GRADEBOOK

Spreadsheet-style course-wise gradebook:

Student | Assignment 1 | Assignment 2 | Quiz | Assessment | Final Score | Status

Allow frontend-only sorting, filtering and searching.

REPORTS

Create attractive charts for:

Average score

Grade distribution

Submission rate

Similarity cases

AI detection statistics

Approved grades

Filters:
Course → Section → Assessment

Buttons:
Export Report and Download Gradebook (UI only; no real backend).

MOCK DATA + INTERACTIONS

Use realistic fictional students and assignments.

Make buttons and navigation functional using frontend state/mock data.

Simulate:

File upload

AI processing

Similarity results

AI grading

Review

Grade editing

Grade approval

Filters

Search

Course/section switching

Notifications

Success/error states

Do not build unnecessary features.

FINAL PRIORITY

Make the frontend feel like a combination of:

AI grading + similarity checking + teacher review + course management

The most important message of the product should be:

"AI handles the repetitive work. Teachers make the final decision."

Create all major pages and connect them through navigation in this single frontend build. Do not create any backend or database.

This project was built with [Lovable](https://lovable.dev).

**Live app**: https://assessment-mentor.lovable.app

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/98fa096e-d728-436f-835f-222b05fbd7ef).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
