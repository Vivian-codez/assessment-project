# Import module os
import os
# Import module sys
import sys
# Import load_dotenv from dotenv
from dotenv import load_dotenv
# Import genai from google
from google import genai

# Load environment variables from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
# Execute statement: load_dotenv(env_path)
load_dotenv(env_path)

# Set api_key to os.environ.get("GEMINI_API_KEY")
api_key = os.environ.get("GEMINI_API_KEY")
# Check if condition: not api_key
if not api_key:
    # Print console output: print("Error: GEMINI_API_KEY is not set in environment or backend/.env")
    print("Error: GEMINI_API_KEY is not set in environment or backend/.env")
    # Execute statement: sys.exit(1)
    sys.exit(1)

# Set client to genai.Client(
client = genai.Client(
    # Specify argument: api_key=api_key
    api_key=api_key,
)

# Set tools to [
tools = [
    # Execute statement: {
    {
        # Define field entry: 'type': 'google_search'
        'type': 'google_search',
    },
]

# Set generation_config to {
generation_config = {
    # Define field entry: 'max_output_tokens': 65536
    'max_output_tokens': 65536,
    # Define field entry: 'thinking_level': 'medium'
    'thinking_level': 'medium',
}

# Set sample_input to """
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

# Set input_data to sys.argv[1] if len(sys.argv) > 1 else sample_input
input_data = sys.argv[1] if len(sys.argv) > 1 else sample_input

# Begin try block to handle operations safely
try:
    # Set interaction to client.interactions.create(
    interaction = client.interactions.create(
        # Specify argument: model='models/gemini-3.8-flash'
        model='models/gemini-3.8-flash',
        # Specify argument: input=input_data
        input=input_data,
        # Execute statement: system_instruction="""You are an authoritative academic evaluator, automate
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
        # Specify argument: tools=tools
        tools=tools,
        # Specify argument: generation_config=generation_config
        generation_config=generation_config,
    )

    # Print console output: print("=== Interaction Evaluation Result ===")
    print("=== Interaction Evaluation Result ===")
    # Print console output: print(interaction.steps[-1])
    print(interaction.steps[-1])

# Handle exception during execution: except Exception as err
except Exception as err:
    # Print console output: print(f"Interaction error ({err}), falling back to standard generate_content...")
    print(f"Interaction error ({err}), falling back to standard generate_content...")
    # Fallback to model generation with search tools or direct evaluation
    response = client.models.generate_content(
        # Specify argument: model="gemini-flash-latest"
        model="gemini-flash-latest",
        # Specify argument: contents=input_data
        contents=input_data,
    )
    # Print console output: print("=== Model Generation Result ===")
    print("=== Model Generation Result ===")
    # Print console output: print(response.text)
    print(response.text)
