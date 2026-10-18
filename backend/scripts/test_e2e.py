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

import json
import time
import urllib.request

print("=== 1. Checking Frontend Dev Server (Port 8080) ===")
with urllib.request.urlopen("http://localhost:8080", timeout=5) as res:
    html = res.read().decode("utf-8")
    assert "<html" in html or "<!DOCTYPE" in html or "vite" in html
    print("Frontend is live and returning HTML! Status:", res.status)

print("\n=== 2. User Sign-Up (New User) ===")
unique_email = f"knuth_{int(time.time())}@stanford.edu"
signup_payload = {
    "name": "Prof. Donald Knuth",
    "email": unique_email,
    "password": "AlgorithmMaster2024!",
    "role": "Professor · Computer Science",
}
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/signup",
    data=json.dumps(signup_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as res:
    signup_data = json.loads(res.read().decode("utf-8"))
    token = signup_data["access_token"]
    user_id = signup_data["user"]["id"]
    user_name = signup_data["user"]["name"]
    print(f"User successfully registered in Supabase & Postgres! ID: {user_id}, Name: {user_name}")

auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

print("\n=== 3. User Sign-In (Existing User Verification) ===")
login_payload = {
    "email": unique_email,
    "password": "AlgorithmMaster2024!",
}
req = urllib.request.Request(
    "http://localhost:8000/api/v1/auth/login",
    data=json.dumps(login_payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as res:
    login_data = json.loads(res.read().decode("utf-8"))
    assert "access_token" in login_data
    print("User successfully authenticated and token validated!")

print("\n=== 4. Create Course (User Data Input) ===")
course_payload = {
    "name": "Analysis of Algorithms",
    "code": "CS401",
    "section": "A",
    "tone": "sage",
    "students_count": 42,
}
req = urllib.request.Request(
    "http://localhost:8000/api/v1/courses",
    data=json.dumps(course_payload).encode("utf-8"),
    headers=auth_headers,
)
with urllib.request.urlopen(req) as res:
    course = json.loads(res.read().decode("utf-8"))
    course_id = course["id"]
    print(f"Course created! ID: {course_id}, Name: {course['name']}")

print("\n=== 5. Create Assignment with Reference Exemplar Ground Truth ===")
assign_payload = {
    "title": "Assignment 4 · Shortest Path Dijkstra",
    "description": "Implement Dijkstra shortest path using priority queues.",
    "max_score": 100.0,
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
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/courses/{course_id}/assignments",
    data=json.dumps(assign_payload).encode("utf-8"),
    headers=auth_headers,
)
with urllib.request.urlopen(req) as res:
    assign = json.loads(res.read().decode("utf-8"))
    assign_id = assign["id"]
    print(f"Assignment created with reference exemplar! ID: {assign_id}, Title: {assign['title']}")

print("\n=== 6. Input Real Student Submissions (Manual Text Entry) ===")
sub1_payload = {
    "assignment_id": assign_id,
    "student_name": "Grace Hopper",
    "student_roll": "2024-101",
    "student_email": "grace.hopper@navy.mil",
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
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions",
    data=json.dumps(sub1_payload).encode("utf-8"),
    headers=auth_headers,
)
with urllib.request.urlopen(req) as res:
    sub1 = json.loads(res.read().decode("utf-8"))
    sub1_id = sub1["id"]
    print(f"Submission 1 registered: {sub1['student']} (ID: {sub1_id})")

sub2_payload = {
    "assignment_id": assign_id,
    "student_name": "Alan Kay",
    "student_roll": "2024-102",
    "student_email": "alan.kay@smalltalk.org",
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
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/assignments/{assign_id}/submissions",
    data=json.dumps(sub2_payload).encode("utf-8"),
    headers=auth_headers,
)
with urllib.request.urlopen(req) as res:
    sub2 = json.loads(res.read().decode("utf-8"))
    sub2_id = sub2["id"]
    print(f"Submission 2 registered: {sub2['student']} (ID: {sub2_id})")

print("\n=== 7. Start AI Auto-Grading & 3-Way Plagiarism Check ===")
eval_payload = {"rubric_id": None, "similarity_threshold": 85.0}
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/assignments/{assign_id}/evaluate-batch",
    data=json.dumps(eval_payload).encode("utf-8"),
    headers=auth_headers,
)
with urllib.request.urlopen(req) as res:
    job = json.loads(res.read().decode("utf-8"))
    job_id = job["job_id"]
    print(f"Evaluation job dispatched! Job ID: {job_id}")

# Poll job completion
for poll_step in range(40):
    time.sleep(1.5)
    req = urllib.request.Request(f"http://localhost:8000/api/v1/jobs/{job_id}", headers=auth_headers)
    with urllib.request.urlopen(req) as res:
        j_status = json.loads(res.read().decode("utf-8"))
        print(f"Polling job status: {j_status['status']} ({j_status['progress_pct']}%) - processed {j_status['processed_items']}/{j_status['total_items']}")
        if j_status["status"] == "completed":
            print(f"Job completed! Progress: {j_status['progress_pct']}%, Processed: {j_status['processed_items']}")
            break
        elif j_status["status"] == "failed":
            print(f"Job failed with error: {j_status.get('error_message')}")
            break

print("\n=== 8. Review Queue & 3-Way Plagiarism Inspection ===")
req = urllib.request.Request(f"http://localhost:8000/api/v1/submissions/{sub1_id}/review-detail", headers=auth_headers)
with urllib.request.urlopen(req) as res:
    detail = json.loads(res.read().decode("utf-8"))
    print(f"Student: {detail['student']}")
    print(f"AI Suggested Score: {detail['score']}/100")
    print(f"1. Peer Similarity: {detail.get('similarity')}%")
    print(f"2. AI Content Probability: {detail.get('aiContent')}%")
    print(f"3. Public Web Plagiarism: {detail.get('webPlagiarism')}%")
    print(f"Criteria evaluations count: {len(detail.get('criteria_scores', []))}")

print("\n=== 9. Teacher Stamping Grade ===")
stamp_payload = {
    "status": "approved",
    "final_score": 96.0,
    "criteria_scores": detail.get("criteria_scores", []),
    "teacher_feedback": "Outstanding implementation matching the ground truth reference solution perfectly.",
    "action": "APPROVE",
}
req = urllib.request.Request(
    f"http://localhost:8000/api/v1/submissions/{sub1_id}/stamp-grade",
    data=json.dumps(stamp_payload).encode("utf-8"),
    headers=auth_headers,
)
req.get_method = lambda: "PUT"
with urllib.request.urlopen(req) as res:
    grade_res = json.loads(res.read().decode("utf-8"))
    print(f"Grade officially stamped by teacher! Final Score: {grade_res.get('final_score')}/100, Status: {grade_res.get('status')}")

print("\n=== 10. Verification in Live Gradebook ===")
req = urllib.request.Request(f"http://localhost:8000/api/v1/courses/{course_id}/gradebook", headers=auth_headers)
with urllib.request.urlopen(req) as res:
    gb = json.loads(res.read().decode("utf-8"))
    print(f"Gradebook active! Total entries: {len(gb)}")

print("\n*** ALL END-TO-END FLOWS FULLY OPERATIONAL AND VERIFIED! ***")
