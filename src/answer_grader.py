"""
answer_grader.py

Handles the final evaluation by sending extracted text to the Gemini API.
--- MODIFIED ---
- The prompt now requests a new "detailed_breakdown" key in the JSON for a table.
- The prompt for the Markdown report is now focused only on the summary.
"""

import os
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import streamlit as st
import json
import re

def initialize_gemini(api_key):
    """Initializes and configures the Gemini client."""
    try:
        if not api_key:
            st.error("API Key is missing. Please add it on the 'Settings' page.")
            return False
        
        genai.configure(api_key=api_key)  # pyright: ignore[reportPrivateImportUsage]
        return True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {e}")
        return False

def parse_ai_response(raw_text: str) -> dict:
    """
    Parses the raw text output from the AI, separating the JSON
    analytics block from the markdown report.
    """
    analytics = {}
    report = "Error: Could not parse AI response."
    
    try:
        # Regex to find the JSON block
        json_match = re.search(r"```json\n({.*?})\n```", raw_text, re.DOTALL)
        
        if json_match:
            json_string = json_match.group(1)
            analytics = json.loads(json_string)
            # The report is everything *outside* the JSON block
            report = raw_text.replace(json_match.group(0), "").strip()
        else:
            # If no JSON block is found, assume the entire output is the report
            report = raw_text
            
    except json.JSONDecodeError:
        st.warning("Could not decode analytics JSON from response. Analytics may be unavailable.")
        report = raw_text # Still return the raw text as the report
    except Exception as e:
        st.error(f"Error parsing response: {e}")
        report = raw_text

    return {"report": report, "analytics": analytics}


# --- MODIFIED: Function now accepts 'api_key' ---
def grade_answers(question_text: str, key_text: str, student_text: str, rules: str, mode: str, diagram_count: int, api_key: str) -> dict:
    """
    Performs the final evaluation based on extracted text.
    """
    print("Starting final grading evaluation...")
    
    # Initialize the API client
    if not initialize_gemini(api_key):
        return {"report": "API Key configuration failed.", "analytics": {}}

    # Use the old model names compatible with your library (v0.8.5)
    GRADING_MODEL = genai.GenerativeModel("models/gemini-2.5-flash-preview-09-2025")  # pyright: ignore[reportPrivateImportUsage]
    
    GENERATION_CONFIG = genai.types.GenerationConfig(  # pyright: ignore[reportPrivateImportUsage]
        temperature=0.3,
    )

    SAFETY_SETTINGS = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    # --- Dynamic Grading Philosophy ---
    philosophy_text = ""
    if mode == "Lenient":
        philosophy_text = """
        - **Philosophy:** Be generous. Award partial credit for any reasonable attempt.
        - **Keywords:** If the student's answer shows they understand the core concept, award most of the marks, even if they miss specific keywords.
        - **Errors:** Be very tolerant of OCR errors, spelling mistakes, and different phrasing.
        - **Partials:** Grant credit for partially correct answers.
        """
    elif mode == "Strict":
        philosophy_text = """
        - **Philosophy:** Be precise. Adhere closely to the answer key for full credit.
        - **Keywords:** Award marks based on the presence of specific keywords from the answer key.
        - **Errors:** Full marks require all details. Incomplete or incorrect answers should receive reduced credit.
        - **Partials:** Award credit only for parts of the answer that are fully correct and complete.
        """
    else: # Moderate (Default)
        philosophy_text = """
        - **Philosophy:** Be balanced and fair. This is a standard university-level grading.
        - **Keywords:** The student must include the main keywords, but allow for some phrasing flexibility.
        - **Errors:** Tolerate minor spelling or OCR errors, but deduct for clear conceptual mistakes.
        - **Partials:** Grant partial credit where deserved, but do not be overly generous.
        """
    # --- END NEW LOGIC ---

    # --- MODIFIED: Prompt now includes the detailed philosophy ---
    prompt = f"""
        You are an expert teaching assistant. Your task is to grade a student's answer sheet.

        Here is the Question Paper:
        ---
        {question_text}
        ---

        Here is the official Answer Key:
        ---
        {key_text}
        ---

        Here is the Student's Handwritten Answer Sheet:
        ---
        {student_text}
        ---

        Here is an analysis from a separate diagram detection tool:
        - Potential diagrams found: {diagram_count}
        ---

        Here are the critical Scoring Rules & Question Structure:
        - {rules or "No specific rules provided. Assume all questions are mandatory and in order."}
        ---

        **CRITICAL GRADING PHILOSOPHY (MODE: {mode})**
        You MUST follow this philosophy while grading:
        {philosophy_text}
        ---

        **TASK:**
        Provide two things:
        1.  A structured JSON object with detailed analytics.
        2.  A comprehensive, student-facing evaluation report in Markdown.

        **JSON Analytics Format (Task 1):**
        Create a JSON object inside a ```json code block with this exact structure:
        {{
            "total_score": {{"awarded": <int>, "max": <int>, "percentage": <float>}},
            "section_wise": [
                {{"section": "<Section Name>", "awarded": <int>, "max": <int>, "percentage": <float>}}
            ],
            "question_wise": [
                {{"question": "<Q#>", "awarded": <int>, "max": <int>, "percentage": <float>}}
            ],
            "diagram_performance": {{"required_estimate": <int>, "found_estimate": <int>}},
            "detailed_breakdown": [
                {{"question": "<Q#>", "part": "<part>", "description": "<Key answer concept>", "feedback": "<Specific feedback on student's answer>", "marks_awarded": <int>, "max_marks": <int>}}
            ]
        }}
        - "required_estimate" is your best guess of required diagrams from the key.
        - "found_estimate" is your best guess of how many the student drew (using the {diagram_count} as a hint).
        - "detailed_breakdown" MUST contain one entry for each sub-part of each question the student attempted. "description" should be a 2-5 word summary of the answer key concept.

        **Markdown Report (Task 2):**
        After the JSON block, write the full, student-facing *feedback summary* in Markdown.
        - Provide a brief summary of the performance *based on the {mode} philosophy*.
        - Mention diagram performance, using the {diagram_count} count as a reference.
        - Conclude with a "Strengths" section (bullet points).
        - Conclude with an "Areas for Improvement" section (bullet points).
        - **DO NOT** include the overall score or the detailed table in this markdown report.

        Begin your response with the JSON block.
    """
    
    try:
        response = GRADING_MODEL.generate_content(
            prompt,
            generation_config=GENERATION_CONFIG, 
            safety_settings=SAFETY_SETTINGS
        )
        
        if response.parts:
            print("Grading successful.")
            # Parse the raw text to separate JSON and Markdown
            return parse_ai_response(response.text)
        else:
            reason = response.candidates[0].finish_reason if response.candidates else "Unknown"
            print(f"Grading failed. Finish Reason: {reason}")
            raise Exception(f"Grading failed. Reason: {reason}")
            
    except Exception as e:
        print(f"An error occurred during grading: {e}")
        st.error(f"Error (Grading): {e}")
        # Return error in the expected format
        return {"report": f"Error (Grading): {e}", "analytics": {}}