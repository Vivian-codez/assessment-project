"""Database Seeding Script.

Populates initial courses, assignments, rubrics, submissions (with FERPA
encryption), draft grades, and similarity matches matching the Verism AI
frontend.
"""

import os
import sys
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.models.instructor import Instructor
from app.models.course import Course
from app.models.rubric import Rubric, RubricCriterion
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.models.audit_log import AuditLog
from app.core.security import get_password_hash


def seed():
    print("Initializing tables...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded with primary course
        if db.query(Course).filter(Course.id == "c_cs203").first():
            print("Database already contains seed data for c_cs203. Skipping.")
            return

        instructor = db.query(Instructor).filter(Instructor.email == "priya.rao@university.edu").first()
        if not instructor:
            print("Seeding Instructor Dr. Priya Rao...")
            instructor = Instructor(
                id="inst_priya_rao",
                name="Dr. Priya Rao",
                email="priya.rao@university.edu",
                role="Instructor · Computer Science",
                hashed_password=get_password_hash("teacher123"),
                preferences={
                    "show_similarity_context": True,
                    "require_teacher_notes_on_overrides": False,
                    "include_ai_content_indicator": True,
                },
            )
            db.add(instructor)
            db.flush()

        print("Seeding Courses...")
        courses_data = [
            {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav"},
            {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue"},
            {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage"},
            {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber"},
        ]
        for cd in courses_data:
            course = Course(instructor_id=instructor.id, **cd)
            db.add(course)

        print("Seeding Rubric...")
        rubric = Rubric(
            id="rub_oop_a3",
            name="Assignment 3 · OOP & Polymorphism Rubric",
            course_id="c_cs203",
            total_max_score=100.0,
        )
        db.add(rubric)

        criteria_data = [
            {"id": "crit_1", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0},
            {"id": "crit_2", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1},
            {"id": "crit_3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2},
            {"id": "crit_4", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3},
        ]
        for c in criteria_data:
            crit = RubricCriterion(rubric_id=rubric.id, **c)
            db.add(crit)

        print("Seeding Assignment...")
        assignment = Assignment(
            id="assign_oop_a3",
            course_id="c_cs203",
            title="Assignment 3 · Graph Traversal & Ledger Modeling",
            description="Implementation of banking transaction ledger and polymorphic account hierarchies.",
            due_date=datetime(2026, 10, 25, 23, 59, 59),
            max_score=100.0,
            rubric_id=rubric.id,
        )
        db.add(assignment)

        print("Seeding Submissions (with FERPA encryption)...")
        submissions_data = [
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

        for sdata in submissions_data:
            sub = Submission(
                id=sdata["id"],
                assignment_id=assignment.id,
                file_name=sdata["file_name"],
                extracted_text=sdata["text"],
                similarity_score=sdata["similarity_score"],
                ai_content_probability=sdata["ai_content"],
                status=sdata["status"],
            )
            # FERPA transparent encrypted properties
            sub.student_name = sdata["name"]
            sub.student_roll = sdata["roll"]
            sub.student_email = sdata["email"]
            db.add(sub)

            # Draft Grade
            crit_breakdown = [
                {"criterion_name": "Understanding", "score": round(sdata["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"},
                {"criterion_name": "Accuracy", "score": round(sdata["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"},
                {"criterion_name": "Methodology", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"},
                {"criterion_name": "Presentation", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"},
            ]
            draft = DraftGrade(
                id=f"draft_{sdata['id']}",
                submission_id=sdata["id"],
                suggested_score=sdata["score"],
                final_score=sdata["score"] if sdata["status"] == "approved" else None,
                criteria_scores=crit_breakdown,
                ai_feedback="Good understanding of the core concept with accurate class modeling. Methodology depth is moderate.",
                status=sdata["status"],
                ai_model="gemini-2.5-flash",
                approved_at=datetime.utcnow() if sdata["status"] == "approved" else None,
                approved_by_id=instructor.id if sdata["status"] == "approved" else None,
            )
            db.add(draft)

        print("Seeding Similarity Pair Flag...")
        sim_match = SimilarityMatch(
            id="pair_rahul_amit",
            assignment_id=assignment.id,
            submission_a_id="sub_rahul_047",
            submission_b_id="sub_amit_051",
            similarity_score=94.0,
            matching_phrases=[
                "…branches into Savings and Current subtypes, overriding the interest method…"
            ],
            status="High similarity",
        )
        db.add(sim_match)

        audit = AuditLog(
            id="audit_init",
            actor_id=instructor.id,
            actor_name=instructor.name,
            action="SYSTEM_INIT_SEED",
            entity_type="Course",
            entity_id="c_cs203",
            details={"event": "Initial seed load complete with FERPA encryption enabled"},
        )
        db.add(audit)

        db.commit()
        print("Database seeded successfully with all initial records!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed()
