"""
agent_engine.py - Cognitive Diagnostic & Pedagogical Reasoning Engine
Powered by Google Gemini (with seamless local pedagogical fallback).
Transforms raw student doubts into structured master-class explanations,
diagnostic gap analyses, scaffolded practice challenges, and rubric feedback.
"""

import os
import json
import re
import uuid
from dotenv import load_dotenv
from knowledge_base import synthesize_fallback_explanation

# Load .env file from current directory or parent
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "Doubt_to_Learning", ".env"))

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class DoubtToLearningAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        self._init_gemini()

    def _init_gemini(self):
        if self.api_key and GENAI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.is_live = True
            except Exception as e:
                print(f"[AgentEngine] Gemini configuration warning: {e}")
                self.is_live = False
        else:
            self.is_live = False

    def set_api_key(self, key):
        self.api_key = key.strip()
        self._init_gemini()
        # Also persist to local .env
        try:
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={self.api_key}\n")
        except Exception as e:
            print(f"[AgentEngine] Could not write to .env: {e}")

    def test_connection(self, key=None):
        test_key = key.strip() if key else self.api_key
        if not test_key or not GENAI_AVAILABLE:
            return False, "Gemini SDK not available or API key empty."
        try:
            genai.configure(api_key=test_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content("Ping. Reply with 'Pong'.")
            if resp and resp.text:
                return True, "Successfully connected to Google Gemini!"
            return False, "No response received from Gemini."
        except Exception as e:
            return False, f"API test failed: {str(e)}"

    def analyze_doubt(self, subject, doubt_text, context_attempt="", learning_level="Intermediate (High School)"):
        """
        Ingests student doubt and returns complete cognitive diagnosis,
        prerequisite mapping, step-by-step breakdown, and scaffolded practice suite.
        """
        session_uuid = str(uuid.uuid4())

        # Attempt with Gemini if live
        if self.is_live:
            try:
                result = self._gemini_analyze(subject, doubt_text, context_attempt, learning_level)
                if result:
                    result["session_uuid"] = session_uuid
                    result["source"] = "gemini_live"
                    return result
            except Exception as e:
                print(f"[AgentEngine] Gemini live generation failed, switching to pedagogical engine: {e}")

        # Fallback to local pedagogical domain engine
        fallback_data = synthesize_fallback_explanation(subject, doubt_text, learning_level)
        fallback_data["session_uuid"] = session_uuid
        fallback_data["doubt_text"] = doubt_text
        fallback_data["context_attempt"] = context_attempt
        fallback_data["learning_level"] = learning_level
        fallback_data["source"] = "pedagogical_engine"
        return fallback_data

    def _gemini_analyze(self, subject, doubt_text, context_attempt, learning_level):
        """Calls Gemini with strict structured JSON output instructions."""
        prompt = f"""
You are the "Doubt-to-Learning Agent", an elite cognitive tutor and master pedagogue.
Your mission is to transform a student's academic doubt into a transformative, concept-mastery learning experience.

STUDENT PROFILE & CONTEXT:
- Subject: {subject}
- Academic Level: {learning_level}
- Student's Doubt: "{doubt_text}"
- Student's Prior Attempt or Context: "{context_attempt or 'None provided'}"

PEDAGOGICAL REQUIREMENTS:
1. Identify the EXACT core academic concept underpinning this doubt.
2. Diagnose the root learning gap or misconception (distinguish between procedural slips, terminology confusion, and conceptual prerequisite gaps).
3. List 2 to 3 prerequisite concepts needed to understand this.
4. Craft a vivid, intuitive real-world analogy (Mental Model) appropriate for their level ({learning_level}).
5. Provide a simple, step-by-step explanation (3 to 4 sequential steps). Use LaTeX ($...$ or $$...$$) for any mathematical equations or formulas, or code blocks for programming.
6. Highlight 2 "Common Pitfalls" (what mistakes do students almost always make on this exact concept?).
7. Generate 3 Scaffolded Practice Questions:
   - Tier 1 (Concept Check): Multiple choice question testing the core intuition.
   - Tier 2 (Application): Numerical, code, or short answer testing practical application.
   - Tier 3 (Mastery Scenario): Deep reasoning question testing transfer or edge cases.

OUTPUT FORMAT:
Respond with ONLY a valid, parseable JSON object matching this schema without markdown fences:
{{
  "subject": "{subject}",
  "diagnosed_concept": "String",
  "misconception_gap": "String",
  "prerequisites": ["Concept A", "Concept B"],
  "mental_model_analogy": "String",
  "explanation_steps": [
    {{
      "title": "Step 1: ...",
      "explanation": "Clear explanation with LaTeX math if needed",
      "formula": "LaTeX formula or key code takeaway"
    }}
  ],
  "common_pitfalls": [
    "Pitfall 1...",
    "Pitfall 2..."
  ],
  "practice_questions": [
    {{
      "question_tier": 1,
      "question_text": "...",
      "question_type": "mcq",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "explanation": "...",
      "hints": ["Hint 1...", "Hint 2..."]
    }},
    {{
      "question_tier": 2,
      "question_text": "...",
      "question_type": "open",
      "correct_answer": "...",
      "explanation": "...",
      "hints": ["Hint 1...", "Hint 2..."]
    }},
    {{
      "question_tier": 3,
      "question_text": "...",
      "question_type": "mcq",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option C",
      "explanation": "...",
      "hints": ["Hint 1...", "Hint 2..."]
    }}
  ]
}}
"""
        models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro"]
        response_text = ""
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                resp = model.generate_content(prompt)
                if resp and resp.text:
                    response_text = resp.text
                    break
            except Exception as me:
                continue

        if not response_text:
            return None

        # Clean JSON from backticks
        cleaned = re.sub(r"^```json\s*", "", response_text.strip())
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        data = json.loads(cleaned)
        data["doubt_text"] = doubt_text
        data["context_attempt"] = context_attempt
        data["learning_level"] = learning_level
        return data

    def evaluate_answer(self, question, student_answer):
        """
        Evaluates a student's answer using rubric standards.
        Returns score (0-100), mastery_level, is_correct, constructive feedback, and corrective tip.
        """
        if not student_answer or not str(student_answer).strip():
            return {
                "score": 0,
                "mastery_level": "Novice",
                "is_correct": False,
                "feedback": "No answer was provided. Please write down your thought process or select an option!",
                "corrective_tip": "Review the concept steps above before attempting this question."
            }

        q_type = question.get("question_type", "mcq")
        correct_ans = question.get("correct_answer", "").strip()
        explanation = question.get("explanation", "")

        # Quick exact match for MCQ
        if q_type == "mcq":
            clean_student = student_answer.strip().lower()
            clean_correct = correct_ans.strip().lower()
            if clean_student == clean_correct or (len(clean_student) > 5 and clean_student in clean_correct) or (len(clean_correct) > 5 and clean_correct in clean_student):
                return {
                    "score": 100,
                    "mastery_level": "Mastered",
                    "is_correct": True,
                    "feedback": f"Spot on! Your answer is completely correct. {explanation}",
                    "corrective_tip": "You demonstrated solid mastery of this core concept. Keep building on this momentum!"
                }

        # If live Gemini is active, use AI rubric evaluation
        if self.is_live:
            try:
                ai_eval = self._gemini_evaluate(question, student_answer)
                if ai_eval:
                    return ai_eval
            except Exception as e:
                print(f"[AgentEngine] Gemini evaluation failed, using rubric heuristics: {e}")

        # Rubric heuristics fallback
        return self._heuristic_evaluate(question, student_answer)

    def _gemini_evaluate(self, question, student_answer):
        prompt = f"""
You are an expert academic evaluator and encouraging mentor for a student.
Evaluate the student's submitted response against the question and target solution.

QUESTION DETAILS:
Question: {question.get('question_text')}
Type: {question.get('question_type')}
Expected Correct Answer: {question.get('correct_answer')}
Concept Explanation: {question.get('explanation')}

STUDENT'S SUBMISSION:
"{student_answer}"

EVALUATION CRITERIA:
1. Accuracy Score: 0 to 100 based on conceptual validity and reasoning.
2. Mastery Level: "Novice" (0-45), "Developing" (46-69), "Proficient" (70-89), or "Mastered" (90-100).
3. is_correct: true if score >= 70, false otherwise.
4. Feedback: Constructive, supportive, and specific. Acknowledge what the student got right, pinpoint exactly where the misunderstanding or calculation slip occurred, and explain why.
5. Corrective Tip: A concise, memorable 1-sentence tip to prevent this mistake in future tests.

OUTPUT FORMAT:
Respond ONLY with a JSON object:
{{
  "score": 85,
  "mastery_level": "Proficient",
  "is_correct": true,
  "feedback": "...",
  "corrective_tip": "..."
}}
"""
        models_to_try = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-pro"]
        for model_name in models_to_try:
            try:
                model = genai.GenerativeModel(model_name)
                resp = model.generate_content(prompt)
                if resp and resp.text:
                    cleaned = re.sub(r"^```json\s*", "", resp.text.strip())
                    cleaned = re.sub(r"^```\s*", "", cleaned)
                    cleaned = re.sub(r"\s*```$", "", cleaned)
                    return json.loads(cleaned)
            except Exception:
                continue
        return None

    def _heuristic_evaluate(self, question, student_answer):
        q_type = question.get("question_type", "mcq")
        correct_ans = question.get("correct_answer", "")
        explanation = question.get("explanation", "")

        stud_lower = str(student_answer).strip().lower()
        corr_lower = str(correct_ans).strip().lower()

        if q_type == "mcq":
            # Direct or fuzzy match
            if stud_lower == corr_lower or stud_lower in corr_lower:
                score = 100
                level = "Mastered"
                correct = True
                feedback = f"Great work! Your choice is correct. {explanation}"
                tip = "You have identified the key distinction in this question."
            else:
                score = 25
                level = "Novice"
                correct = False
                feedback = f"Not quite. The correct answer is '{correct_ans}'. Here is why: {explanation}"
                tip = "Take a moment to re-read the explanation above and review the underlying definition."
        else:
            # Open ended evaluation heuristic
            keywords = [w for w in corr_lower.replace(",", "").replace(".", "").split() if len(w) > 3]
            match_count = sum(1 for kw in keywords if kw in stud_lower)
            match_ratio = match_count / max(1, len(keywords))

            if match_ratio >= 0.6:
                score = 90
                level = "Mastered"
                correct = True
                feedback = f"Outstanding explanation! You clearly hit the key conceptual points. {explanation}"
                tip = "Excellent conceptual clarity. Practice applying this to multi-step exam questions."
            elif match_ratio >= 0.3 or len(stud_lower) > 30:
                score = 65
                level = "Developing"
                correct = False
                feedback = f"Good initial effort! You captured part of the mechanism, but missed key terms or formal relationships. Note that: {explanation}"
                tip = "Focus on clearly linking cause and effect when explaining scientific concepts."
            else:
                score = 35
                level = "Novice"
                correct = False
                feedback = f"Your answer is incomplete or addresses a different point. The key expected insight is: {explanation}"
                tip = "Use the progressive hints provided for this question to guide your reasoning."

        return {
            "score": score,
            "mastery_level": level,
            "is_correct": correct,
            "feedback": feedback,
            "corrective_tip": tip
        }


# Global Singleton Agent Instance
doubt_agent = DoubtToLearningAgent()
