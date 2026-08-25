try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
import os
import json
import re

class ZEEAAIEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and GENAI_AVAILABLE:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            self.model = None

    async def build_paper_with_ai(self, question_bank: list) -> list:
        """
        Uses Gemini to filter and select questions strictly adhering to the ZEEA blueprint.
        """
        
        system_prompt = """
        You are the ZEEA Examination Paper Generation Engine.

        Your task is to generate a complete examination paper strictly according
        to the supplied examination blueprint.

        You MUST NOT invent questions.
        You MUST select questions only from the approved and active Question Bank provided.

        Every selected question must satisfy the required:
        - Subject
        - Chapter/topic coverage
        - Difficulty
        - Marks
        - Question type
        - Syllabus constraints

        EXAM BLUEPRINT:
        Total Questions: 180
        Total Marks: 720
        Marks per Question: 4

        PHYSICS:
        Easy: 15, Medium: 20, Hard: 10 (Total: 45)

        CHEMISTRY:
        Easy: 15, Medium: 20, Hard: 10 (Total: 45)

        BIOLOGY:
        Easy: 30, Medium: 40, Hard: 20 (Total: 90)

        DIFFICULTY TOTAL:
        Easy: 60, Medium: 80, Hard: 40

        VALIDATION RULES:
        1. Total questions must be exactly 180.
        2. Total marks must be exactly 720.
        3. Physics must contain exactly 45 questions.
        4. Chemistry must contain exactly 45 questions.
        5. Biology must contain exactly 90 questions.
        6. Difficulty distribution must exactly match the blueprint.
        7. Every question must have exactly four options.
        8. Every question must have exactly one valid correct answer.
        9. Do not select duplicate questions.
        10. Do not select questions marked DRAFT, UNDER_REVIEW or RETIRED.
        11. Do not modify the original question text.
        12. Do not modify the options or correct answer.
        13. Verify that every selected question belongs to the required syllabus.
        14. Check chapter/topic distribution against the chapter blueprint.
        15. Check that the exam does not contain excessive repetition of the same concept.
        16. Check that all required blueprint constraints are satisfied.
        17. Output the result STRICTLY as a JSON array of the selected Question IDs.
        Example output format: ["id_1", "id_2", "id_3", ...]
        """

        # Convert question bank to JSON string to feed to AI
        bank_json = json.dumps(question_bank)

        prompt = f"{system_prompt}\n\n=== QUESTION BANK STRICLY USE THIS ===\n{bank_json}\n\nReturn the JSON array of selected IDs now."

        if not os.getenv("GEMINI_API_KEY") or not GENAI_AVAILABLE or not self.model:
            # Fallback if no API key is provided: Return up to 180 logically (Mock AI behavior)
            print("WARNING: GEMINI_API_KEY missing or module unavailable. Using Mock AI Blueprint selection.")
            selected_ids = [q["id"] for q in question_bank[:180]]
            return selected_ids

        try:
            response = self.model.generate_content(prompt)
            # Extracted list of IDs from JSON
            selected_ids = json.loads(response.text)
            return selected_ids
        except Exception as e:
            print(f"AI Generation Failed: {e}")
            raise Exception("AI failed to generate paper based on blueprint")
