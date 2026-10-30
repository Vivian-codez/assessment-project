"""
==============================================================================
Verism AI – Batch Submission ZIP Upload & Matching Test Flow
Tests in-memory ZIP generation with sample student submissions, endpoint
submission ingestion (/batch-upload), filename regex student matching,
and asynchronous Celery evaluation job status polling.
==============================================================================
"""

# Import in-memory byte buffer library for creating mock ZIP archives
import io
# Import time module for polling sleep intervals
import time
# Import zipfile module to programmatically construct ZIP packages
import zipfile
# Import FastAPI/Starlette test client to execute API requests in-memory
from fastapi.testclient import TestClient
# Import main FastAPI application instance from the backend
from app.main import app


def test_batch_upload():
    """Tests the complete end-to-end batch submission ZIP upload and job polling."""
    # Instantiate synchronous TestClient wrapping the FastAPI application
    with TestClient(app) as client:
        # Create an in-memory byte stream buffer to hold the ZIP archive data
        zip_buffer = io.BytesIO()
        # Open a new ZipFile object in write mode backed by the memory buffer
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            # Write a sample Python submission matching student roll 201 (Alice)
            zf.writestr("Roll_201_Alice.py", "def add(a, b):\n    return a + b\n")
            # Write a sample Python submission matching student roll 202 (Bob)
            zf.writestr("202_Bob.py", "def multiply(x, y):\n    return x * y\n")
            # Write a submission with unknown student roll 999 to test unmatched handling
            zf.writestr("999_Unknown.py", "def test():\n    pass\n")
        # Rewind the byte stream cursor back to the start of the buffer
        zip_buffer.seek(0)

        # Target classroom identifier used for the batch upload request
        classroom_id = "c1f5426e-2442-4905-aa1d-a8464afec398"
        # Target assignment identifier used for the batch upload request
        assignment_id = "a_demo_test"

        # Print progress indicator indicating upload request transmission
        print("--> Sending batch upload request...")
        # Send multipart/form-data POST request with the constructed submissions.zip
        response = client.post(
            f"/api/classrooms/{classroom_id}/assignments/{assignment_id}/batch-upload",
            files={"file": ("submissions.zip", zip_buffer.getvalue(), "application/zip")},
        )

        # Print the HTTP status code returned by the upload endpoint
        print("Upload Status Code:", response.status_code)
        # Assert that the batch upload was accepted with HTTP 202 Accepted
        assert response.status_code == 202, f"Expected 202, got {response.status_code}"
        
        # Parse the JSON response body payload
        data = response.json()
        # Print the asynchronous batch job tracking identifier
        print("Batch Job ID:", data.get("batch_job_id"))
        # Print the total count of files extracted from the archive
        print("Total Files:", data.get("total"))
        # Print the count of successfully matched student submissions queued for grading
        print("Queued Count:", len(data.get("queued_submissions", [])))
        # Print the count of unmatched files requiring manual teacher resolution
        print("Unmatched Count:", len(data.get("unmatched_submissions", [])))

        # Iterate through all queued student submissions
        for q in data.get("queued_submissions", []):
            # Print queued item details including filename, student name, and roll number
            print(f"  [QUEUED] {q.get('file_name')} -> {q.get('student_name')} (ID: {q.get('student_id')}, Roll: {q.get('roll_number')})")

        # Iterate through all unmatched submissions
        for u in data.get("unmatched_submissions", []):
            # Print unmatched item details for teacher review
            print(f"  [UNMATCHED] {u.get('file_name')} -> {u.get('student_name')} (Roll: {u.get('roll_number')})")

        # Extract the batch job ID to poll asynchronous worker progress
        job_id = data.get("batch_job_id")
        # Check if a valid job ID was returned
        if job_id:
            # Print header for polling section
            print("\n--> Polling job status...")
            # Poll status endpoint up to 5 times
            for i in range(5):
                # Send HTTP GET request to check background Celery job progress
                status_res = client.get(f"/api/jobs/{job_id}/status")
                # Print current poll index and status payload
                print(f"Poll #{i+1} Status Code: {status_res.status_code}, Body: {status_res.json()}")
                # Break early if background worker has finished processing
                if status_res.json().get("status") in ("SUCCESS", "completed"):
                    # Exit polling loop
                    break
                # Pause 1 second between polling requests
                time.sleep(1)


# Main entry point guard to run the test when executed directly
if __name__ == "__main__":
    # Execute the batch upload test function
    test_batch_upload()
