# Docstring explaining Database Seeding Script.
"""Database Seeding Script.

Populates initial courses, assignments, rubrics, submissions (with FERPA
encryption), draft grades, and similarity matches matching the Verism AI
frontend.
"""

# Import module os
import os
# Import module sys
import sys
# Import datetime from datetime
from datetime import datetime

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import SessionLocal, engine, Base from app.core.database
from app.core.database import SessionLocal, engine, Base
# Import Instructor from app.models.instructor
from app.models.instructor import Instructor
# Import Course from app.models.course
from app.models.course import Course
# Import Rubric, RubricCriterion from app.models.rubric
from app.models.rubric import Rubric, RubricCriterion
# Import Assignment from app.models.assignment
from app.models.assignment import Assignment
# Import Submission from app.models.submission
from app.models.submission import Submission
# Import DraftGrade from app.models.draft_grade
from app.models.draft_grade import DraftGrade
# Import SimilarityMatch from app.models.similarity_match
from app.models.similarity_match import SimilarityMatch
# Import AuditLog from app.models.audit_log
from app.models.audit_log import AuditLog
# Import get_password_hash from app.core.security
from app.core.security import get_password_hash


# Define function seed
def seed():
    # Print console output: print("Initializing tables...")
    print("Initializing tables...")
    # Execute statement: Base.metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Set db to SessionLocal()
    db = SessionLocal()

    # Begin try block to handle operations safely
    try:
        # Check if already seeded with primary course
        if db.query(Course).filter(Course.id == "c_cs203").first():
            # Print console output: print("Database already contains seed data for c_cs203. Skipping.")
            print("Database already contains seed data for c_cs203. Skipping.")
            # Return from function
            return

        # Set instructor to db.query(Instructor).filter(Instructor.email == "priya.rao@university.edu").first()
        instructor = db.query(Instructor).filter(Instructor.email == "priya.rao@university.edu").first()
        # Check if condition: not instructor
        if not instructor:
            # Print console output: print("Seeding Instructor Dr. Priya Rao...")
            print("Seeding Instructor Dr. Priya Rao...")
            # Set instructor to Instructor(
            instructor = Instructor(
                # Specify argument: id="inst_priya_rao"
                id="inst_priya_rao",
                # Specify argument: name="Dr. Priya Rao"
                name="Dr. Priya Rao",
                # Specify argument: email="priya.rao@university.edu"
                email="priya.rao@university.edu",
                # Specify argument: role="Instructor · Computer Science"
                role="Instructor · Computer Science",
                # Specify argument: hashed_password=get_password_hash("teacher123")
                hashed_password=get_password_hash("teacher123"),
                # Execute statement: preferences={
                preferences={
                    # Define field entry: "show_similarity_context": True
                    "show_similarity_context": True,
                    # Define field entry: "require_teacher_notes_on_overrides": False
                    "require_teacher_notes_on_overrides": False,
                    # Define field entry: "include_ai_content_indicator": True
                    "include_ai_content_indicator": True,
                },
            )
            # Stage entity into database session: db.add(instructor)
            db.add(instructor)
            # Execute statement: db.flush()
            db.flush()

        # Print console output: print("Seeding Courses...")
        print("Seeding Courses...")
        # Set courses_data to [
        courses_data = [
            # Define field entry: {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav"}
            {"id": "c_cs201", "name": "Data Structures", "code": "CS201", "section": "A", "students_count": 48, "tone": "lav"},
            # Define field entry: {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue"}
            {"id": "c_cs202", "name": "Database Management Systems", "code": "CS202", "section": "B", "students_count": 42, "tone": "blue"},
            # Define field entry: {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage"}
            {"id": "c_cs203", "name": "Object Oriented Programming", "code": "CS203", "section": "A", "students_count": 62, "tone": "sage"},
            # Define field entry: {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber"}
            {"id": "c_ds301", "name": "Machine Learning", "code": "DS301", "section": "A", "students_count": 36, "tone": "amber"},
        ]
        # Loop over items: cd in courses_data
        for cd in courses_data:
            # Set course to Course(instructor_id=instructor.id, **cd)
            course = Course(instructor_id=instructor.id, **cd)
            # Stage entity into database session: db.add(course)
            db.add(course)

        # Print console output: print("Seeding Rubric...")
        print("Seeding Rubric...")
        # Set rubric to Rubric(
        rubric = Rubric(
            # Specify argument: id="rub_oop_a3"
            id="rub_oop_a3",
            # Specify argument: name="Assignment 3 · OOP & Polymorphism Rubric"
            name="Assignment 3 · OOP & Polymorphism Rubric",
            # Specify argument: course_id="c_cs203"
            course_id="c_cs203",
            # Specify argument: total_max_score=100.0
            total_max_score=100.0,
        )
        # Stage entity into database session: db.add(rubric)
        db.add(rubric)

        # Set criteria_data to [
        criteria_data = [
            # Define field entry: {"id": "crit_1", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0}
            {"id": "crit_1", "name": "Understanding", "description": "Conceptual clarity and depth", "weight": 30.0, "max_score": 30.0, "order_index": 0},
            # Define field entry: {"id": "crit_2", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1}
            {"id": "crit_2", "name": "Accuracy", "description": "Correctness of solution", "weight": 30.0, "max_score": 30.0, "order_index": 1},
            # Define field entry: {"id": "crit_3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2}
            {"id": "crit_3", "name": "Methodology", "description": "Process and reasoning", "weight": 20.0, "max_score": 20.0, "order_index": 2},
            # Define field entry: {"id": "crit_4", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3}
            {"id": "crit_4", "name": "Presentation", "description": "Structure and communication", "weight": 20.0, "max_score": 20.0, "order_index": 3},
        ]
        # Loop over items: c in criteria_data
        for c in criteria_data:
            # Set crit to RubricCriterion(rubric_id=rubric.id, **c)
            crit = RubricCriterion(rubric_id=rubric.id, **c)
            # Stage entity into database session: db.add(crit)
            db.add(crit)

        # Print console output: print("Seeding Assignment...")
        print("Seeding Assignment...")
        # Set assignment to Assignment(
        assignment = Assignment(
            # Specify argument: id="assign_oop_a3"
            id="assign_oop_a3",
            # Specify argument: course_id="c_cs203"
            course_id="c_cs203",
            # Specify argument: title="Assignment 3 · Graph Traversal & Ledger Modeling"
            title="Assignment 3 · Graph Traversal & Ledger Modeling",
            # Specify argument: description="Implementation of banking transaction ledger and polymorphic account hierarchies."
            description="Implementation of banking transaction ledger and polymorphic account hierarchies.",
            # Specify argument: due_date=datetime(2026, 10, 25, 23, 59, 59)
            due_date=datetime(2026, 10, 25, 23, 59, 59),
            # Specify argument: max_score=100.0
            max_score=100.0,
            # Specify argument: rubric_id=rubric.id
            rubric_id=rubric.id,
        )
        # Stage entity into database session: db.add(assignment)
        db.add(assignment)

        # Print console output: print("Seeding Submissions (with FERPA encryption)...")
        print("Seeding Submissions (with FERPA encryption)...")
        # Set submissions_data to [
        submissions_data = [
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

        # Loop over items: sdata in submissions_data
        for sdata in submissions_data:
            # Set sub to Submission(
            sub = Submission(
                # Specify argument: id=sdata["id"]
                id=sdata["id"],
                # Specify argument: assignment_id=assignment.id
                assignment_id=assignment.id,
                # Specify argument: file_name=sdata["file_name"]
                file_name=sdata["file_name"],
                # Specify argument: extracted_text=sdata["text"]
                extracted_text=sdata["text"],
                # Specify argument: similarity_score=sdata["similarity_score"]
                similarity_score=sdata["similarity_score"],
                # Specify argument: ai_content_probability=sdata["ai_content"]
                ai_content_probability=sdata["ai_content"],
                # Specify argument: status=sdata["status"]
                status=sdata["status"],
            )
            # FERPA transparent encrypted properties
            sub.student_name = sdata["name"]
            # Set sub.student_roll to sdata["roll"]
            sub.student_roll = sdata["roll"]
            # Set sub.student_email to sdata["email"]
            sub.student_email = sdata["email"]
            # Stage entity into database session: db.add(sub)
            db.add(sub)

            # Draft Grade
            crit_breakdown = [
                # Define field entry: {"criterion_name": "Understanding", "score": round(sdata["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"}
                {"criterion_name": "Understanding", "score": round(sdata["score"] * 0.30, 1), "max": 30.0, "rationale": "Clear conceptual grounding"},
                # Define field entry: {"criterion_name": "Accuracy", "score": round(sdata["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"}
                {"criterion_name": "Accuracy", "score": round(sdata["score"] * 0.32, 1), "max": 30.0, "rationale": "Accurate algorithm structure"},
                # Define field entry: {"criterion_name": "Methodology", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"}
                {"criterion_name": "Methodology", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Sound methodology"},
                # Define field entry: {"criterion_name": "Presentation", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"}
                {"criterion_name": "Presentation", "score": round(sdata["score"] * 0.19, 1), "max": 20.0, "rationale": "Well structured documentation"},
            ]
            # Set draft to DraftGrade(
            draft = DraftGrade(
                # Specify argument: id=f"draft_{sdata['id']}"
                id=f"draft_{sdata['id']}",
                # Specify argument: submission_id=sdata["id"]
                submission_id=sdata["id"],
                # Specify argument: suggested_score=sdata["score"]
                suggested_score=sdata["score"],
                # Specify argument: final_score=sdata["score"] if sdata["status"] == "approved" else None
                final_score=sdata["score"] if sdata["status"] == "approved" else None,
                # Specify argument: criteria_scores=crit_breakdown
                criteria_scores=crit_breakdown,
                # Specify argument: ai_feedback="Good understanding of the core concept with accurate class modeling. Methodology depth is moderate."
                ai_feedback="Good understanding of the core concept with accurate class modeling. Methodology depth is moderate.",
                # Specify argument: status=sdata["status"]
                status=sdata["status"],
                # Specify argument: ai_model="gemini-2.5-flash"
                ai_model="gemini-2.5-flash",
                # Specify argument: approved_at=datetime.utcnow() if sdata["status"] == "approved" else None
                approved_at=datetime.utcnow() if sdata["status"] == "approved" else None,
                # Specify argument: approved_by_id=instructor.id if sdata["status"] == "approved" else None
                approved_by_id=instructor.id if sdata["status"] == "approved" else None,
            )
            # Stage entity into database session: db.add(draft)
            db.add(draft)

        # Print console output: print("Seeding Similarity Pair Flag...")
        print("Seeding Similarity Pair Flag...")
        # Set sim_match to SimilarityMatch(
        sim_match = SimilarityMatch(
            # Specify argument: id="pair_rahul_amit"
            id="pair_rahul_amit",
            # Specify argument: assignment_id=assignment.id
            assignment_id=assignment.id,
            # Specify argument: submission_a_id="sub_rahul_047"
            submission_a_id="sub_rahul_047",
            # Specify argument: submission_b_id="sub_amit_051"
            submission_b_id="sub_amit_051",
            # Specify argument: similarity_score=94.0
            similarity_score=94.0,
            # Execute statement: matching_phrases=[
            matching_phrases=[
                # Execute statement: "…branches into Savings and Current subtypes, overriding the interest metho
                "…branches into Savings and Current subtypes, overriding the interest method…"
            ],
            # Specify argument: status="High similarity"
            status="High similarity",
        )
        # Stage entity into database session: db.add(sim_match)
        db.add(sim_match)

        # Set audit to AuditLog(
        audit = AuditLog(
            # Specify argument: id="audit_init"
            id="audit_init",
            # Specify argument: actor_id=instructor.id
            actor_id=instructor.id,
            # Specify argument: actor_name=instructor.name
            actor_name=instructor.name,
            # Specify argument: action="SYSTEM_INIT_SEED"
            action="SYSTEM_INIT_SEED",
            # Specify argument: entity_type="Course"
            entity_type="Course",
            # Specify argument: entity_id="c_cs203"
            entity_id="c_cs203",
            # Specify argument: details={"event": "Initial seed load complete with FERPA encryption enabled"}
            details={"event": "Initial seed load complete with FERPA encryption enabled"},
        )
        # Stage entity into database session: db.add(audit)
        db.add(audit)

        # Commit transaction to database
        db.commit()
        # Print console output: print("Database seeded successfully with all initial records!")
        print("Database seeded successfully with all initial records!")

    # Handle exception during execution: except Exception as e
    except Exception as e:
        # Rollback database transaction on error
        db.rollback()
        # Print console output: print(f"Error seeding database: {e}")
        print(f"Error seeding database: {e}")
        # Raise exception: e
        raise e
    # Execute cleanup block in finally clause
    finally:
        # Execute statement: db.close()
        db.close()


# Check if condition: __name__ == "__main__"
if __name__ == "__main__":
    # Execute statement: seed()
    seed()
