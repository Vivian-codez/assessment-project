# AI Auto-Grading & Reference Benchmarking Engine

## 1. System Prompt & Evaluation Principles

Verism AI utilizes Google Gemini 2.5 Flash through the `google-genai` SDK to evaluate student submissions against educator rubrics and canonical reference solutions.

### Guiding Principles
1. **AI Suggests. You Stamp:** The AI generates `DraftGrade` suggestions. Final grades are stamped only when an authorized educator reviews and approves them.
2. **Pure-Python Arithmetic:** LLMs frequently produce arithmetic addition errors (e.g., $18 + 24 + 16 = 60$ instead of $58$). In Verism AI, the LLM evaluates *only individual rubric criteria*. Total points are summed exclusively using pure-Python IEEE-754 arithmetic:
   $$\text{Total Score} = \sum_{i=1}^{n} \text{clamp}(s_i, 0, \text{max\_points}_i)$$
   with exact 2-decimal floating point rounding.
3. **Reference Benchmarking:** When an instructor provides a canonical reference solution or starter code, student logic is directly compared against the benchmark to reward algorithmic elegance and flag structural regressions.

---

## 2. Structured JSON Output Schema

To eliminate parsing failures, the LLM is constrained to output strict JSON conforming to the following Pydantic schema:

```json
{
  "criteria_scores": [
    {
      "criterion_name": "Correctness & Algorithmic Logic",
      "score": 38.0,
      "max_points": 40.0,
      "explanation": "Passed 9/10 test cases. Fails on edge case with empty list input."
    },
    {
      "criterion_name": "Asymptotic Time Complexity",
      "score": 28.5,
      "max_points": 30.0,
      "explanation": "Achieves O(N log N) using divide-and-conquer, matching reference solution."
    },
    {
      "criterion_name": "Code Modularity & Readability",
      "score": 18.0,
      "max_points": 20.0,
      "explanation": "Clean helper functions and docstrings. Variable names are self-explanatory."
    },
    {
      "criterion_name": "Test Suite Coverage",
      "score": 9.0,
      "max_points": 10.0,
      "explanation": "Includes comprehensive unit tests covering boundary values."
    }
  ],
  "confidence_score": 0.94,
  "overall_feedback": "Strong submission demonstrating mastery of tree balancing. Pay attention to null pointer edge checks.",
  "strengths": [
    "Optimal asymptotic complexity",
    "Clean modular helper functions"
  ],
  "areas_for_improvement": [
    "Boundary value validation on empty tree root"
  ]
}
```

---

## 3. Spot-Check Calibration & Teacher Overrides

When an educator modifies a grade in the Review Queue:
1. The difference $\Delta = \text{Teacher Final Score} - \text{AI Suggested Score}$ is recorded in the `AuditLog`.
2. Model confidence is dynamically adjusted based on instructor alignment.
3. If an instructor frequently lowers points for a specific criterion, subsequent batch suggestions for that cohort incorporate the teacher's grading strictness delta.
