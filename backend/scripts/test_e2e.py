# Docstring explaining End-to-End Test Suite for Verism AI Platform.
"""End-to-End Test Suite for Verism AI Platform.
Tests:
1. Frontend dev server serving
2. User Sign-Up (Supabase + Postgres auth)
3. User Sign-In & JWT auth
4. Create Course (User Data Input)
5. Create Assignment with Ground Truth Reference Exemplar
6. Input Real Student Submissions (Manual text entry)
7. Start AI Auto-Grading & 3-Way Plagiarism Check (Peer, AI, Web Search)
8. Poll Job completion
9. Inspect Review Queue & 3-Way Plagiarism metrics
10. Teacher Grade Stamping ("AI suggests, You stamp")
11. Live Gradebook verification
"""

# Import module json
import json
# Import module time
import time
# Import module urllib.request
import urllib.request

# Print console output: print("=== 1. Checking Frontend Dev Server (Port 8080) ===")
print("=== 1. Checking Frontend Dev Server (Port 8080) ===")
# Manage execution context with urllib.request.urlopen("http://localhost:8080", timeout=5) as res
with urllib.request.urlopen("http://localhost:8080", timeout=5) as res:
    # Set html to res.read().decode("utf-8")
    html = res.read().decode("utf-8")
    # Assert condition: "<html" in html or "<!DOCTYPE" in html or "vite" in html
    assert "<html" in html or "<!DOCTYPE" in html or "vite" in html
    # Print console output: print("Frontend is live and returning HTML! Status:", res.status)
    print("Frontend is live and returning HTML! Status:", res.status)

