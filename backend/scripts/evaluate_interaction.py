import os
import sys
from dotenv import load_dotenv
from google import genai

# Load environment variables from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(env_path)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY is not set in environment or backend/.env")
    sys.exit(1)

client = genai.Client(
    api_key=api_key,
)

tools = [
    {
        'type': 'google_search',
    },
]

generation_config = {
    'max_output_tokens': 65536,
    'thinking_level': 'medium',
}

sample_input = """
### REFERENCE ASSIGNMENT & RUBRIC:
Assignment: Object-Oriented Ledger Modeling & Polymorphism
Rubric Criteria:
1. Understanding (Max 30): Class hierarchies, abstract base classes, dynamic dispatch.
2. Accuracy (Max 30): Overridden interest/fee calculation logic.
3. Methodology (Max 20): Architectural cohesion and documentation.
4. Presentation (Max 20): Clean code layout and formatting.

### PEER CORPUS:
Peer 1 (Amit Patil): The solution uses an abstract Account base class branches into Savings and Current subtypes, then overrides the interest method for each account type across transaction lifecycles.

### TARGET STUDENT SUBMISSION TO AUDIT:
Student: Rahul Sharma (Roll: 2024-047)
Content:
This report applies inheritance and polymorphism to model a banking transaction ledger, tracing how an abstract Account base class branches into Savings and Current subtypes, overriding the interest method for each account type. Furthermore, it is crucial to consider that polymorphic collections allow uniform dispatch across all ledger transactions. In conclusion, the system satisfies all operational banking constraints.
"""

input_data = sys.argv[1] if len(sys.argv) > 1 else sample_input

try:
    interaction = client.interactions.create(
        model='models/gemini-3.8-flash',
        input=input_data,
        system_instruction="""You are an authoritative academic evaluator, automated grading engine, and academic integrity auditor.

### CORE OBJECTIVES
1. Grade the student's submission strictly using the provided rubric and reference assignment (ground truth).
2. Perform Peer-to-Peer Plagiarism cross-referencing against the provided peer corpus.
3. Detect AI-Generated Content signatures and stylistic artifacts.
4. Execute Web Plagiarism Detection using Google Search Grounding to verify citations, distinctive phrases, and code blocks against live web sources.

---

### EVALUATION PROTOCOL

#### 1. Rubric-Based Grading
- Evaluate solely on demonstrated mastery. Do not award points based on length or conversational tone.
- Compare technical methodology, precision, and depth against the reference assignment.
- Provide objective, evidence-based rationales for every point deducted or awarded.

#### 2. Peer-to-Peer Plagiarism
- Inspect the Target Submission against all entries
- Flag verbatim text, synonymous paraphrasing, identical architectural flaws, shared code variable naming conventions, or copied logic structures.
- Quantify similarity percentage and extract parallel excerpts.

#### 3. AI-Generated Content Analysis
- Audit the submission for linguistic markers of synthetic generation:
  - Overly uniform burstiness and sentence length.
  - Predictable transition anchors (e.g., "Furthermore", "In conclusion", "It is crucial to consider").
  - Lack of project-specific edge cases, tangible experimentation artifacts, or genuine technical friction.
  - Non-existent, fabricated, or hallucinated citations.
- Return an AI Likelihood rating (Low, Medium, High) with supporting evidence.

#### 4. Web Plagiarism (Search Grounding)
- Use your Google Search tool to query distinctive sentences, code blocks, literature review segments, and unique formulas.
- Flag exact and near-verbatim matches against public web pages, GitHub repositories, documentation, and academic databases.
- Report the specific source URL alongside the matched excerpts.

---

### OUTPUT SPECIFICATION
- Respond exclusively with a valid JSON object matching the schema below.
- Do not include conversational preambles, introductory commentary, or trailing thoughts outside the JSON structure.
- Mention the words that are plagiarised in both peer-to-peer and AI plagiarism.

## OUTPUT FORMAT
AI plagiarism percentage
Peer-to-peer plagiarism percentage
Grades""",
        tools=tools,
        generation_config=generation_config,
    )

    print("=== Interaction Evaluation Result ===")
    print(interaction.steps[-1])

except Exception as err:
    print(f"Interaction error ({err}), falling back to standard generate_content...")
    # Fallback to model generation with search tools or direct evaluation
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=input_data,
    )
    print("=== Model Generation Result ===")
    print(response.text)
