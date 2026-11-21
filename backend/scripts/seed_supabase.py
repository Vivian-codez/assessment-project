# Docstring explaining Direct Supabase Database Seeding Script.
"""Direct Supabase Database Seeding Script.

Seeds the new active Supabase database (lzranjtbiucfaktbnjec) directly via
the supabase-py PostgREST client with FERPA/GDPR encryption on student PII.
"""

# Import module os
import os
# Import module sys
import sys
# Import datetime, timezone from datetime
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import supabase from app.core.supabase
from app.core.supabase import supabase
# Import ferpa_cipher, get_password_hash from app.core.security
from app.core.security import ferpa_cipher, get_password_hash


# Define function seed_supabase
def seed_supabase():
    # Print console output: print(f"Connecting to Supabase at: {supabase.supabase_url}")
    print(f"Connecting to Supabase at: {supabase.supabase_url}")

    # 1. Instructor Dr. Priya Rao
    print("1. Seeding Instructor Dr. Priya Rao...")
    # Set inst_data to {
    inst_data = {
        # Define field entry: "id": "inst_priya_rao"
        "id": "inst_priya_rao",
        # Define field entry: "name": "Dr. Priya Rao"
        "name": "Dr. Priya Rao",
        # Define field entry: "email": "priya.rao@university.edu"
        "email": "priya.rao@university.edu",
        # Define field entry: "role": "Instructor · Computer Science"
        "role": "Instructor · Computer Science",
        # Define field entry: "hashed_password": get_password_hash("teacher123")
        "hashed_password": get_password_hash("teacher123"),
        # Execute statement: "preferences": {
        "preferences": {
            # Define field entry: "show_similarity_context": True
            "show_similarity_context": True,
            # Define field entry: "require_teacher_notes_on_overrides": False
            "require_teacher_notes_on_overrides": False,
            # Define field entry: "include_ai_content_indicator": True
            "include_ai_content_indicator": True,
        },
    }
    # Execute statement: supabase.table("instructors").upsert(inst_data).execute()
    supabase.table("instructors").upsert(inst_data).execute()
    # Print console output: print("   [OK] Instructor seeded.")
    print("   [OK] Instructor seeded.")

    # 2. Courses
    print("2. Seeding Courses...")
    # Set courses to [
    courses = [
        # Define field entry: {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav", "instructor_id": "inst_priya_rao"}
        {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav", "instructor_id": "inst_priya_rao"},
        # Define field entry: {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue", "instructor_id": "inst_priya_rao"}
        {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue", "instructor_id": "inst_priya_rao"},
        # Define field entry: {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage", "instructor_id": "inst_priya_rao"}
        {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage", "instructor_id": "inst_priya_rao"},
        # Define field entry: {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber", "instructor_id": "inst_priya_rao"}
        {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber", "instructor_id": "inst_priya_rao"},
    ]
    # Execute statement: supabase.table("courses").upsert(courses).execute()
    supabase.table("courses").upsert(courses).execute()
    # Print console output: print(f"   [OK] {len(courses)} Courses seeded.")
    print(f"   [OK] {len(courses)} Courses seeded.")

    # 3. Rubric & Criteria
    print("3. Seeding Rubric & Criteria...")
    # Set rubric_data to {
    rubric_data = {
        # Define field entry: "id": "rub_oop_a3"
        "id": "rub_oop_a3",
        # Define field entry: "name": "Assignment 3 · OOP & Polymorphism Rubric"
        "name": "Assignment 3 · OOP & Polymorphism Rubric",
        # Define field entry: "course_id": "c_cs203"
        "course_id": "c_cs203",
        # Define field entry: "total_max_score": 100.0
        "total_max_score": 100.0,
    }
    # Execute statement: supabase.table("rubrics").upsert(rubric_data).execute()
    supabase.table("rubrics").upsert(rubric_data).execute()

    # Set criteria to [
    criteria = [
        # Define field entry: {"id": "crit_1", "rubric_id": "rub_oop_a3", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0}
        {"id": "crit_1", "rubric_id": "rub_oop_a3", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0},
        # Define field entry: {"id": "crit_2", "rubric_id": "rub_oop_a3", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1}
        {"id": "crit_2", "rubric_id": "rub_oop_a3", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1},
        # Define field entry: {"id": "crit_3", "rubric_id": "rub_oop_a3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2}
        {"id": "crit_3", "rubric_id": "rub_oop_a3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2},
        # Define field entry: {"id": "crit_4", "rubric_id": "rub_oop_a3", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3}
        {"id": "crit_4", "rubric_id": "rub_oop_a3", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3},
    ]
    # Execute statement: supabase.table("rubric_criteria").upsert(criteria).execute()
    supabase.table("rubric_criteria").upsert(criteria).execute()
    # Print console output: print("   [OK] Rubric and criteria seeded.")
    print("   [OK] Rubric and criteria seeded.")

    # 4. Assignment
    print("4. Seeding Assignment 3...")
    # Set assignment_data to {
    assignment_data = {
        # Define field entry: "id": "assign_oop_a3"
        "id": "assign_oop_a3",
        # Define field entry: "course_id": "c_cs203"
        "course_id": "c_cs203",
        # Define field entry: "title": "Assignment 3 · Graph Traversal & Ledger Modeling"
        "title": "Assignment 3 · Graph Traversal & Ledger Modeling",
        # Define field entry: "description": "Implementation of banking transaction ledger and polymorphic account hierarchies."
        "description": "Implementation of banking transaction ledger and polymorphic account hierarchies.",
        # Define field entry: "due_date": "2026-10-25T23:59:59Z"
        "due_date": "2026-10-25T23:59:59Z",
        # Define field entry: "max_score": 100.0
        "max_score": 100.0,
        # Define field entry: "rubric_id": "rub_oop_a3"
        "rubric_id": "rub_oop_a3",
    }
    # Execute statement: supabase.table("assignments").upsert(assignment_data).execute()
    supabase.table("assignments").upsert(assignment_data).execute()
    # Print console output: print("   [OK] Assignment seeded.")
    print("   [OK] Assignment seeded.")

    # 5. Submissions with FERPA encryption
    print("5. Seeding Submissions with FERPA encryption...")
    # Set raw_subs to [
    raw_subs = [
        # Execute statement: {
        {
            # Define field entry: "id": "sub_rahul_047"
            "id": "sub_rahul_047",
            # Define field entry: "name": "Rahul Sharma"
            "name": "Rahul Sharma",
            # Define field entry: "roll": "2024-047"
            "roll": "2024-047",
            # Define field entry: "email": "rahul.sharma@university.edu"
            "email": "rahul.sharma@university.edu",
            # Define field entry: "file_name": "sharma_rahul_graphs.pdf"
            "file_name": "sharma_rahul_graphs.pdf",
            # Define field entry: "text": "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes, overriding the interest method for each account type."
            "text": "This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes, overriding the interest method for each account type.",
            # Define field entry: "similarity_score": 94.0
            "similarity_score": 94.0,
            # Define field entry: "ai_content": 31.0
            "ai_content": 31.0,
            # Define field entry: "status": "flagged"
            "status": "flagged",
            # Define field entry: "score": 82.0
            "score": 82.0,
        },
        # Execute statement: {
        {
            # Define field entry: "id": "sub_amit_051"
            "id": "sub_amit_051",
            # Define field entry: "name": "Amit Patil"
            "name": "Amit Patil",
            # Define field entry: "roll": "2024-051"
            "roll": "2024-051",
            # Define field entry: "email": "amit.patil@university.edu"
            "email": "amit.patil@university.edu",
            # Define field entry: "file_name": "patil_amit_graphs.docx"
            "file_name": "patil_amit_graphs.docx",
            # Define field entry: "text": "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type across transaction lifecycles."
            "text": "The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type across transaction lifecycles.",
            # Define field entry: "similarity_score": 94.0
            "similarity_score": 94.0,
            # Define field entry: "ai_content": 27.0
            "ai_content": 27.0,
            # Define field entry: "status": "flagged"
            "status": "flagged",
            # Define field entry: "score": 79.0
            "score": 79.0,
        },
        # Execute statement: {
        {
            # Define field entry: "id": "sub_sneha_018"
            "id": "sub_sneha_018",
            # Define field entry: "name": "Sneha Iyer"
            "name": "Sneha Iyer",
            # Define field entry: "roll": "2024-018"
            "roll": "2024-018",
            # Define field entry: "email": "sneha.iyer@university.edu"
            "email": "sneha.iyer@university.edu",
            # Define field entry: "file_name": "iyer_sneha_graphs.pdf"
            "file_name": "iyer_sneha_graphs.pdf",
            # Define field entry: "text": "Comprehensive analysis of tree and graph traversals with adjacency list representation, cycle detection, and memory profiling."
            "text": "Comprehensive analysis of tree and graph traversals with adjacency list representation, cycle detection, and memory profiling.",
            # Define field entry: "similarity_score": 6.0
            "similarity_score": 6.0,
            # Define field entry: "ai_content": 72.0
            "ai_content": 72.0,
            # Define field entry: "status": "pending"
            "status": "pending",
            # Define field entry: "score": 88.0
            "score": 88.0,
        },
        # Execute statement: {
        {
            # Define field entry: "id": "sub_karan_036"
            "id": "sub_karan_036",
            # Define field entry: "name": "Karan Mehta"
            "name": "Karan Mehta",
            # Define field entry: "roll": "2024-036"
            "roll": "2024-036",
            # Define field entry: "email": "karan.mehta@university.edu"
            "email": "karan.mehta@university.edu",
            # Define field entry: "file_name": "mehta_karan_graphs.pdf"
            "file_name": "mehta_karan_graphs.pdf",
            # Define field entry: "text": "Clean implementation using breadth-first search and depth-first search for directed acyclic graph topological sorting."
            "text": "Clean implementation using breadth-first search and depth-first search for directed acyclic graph topological sorting.",
            # Define field entry: "similarity_score": 4.0
            "similarity_score": 4.0,
            # Define field entry: "ai_content": 12.0
            "ai_content": 12.0,
            # Define field entry: "status": "approved"
            "status": "approved",
            # Define field entry: "score": 84.0
            "score": 84.0,
        },
        # Execute statement: {
        {
            # Define field entry: "id": "sub_meera_029"
            "id": "sub_meera_029",
            # Define field entry: "name": "Meera Nair"
            "name": "Meera Nair",
            # Define field entry: "roll": "2024-029"
            "roll": "2024-029",
            # Define field entry: "email": "meera.nair@university.edu"
            "email": "meera.nair@university.edu",
            # Define field entry: "file_name": "nair_meera_graphs.pdf"
            "file_name": "nair_meera_graphs.pdf",
            # Define field entry: "text": "Exploration of polymorphic interfaces and dynamic dispatch in transactional state machines."
            "text": "Exploration of polymorphic interfaces and dynamic dispatch in transactional state machines.",
            # Define field entry: "similarity_score": 9.0
            "similarity_score": 9.0,
            # Define field entry: "ai_content": 68.0
            "ai_content": 68.0,
            # Define field entry: "status": "pending"
            "status": "pending",
            # Define field entry: "score": 74.0
            "score": 74.0,
        },
        # Execute statement: {
        {
            # Define field entry: "id": "sub_daniel_012"
            "id": "sub_daniel_012",
            # Define field entry: "name": "Daniel Mensah"
            "name": "Daniel Mensah",
            # Define field entry: "roll": "2024-012"
            "roll": "2024-012",
            # Define field entry: "email": "daniel.mensah@university.edu"
            "email": "daniel.mensah@university.edu",
            # Define field entry: "file_name": "mensah_daniel_graphs.pdf"
            "file_name": "mensah_daniel_graphs.pdf",
            # Define field entry: "text": "Optimized memory layout with abstract base classes and generic collections for large ledger datasets."
            "text": "Optimized memory layout with abstract base classes and generic collections for large ledger datasets.",
            # Define field entry: "similarity_score": 3.0
            "similarity_score": 3.0,
            # Define field entry: "ai_content": 18.0
            "ai_content": 18.0,
            # Define field entry: "status": "pending"
            "status": "pending",
            # Define field entry: "score": 91.0
            "score": 91.0,
        },
    ]

    # Set subs_to_insert to []
    subs_to_insert = []
    # Set drafts_to_insert to []
    drafts_to_insert = []

    # Loop over items: s in raw_subs
    for s in raw_subs:
        # Execute statement: subs_to_insert.append({
        subs_to_insert.append({
            # Define field entry: "id": s["id"]
            "id": s["id"],
            # Define field entry: "assignment_id": "assign_oop_a3"
            "assignment_id": "assign_oop_a3",
            # Define field entry: "student_name_encrypted": ferpa_cipher.encrypt(s["name"])
            "student_name_encrypted": ferpa_cipher.encrypt(s["name"]),
            # Define field entry: "student_roll_encrypted": ferpa_cipher.encrypt(s["roll"])
            "student_roll_encrypted": ferpa_cipher.encrypt(s["roll"]),
            # Define field entry: "student_email_encrypted": ferpa_cipher.encrypt(s["email"])
            "student_email_encrypted": ferpa_cipher.encrypt(s["email"]),
            # Define field entry: "file_name": s["file_name"]
            "file_name": s["file_name"],
            # Define field entry: "file_type": "pdf" if s["file_name"].endswith(".pdf") else "docx"
            "file_type": "pdf" if s["file_name"].endswith(".pdf") else "docx",
            # Define field entry: "extracted_text": s["text"]
            "extracted_text": s["text"],
            # Define field entry: "similarity_score": s["similarity_score"]
            "similarity_score": s["similarity_score"],
            # Define field entry: "ai_content_probability": s["ai_content"]
            "ai_content_probability": s["ai_content"],
            # Define field entry: "status": s["status"]
            "status": s["status"],
        # Execute statement: })
        })

        # Set crit_breakdown to [
        crit_breakdown = [
            # Define field entry: {"criterion_name": "Understanding", "score": round(s["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"}
            {"criterion_name": "Understanding", "score": round(s["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"},
            # Define field entry: {"criterion_name": "Accuracy", "score": round(s["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"}
            {"criterion_name": "Accuracy", "score": round(s["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"},
            # Define field entry: {"criterion_name": "Methodology", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"}
            {"criterion_name": "Methodology", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"},
            # Define field entry: {"criterion_name": "Presentation", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"}
            {"criterion_name": "Presentation", "score": round(s["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"},
        ]
        # Execute statement: drafts_to_insert.append({
        drafts_to_insert.append({
            # Define field entry: "id": f"draft_{s['id']}"
            "id": f"draft_{s['id']}",
            # Define field entry: "submission_id": s["id"]
            "submission_id": s["id"],
            # Define field entry: "suggested_score": s["score"]
            "suggested_score": s["score"],
            # Specify argument: "final_score": s["score"] if s["status"] == "approved" else None
            "final_score": s["score"] if s["status"] == "approved" else None,
            # Define field entry: "criteria_scores": crit_breakdown
            "criteria_scores": crit_breakdown,
            # Define field entry: "ai_feedback": "Good understanding of the core concept with accurate class modeling. Methodology depth is moderate."
            "ai_feedback": "Good understanding of the core concept with accurate class modeling. Methodology depth is moderate.",
            # Define field entry: "status": s["status"]
            "status": s["status"],
            # Define field entry: "ai_model": "gemini-2.5-flash"
            "ai_model": "gemini-2.5-flash",
            # Specify argument: "approved_at": datetime.now(timezone.utc).isoformat() if s["status"] == "approved" else None
            "approved_at": datetime.now(timezone.utc).isoformat() if s["status"] == "approved" else None,
            # Specify argument: "approved_by_id": "inst_priya_rao" if s["status"] == "approved" else None
            "approved_by_id": "inst_priya_rao" if s["status"] == "approved" else None,
        # Execute statement: })
        })

    # Execute statement: supabase.table("submissions").upsert(subs_to_insert).execute()
    supabase.table("submissions").upsert(subs_to_insert).execute()
    # Execute statement: supabase.table("draft_grades").upsert(drafts_to_insert).execute()
    supabase.table("draft_grades").upsert(drafts_to_insert).execute()
    # Print console output: print(f"   [OK] {len(subs_to_insert)} Submissions & Draft Grades seeded.")
    print(f"   [OK] {len(subs_to_insert)} Submissions & Draft Grades seeded.")

    # 6. Similarity Match
    print("6. Seeding Similarity Match pair...")
    # Set sim_data to {
    sim_data = {
        # Define field entry: "id": "pair_rahul_amit"
        "id": "pair_rahul_amit",
        # Define field entry: "assignment_id": "assign_oop_a3"
        "assignment_id": "assign_oop_a3",
        # Define field entry: "submission_a_id": "sub_rahul_047"
        "submission_a_id": "sub_rahul_047",
        # Define field entry: "submission_b_id": "sub_amit_051"
        "submission_b_id": "sub_amit_051",
        # Define field entry: "similarity_score": 94.0
        "similarity_score": 94.0,
        # Execute statement: "matching_phrases": [
        "matching_phrases": [
            # Execute statement: "…branches into Savings and Current subtypes, overriding the interest metho
            "…branches into Savings and Current subtypes, overriding the interest method…"
        ],
        # Define field entry: "status": "High similarity"
        "status": "High similarity",
        # Define field entry: "teacher_note": "Awaiting teacher verification of polymorphic ledger source excerpts."
        "teacher_note": "Awaiting teacher verification of polymorphic ledger source excerpts.",
    }
    # Execute statement: supabase.table("similarity_matches").upsert(sim_data).execute()
    supabase.table("similarity_matches").upsert(sim_data).execute()
    # Print console output: print("   [OK] Similarity Match seeded.")
    print("   [OK] Similarity Match seeded.")

    # 7. Audit Log
    print("7. Seeding Audit Log...")
    # Set audit_data to {
    audit_data = {
        # Define field entry: "id": "audit_supabase_init"
        "id": "audit_supabase_init",
        # Define field entry: "actor_id": "inst_priya_rao"
        "actor_id": "inst_priya_rao",
        # Define field entry: "actor_name": "Dr. Priya Rao"
        "actor_name": "Dr. Priya Rao",
        # Define field entry: "action": "SYSTEM_INIT_SEED"
        "action": "SYSTEM_INIT_SEED",
        # Define field entry: "entity_type": "Course"
        "entity_type": "Course",
        # Define field entry: "entity_id": "c_cs203"
        "entity_id": "c_cs203",
        # Define field entry: "details": {"event": "Supabase PostgreSQL Database seeded successfully with FERPA encryption enabled"}
        "details": {"event": "Supabase PostgreSQL Database seeded successfully with FERPA encryption enabled"},
        # Define field entry: "ip_address": "127.0.0.1"
        "ip_address": "127.0.0.1",
    }
    # Execute statement: supabase.table("audit_logs").upsert(audit_data).execute()
    supabase.table("audit_logs").upsert(audit_data).execute()
    # Print console output: print("   [OK] Audit log seeded.")
    print("   [OK] Audit log seeded.")

    # Print console output: print("\n[SUCCESS] New Supabase database completely seeded and ready for production use!")
    print("\n[SUCCESS] New Supabase database completely seeded and ready for production use!")


# Check if condition: __name__ == "__main__"
if __name__ == "__main__":
    # Execute statement: seed_supabase()
    seed_supabase()
