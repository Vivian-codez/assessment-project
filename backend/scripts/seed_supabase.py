"""Direct Supabase Database Seeding Script.

Seeds the new active Supabase database (lzranjtbiucfaktbnjec) directly via
the supabase-py PostgREST client with FERPA/GDPR encryption on student PII.
"""

import os
import sys
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.supabase import supabase
from app.core.security import ferpa_cipher, get_password_hash


def seed_supabase():
    print(f"Connecting to Supabase at: {supabase.supabase_url}")

    # 1. Instructor Dr. Priya Rao
    print("1. Seeding Instructor Dr. Priya Rao...")
    inst_data = {
        "id": "inst_priya_rao",
        "name": "Dr. Priya Rao",
        "email": "priya.rao@university.edu",
        "role": "Instructor · Computer Science",
        "hashed_password": get_password_hash("teacher123"),
        "preferences": {
            "show_similarity_context": True,
            "require_teacher_notes_on_overrides": False,
            "include_ai_content_indicator": True,
        },
    }
    supabase.table("instructors").upsert(inst_data).execute()
    print("   [OK] Instructor seeded.")

    # 2. Courses
    print("2. Seeding Courses...")
    courses = [
        {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav", "instructor_id": "inst_priya_rao"},
        {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue", "instructor_id": "inst_priya_rao"},
        {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage", "instructor_id": "inst_priya_rao"},
        {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber", "instructor_id": "inst_priya_rao"},
    ]
    supabase.table("courses").upsert(courses).execute()
    print(f"   [OK] {len(courses)} Courses seeded.")

    # 3. Rubric & Criteria
    print("3. Seeding Rubric & Criteria...")
    rubric_data = {
        "id": "rub_oop_a3",
        "name": "Assignment 3 · OOP & Polymorphism Rubric",
        "course_id": "c_cs203",
        "total_max_score": 100.0,
    }
    supabase.table("rubrics").upsert(rubric_data).execute()

    criteria = [
        {"id": "crit_1", "rubric_id": "rub_oop_a3", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0},
        {"id": "crit_2", "rubric_id": "rub_oop_a3", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1},
        {"id": "crit_3", "rubric_id": "rub_oop_a3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2},
        {"id": "crit_4", "rubric_id": "rub_oop_a3", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3},
    ]
    supabase.table("rubric_criteria").upsert(criteria).execute()
    print("   [OK] Rubric and criteria seeded.")

    # 4. Assignment
    print("4. Seeding Assignment 3...")
    assignment_data = {
        "id": "assign_oop_a3",
        "course_id": "c_cs203",
        "title": "Assignment 3 · Graph Traversal & Ledger Modeling",
        "description": "Implementation of banking transaction ledger and polymorphic account hierarchies.",
        "due_date": "2026-10-25T23:59:59Z",
        "max_score": 100.0,
        "rubric_id": "rub_oop_a3",
    }
    supabase.table("assignments").upsert(assignment_data).execute()
    print("   [OK] Assignment seeded.")

    # 5. Submissions with FERPA encryption
    print("5. Seeding Submissions with FERPA encryption...")
    raw_subs = [
        {
            "id": "sub_rahul_047",
            "name": "Rahul Sharma",
            "roll": "2024-047",
            "email": "rahul.sharma@university.edu",
            "file_name": "sharma_rahul_graphs.pdf",
            "text": "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes, overriding the interest method for each account type.",
            "similarity_score": 94.0,
            "ai_content": 31.0,
            "status": "flagged",
            "score": 82.0,
        },
        {
            "id": "sub_amit_051",
            "name": "Amit Patil",
            "roll": "2024-051",
            "email": "amit.patil@university.edu",
            "file_name": "patil_amit_graphs.docx",
            "text": "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type across transaction lifecycles.",
            "similarity_score": 94.0,
            "ai_content": 27.0,
            "status": "flagged",
            "score": 79.0,
        },
        {
            "id": "sub_sneha_018",
            "name": "Sneha Iyer",
            "roll": "2024-018",
            "email": "sneha.iyer@university.edu",
            "file_name": "iyer_sneha_graphs.pdf",
            "text": "Comprehensive analysis of tree and graph traversals with adjacency list representation, cycle detection, and memory profiling.",
            "similarity_score": 6.0,
            "ai_content": 72.0,
            "status": "pending",
            "score": 88.0,
        },
        {
            "id": "sub_karan_036",
            "name": "Karan Mehta",
            "roll": "2024-036",
            "email": "karan.mehta@university.edu",
            "file_name": "mehta_karan_graphs.pdf",
            "text": "Clean implementation using breadth-first search and depth-first search for directed acyclic graph topological sorting.",
            "similarity_score": 4.0,
            "ai_content": 12.0,
            "status": "approved",
            "score": 84.0,
        },
        {
            "id": "sub_meera_029",
            "name": "Meera Nair",
            "roll": "2024-029",
            "email": "meera.nair@university.edu",
            "file_name": "nair_meera_graphs.pdf",
            "text": "Exploration of polymorphic interfaces and dynamic dispatch in transactional state machines.",
            "similarity_score": 9.0,
            "ai_content": 68.0,
            "status": "pending",
            "score": 74.0,
        },
        {
            "id": "sub_daniel_012",
            "name": "Daniel Mensah",
            "roll": "2024-012",
            "email": "daniel.mensah@university.edu",
            "file_name": "mensah_daniel_graphs.pdf",
            "text": "Optimized memory layout with abstract base classes and generic collections for large ledger datasets.",
            "similarity_score": 3.0,
            "ai_content": 18.0,
            "status": "pending",
            "score": 91.0,
        },
    ]

    subs_to_insert = []
    drafts_to_insert = []

    for s in raw_subs:
        subs_to_insert.append({
            "id": s["id"],
            "assignment_id": "assign_oop_a3",
            "student_name_encrypted": ferpa_cipher.encrypt(s["name"]),
            "student_roll_encrypted": ferpa_cipher.encrypt(s["roll"]),
            "student_email_encrypted": ferpa_cipher.encrypt(s["email"]),
            "file_name": s["file_name"],
            "file_type": "pdf" if s["file_name"].endswith(".pdf") else "docx",
            "extracted_text": s["text"],
            "similarity_score": s["similarity_score"],
            "ai_content_probability": s["ai_content"],
            "status": s["status"],
        })

        crit_breakdown = [
            {"criterion_name": "Understanding", "score": round(s["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"},
            {"criterion_name": "Accuracy", "score": round(s["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"},
            {"criterion_name": "Methodology", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"},
            {"criterion_name": "Presentation", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"},
        ]
        drafts_to_insert.append({
            "id": f"draft_{s['id']}",
            "submission_id": s["id"],
            "suggested_score": s["score"],
            "final_score": s["score"] if s["status"] == "approved" else None,
            "criteria_scores": crit_breakdown,
            "ai_feedback": "Good understanding of the core concept with accurate class modeling. Methodology depth is moderate.",
            "status": s["status"],
            "ai_model": "gemini-2.5-flash",
            "approved_at": datetime.now(timezone.utc).isoformat() if s["status"] == "approved" else None,
            "approved_by_id": "inst_priya_rao" if s["status"] == "approved" else None,
        })

    supabase.table("submissions").upsert(subs_to_insert).execute()
    supabase.table("draft_grades").upsert(drafts_to_insert).execute()
    print(f"   [OK] {len(subs_to_insert)} Submissions & Draft Grades seeded.")

    # 6. Similarity Match
    print("6. Seeding Similarity Match pair...")
    sim_data = {
        "id": "pair_rahul_amit",
        "assignment_id": "assign_oop_a3",
        "submission_a_id": "sub_rahul_047",
        "submission_b_id": "sub_amit_051",
        "similarity_score": 94.0,
        "matching_phrases": [
            "…branches into Savings and Current subtypes, overriding the interest method…"
        ],
        "status": "High similarity",
        "teacher_note": "Awaiting teacher verification of polymorphic ledger source excerpts.",
    }
    supabase.table("similarity_matches").upsert(sim_data).execute()
    print("   [OK] Similarity Match seeded.")

    # 7. Audit Log
    print("7. Seeding Audit Log...")
    audit_data = {
        "id": "audit_supabase_init",
        "actor_id": "inst_priya_rao",
        "actor_name": "Dr. Priya Rao",
        "action": "SYSTEM_INIT_SEED",
        "entity_type": "Course",
        "entity_id": "c_cs203",
        "details": {"event": "Supabase PostgreSQL Database seeded successfully with FERPA encryption enabled"},
        "ip_address": "127.0.0.1",
    }
    supabase.table("audit_logs").upsert(audit_data).execute()
    print("   [OK] Audit log seeded.")

    print("\n[SUCCESS] New Supabase database completely seeded and ready for production use!")


if __name__ == "__main__":
    seed_supabase()