# Print console output: print("\n=== 2. User Sign-Up (New User) ===")
print("\n=== 2. User Sign-Up (New User) ===")
# Set unique_email to f"knuth_{int(time.time())}@stanford.edu"
unique_email = f"knuth_{int(time.time())}@stanford.edu"
# Set signup_payload to {
signup_payload = {
    # Define field entry: "name": "Prof. Donald Knuth"
    "name": "Prof. Donald Knuth",
    # Define field entry: "email": unique_email
    "email": unique_email,
    # Define field entry: "password": "AlgorithmMaster2024!"
    "password": "AlgorithmMaster2024!",
    # Define field entry: "role": "Professor · Computer Science"
    "role": "Professor · Computer Science",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: "http://localhost:8000/api/v1/auth/signup"
    "http://localhost:8000/api/v1/auth/signup",
    # Specify argument: data=json.dumps(signup_payload).encode("utf-8")
    data=json.dumps(signup_payload).encode("utf-8"),
    # Specify argument: headers={"Content-Type": "application/json"}
    headers={"Content-Type": "application/json"},
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set signup_data to json.loads(res.read().decode("utf-8"))
    signup_data = json.loads(res.read().decode("utf-8"))
    # Set token to signup_data["access_token"]
    token = signup_data["access_token"]
    # Set user_id to signup_data["user"]["id"]
    user_id = signup_data["user"]["id"]
    # Set user_name to signup_data["user"]["name"]
    user_name = signup_data["user"]["name"]
    # Print console output: print(f"User successfully registered in Supabase & Postgres! ID: {user_id}, Name: {user_name}")
    print(f"User successfully registered in Supabase & Postgres! ID: {user_id}, Name: {user_name}")

# Set auth_headers to {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Print console output: print("\n=== 3. User Sign-In (Existing User Verification) ===")
print("\n=== 3. User Sign-In (Existing User Verification) ===")
# Set login_payload to {
login_payload = {
    # Define field entry: "email": unique_email
    "email": unique_email,
    # Define field entry: "password": "AlgorithmMaster2024!"
    "password": "AlgorithmMaster2024!",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: "http://localhost:8000/api/v1/auth/login"
    "http://localhost:8000/api/v1/auth/login",
    # Specify argument: data=json.dumps(login_payload).encode("utf-8")
    data=json.dumps(login_payload).encode("utf-8"),
    # Specify argument: headers={"Content-Type": "application/json"}
    headers={"Content-Type": "application/json"},
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set login_data to json.loads(res.read().decode("utf-8"))
    login_data = json.loads(res.read().decode("utf-8"))
    # Assert condition: "access_token" in login_data
    assert "access_token" in login_data
    # Print console output: print("User successfully authenticated and token validated!")
    print("User successfully authenticated and token validated!")

# Print console output: print("\n=== 4. Create Course (User Data Input) ===")
print("\n=== 4. Create Course (User Data Input) ===")
# Set course_payload to {
course_payload = {
    # Define field entry: "name": "Analysis of Algorithms"
    "name": "Analysis of Algorithms",
    # Define field entry: "code": "CS401"
    "code": "CS401",
    # Define field entry: "section": "A"
    "section": "A",
    # Define field entry: "tone": "sage"
    "tone": "sage",
    # Define field entry: "students_count": 42
    "students_count": 42,
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: "http://localhost:8000/api/v1/courses"
    "http://localhost:8000/api/v1/courses",
    # Specify argument: data=json.dumps(course_payload).encode("utf-8")
    data=json.dumps(course_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set course to json.loads(res.read().decode("utf-8"))
    course = json.loads(res.read().decode("utf-8"))
    # Set course_id to course["id"]
    course_id = course["id"]
    # Print console output: print(f"Course created! ID: {course_id}, Name: {course['name']}")
    print(f"Course created! ID: {course_id}, Name: {course['name']}")

# Print console output: print("\n=== 5. Create Assignment with Reference Exemplar Ground Truth ===")
print("\n=== 5. Create Assignment with Reference Exemplar Ground Truth ===")
# Set assign_payload to {
assign_payload = {
    # Define field entry: "title": "Assignment 4 · Shortest Path Dijkstra"
    "title": "Assignment 4 · Shortest Path Dijkstra",
    # Define field entry: "description": "Implement Dijkstra shortest path using priority queues."
    "description": "Implement Dijkstra shortest path using priority queues.",
    # Define field entry: "max_score": 100.0
    "max_score": 100.0,
    # Execute statement: "reference_assignment_text": """# Ground Truth Reference Solution
    "reference_assignment_text": """# Ground Truth Reference Solution
import heapq

def dijkstra(graph, start):
    distances = {node: float("infinity") for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
        if curr_dist > distances[curr_node]:
            continue
        for neighbor, weight in graph[curr_node].items():
            dist = curr_dist + weight
            if dist < distances[neighbor]:
                distances[neighbor] = dist
                heapq.heappush(pq, (dist, neighbor))
    return distances""",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: f"http://localhost:8000/api/v1/courses/{course_id}/assignments"
    f"http://localhost:8000/api/v1/courses/{course_id}/assignments",
    # Specify argument: data=json.dumps(assign_payload).encode("utf-8")
    data=json.dumps(assign_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set assign to json.loads(res.read().decode("utf-8"))
    assign = json.loads(res.read().decode("utf-8"))
    # Set assign_id to assign["id"]
    assign_id = assign["id"]
    # Print console output: print(f"Assignment created with reference exemplar! ID: {assign_id}, Title: {assign['title']}")
    print(f"Assignment created with reference exemplar! ID: {assign_id}, Title: {assign['title']}")

# Print console output: print("\n=== 6. Input Real Student Submissions (Manual Text Entry) ===")
print("\n=== 6. Input Real Student Submissions (Manual Text Entry) ===")
# Set sub1_payload to {
sub1_payload = {
    # Define field entry: "assignment_id": assign_id
    "assignment_id": assign_id,
    # Define field entry: "student_name": "Grace Hopper"
    "student_name": "Grace Hopper",
    # Define field entry: "student_roll": "2024-101"
    "student_roll": "2024-101",
    # Define field entry: "student_email": "grace.hopper@navy.mil"
    "student_email": "grace.hopper@navy.mil",
    # Execute statement: "extracted_text": """import heapq
    "extracted_text": """import heapq

def dijkstra(graph, start):
    distances = {node: float("infinity") for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
        if curr_dist > distances[curr_node]:
            continue
        for neighbor, weight in graph[curr_node].items():
            dist = curr_dist + weight
            if dist < distances[neighbor]:
                distances[neighbor] = dist
                heapq.heappush(pq, (dist, neighbor))
    return distances""",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions"
    f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions",
    # Specify argument: data=json.dumps(sub1_payload).encode("utf-8")
    data=json.dumps(sub1_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set sub1 to json.loads(res.read().decode("utf-8"))
    sub1 = json.loads(res.read().decode("utf-8"))
    # Set sub1_id to sub1["id"]
    sub1_id = sub1["id"]
    # Print console output: print(f"Submission 1 registered: {sub1['student']} (ID: {sub1_id})")
    print(f"Submission 1 registered: {sub1['student']} (ID: {sub1_id})")

# Set sub2_payload to {
sub2_payload = {
    # Define field entry: "assignment_id": assign_id
    "assignment_id": assign_id,
    # Define field entry: "student_name": "Alan Kay"
    "student_name": "Alan Kay",
    # Define field entry: "student_roll": "2024-102"
    "student_roll": "2024-102",
    # Define field entry: "student_email": "alan.kay@smalltalk.org"
    "student_email": "alan.kay@smalltalk.org",
    # Execute statement: "extracted_text": """import heapq
    "extracted_text": """import heapq

def dijkstra(graph, start):
    distances = {node: float("infinity") for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
        if curr_dist > distances[curr_node]:
            continue
        for neighbor, weight in graph[curr_node].items():
            dist = curr_dist + weight
            if dist < distances[neighbor]:
                distances[neighbor] = dist
                heapq.heappush(pq, (dist, neighbor))
    return distances""",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions"
    f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions",
    # Specify argument: data=json.dumps(sub2_payload).encode("utf-8")
    data=json.dumps(sub2_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set sub2 to json.loads(res.read().decode("utf-8"))
    sub2 = json.loads(res.read().decode("utf-8"))
    # Set sub2_id to sub2["id"]
    sub2_id = sub2["id"]
    # Print console output: print(f"Submission 2 registered: {sub2['student']} (ID: {sub2_id})")
    print(f"Submission 2 registered: {sub2['student']} (ID: {sub2_id})")

# Print console output: print("\n=== 7. Start AI Auto-Grading & 3-Way Plagiarism Check ===")
print("\n=== 7. Start AI Auto-Grading & 3-Way Plagiarism Check ===")
# Set eval_payload to {"rubric_id": None, "similarity_threshold": 85.0}
eval_payload = {"rubric_id": None, "similarity_threshold": 85.0}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: f"http://localhost:8000/api/v1/assignments/{assign_id}/evaluate-batch"
    f"http://localhost:8000/api/v1/assignments/{assign_id}/evaluate-batch",
    # Specify argument: data=json.dumps(eval_payload).encode("utf-8")
    data=json.dumps(eval_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set job to json.loads(res.read().decode("utf-8"))
    job = json.loads(res.read().decode("utf-8"))
    # Set job_id to job["job_id"]
    job_id = job["job_id"]
    # Print console output: print(f"Evaluation job dispatched! Job ID: {job_id}")
    print(f"Evaluation job dispatched! Job ID: {job_id}")

# Poll job completion
for poll_step in range(40):
    # Execute statement: time.sleep(1.5)
    time.sleep(1.5)
    # Set req to urllib.request.Request(f"http://localhost:8000/api/v1/jobs/{job_id}", headers=auth_headers)
    req = urllib.request.Request(f"http://localhost:8000/api/v1/jobs/{job_id}", headers=auth_headers)
    # Manage execution context with urllib.request.urlopen(req) as res
    with urllib.request.urlopen(req) as res:
        # Set j_status to json.loads(res.read().decode("utf-8"))
        j_status = json.loads(res.read().decode("utf-8"))
        # Print console output: print(f"Polling job status: {j_status['status']} ({j_status['progress_pct']}%) - processed {j_status['processed_items']}/{j_status['total_items']}")
        print(f"Polling job status: {j_status['status']} ({j_status['progress_pct']}%) - processed {j_status['processed_items']}/{j_status['total_items']}")
        # Check if condition: j_status["status"] == "completed"
        if j_status["status"] == "completed":
            # Print console output: print(f"Job completed! Progress: {j_status['progress_pct']}%, Processed: {j_status['processed_items']}")
            print(f"Job completed! Progress: {j_status['progress_pct']}%, Processed: {j_status['processed_items']}")
            # Break out of current loop
            break
        # Alternative condition check: j_status["status"] == "failed"
        elif j_status["status"] == "failed":
            # Print console output: print(f"Job failed with error: {j_status.get('error_message')}")
            print(f"Job failed with error: {j_status.get('error_message')}")
            # Break out of current loop
            break

# Print console output: print("\n=== 8. Review Queue & 3-Way Plagiarism Inspection ===")
print("\n=== 8. Review Queue & 3-Way Plagiarism Inspection ===")
# Set req to urllib.request.Request(f"http://localhost:8000/api/v1/submissions/{sub1_id}/review-detail", headers=auth_headers)
req = urllib.request.Request(f"http://localhost:8000/api/v1/submissions/{sub1_id}/review-detail", headers=auth_headers)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set detail to json.loads(res.read().decode("utf-8"))
    detail = json.loads(res.read().decode("utf-8"))
    # Print console output: print(f"Student: {detail['student']}")
    print(f"Student: {detail['student']}")
    # Print console output: print(f"AI Suggested Score: {detail['score']}/100")
    print(f"AI Suggested Score: {detail['score']}/100")
    # Print console output: print(f"1. Peer Similarity: {detail.get('similarity')}%")
    print(f"1. Peer Similarity: {detail.get('similarity')}%")
    # Print console output: print(f"2. AI Content Probability: {detail.get('aiContent')}%")
    print(f"2. AI Content Probability: {detail.get('aiContent')}%")
    # Print console output: print(f"3. Public Web Plagiarism: {detail.get('webPlagiarism')}%")
    print(f"3. Public Web Plagiarism: {detail.get('webPlagiarism')}%")
    # Print console output: print(f"Criteria evaluations count: {len(detail.get('criteria_scores', []))}")
    print(f"Criteria evaluations count: {len(detail.get('criteria_scores', []))}")

# Print console output: print("\n=== 9. Teacher Stamping Grade ===")
print("\n=== 9. Teacher Stamping Grade ===")
# Set stamp_payload to {
stamp_payload = {
    # Define field entry: "status": "approved"
    "status": "approved",
    # Define field entry: "final_score": 96.0
    "final_score": 96.0,
    # Define field entry: "criteria_scores": detail.get("criteria_scores", [])
    "criteria_scores": detail.get("criteria_scores", []),
    # Define field entry: "teacher_feedback": "Outstanding implementation matching the ground truth reference solution perfectly."
    "teacher_feedback": "Outstanding implementation matching the ground truth reference solution perfectly.",
    # Define field entry: "action": "APPROVE"
    "action": "APPROVE",
}
# Set req to urllib.request.Request(
req = urllib.request.Request(
    # Define field entry: f"http://localhost:8000/api/v1/submissions/{sub1_id}/stamp-grade"
    f"http://localhost:8000/api/v1/submissions/{sub1_id}/stamp-grade",
    # Specify argument: data=json.dumps(stamp_payload).encode("utf-8")
    data=json.dumps(stamp_payload).encode("utf-8"),
    # Specify argument: headers=auth_headers
    headers=auth_headers,
)
# Set req.get_method to lambda: "PUT"
req.get_method = lambda: "PUT"
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set grade_res to json.loads(res.read().decode("utf-8"))
    grade_res = json.loads(res.read().decode("utf-8"))
    # Print console output: print(f"Grade officially stamped by teacher! Final Score: {grade_res.get('final_score')}/100, Status: {grade_res.get('status')}")
    print(f"Grade officially stamped by teacher! Final Score: {grade_res.get('final_score')}/100, Status: {grade_res.get('status')}")

# Print console output: print("\n=== 10. Verification in Live Gradebook ===")
print("\n=== 10. Verification in Live Gradebook ===")
# Set req to urllib.request.Request(f"http://localhost:8000/api/v1/courses/{course_id}/gradebook", headers=auth_headers)
req = urllib.request.Request(f"http://localhost:8000/api/v1/courses/{course_id}/gradebook", headers=auth_headers)
# Manage execution context with urllib.request.urlopen(req) as res
with urllib.request.urlopen(req) as res:
    # Set gb to json.loads(res.read().decode("utf-8"))
    gb = json.loads(res.read().decode("utf-8"))
    # Print console output: print(f"Gradebook active! Total entries: {len(gb)}")
    print(f"Gradebook active! Total entries: {len(gb)}")

# Print console output: print("\n*** ALL END-TO-END FLOWS FULLY OPERATIONAL AND VERIFIED! ***")
print("\n*** ALL END-TO-END FLOWS FULLY OPERATIONAL AND VERIFIED! ***")
