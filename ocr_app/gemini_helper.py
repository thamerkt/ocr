import google.generativeai as genai
from django.conf import settings
import re
import json
from typing import Dict, Any

genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiProcessor:
    def __init__(self):
        # Use the correct model name for the latest API
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.system_prompt = """You are an advanced AI designed to extract structured data from identity documents.  
Given the detected text from an identity card, return a well-formatted JSON response with the following structure:

{
    "identity_card": {
        "country": "<Country Name>",
        "type": "<Type of Document>",
        "id_number": "<ID Number>",
        "last_name": "<Last Name>",
        "first_name": "<First Name>",
        "father_name": "<Full Father’s Name>",
        "date_of_birth": "<Date of Birth in YYYY-MM-DD format>",
        "place_of_birth": "<Place of Birth>",
        "issue_date": "<Date of Issue>",
        "expiry_date": "<Date of Expiry>",
        "face_detected": "<Yes/No>"
    }
}

### **Rules & Instructions:**
1. Extract and format dates in **YYYY-MM-DD** format.
2. Ensure all names are properly capitalized.
3. If any field is missing, set it to `null` instead of an empty string.
4. Return **only the JSON object** without extra text or explanations.
5. If the country is not detected, default to `"Unknown"`.

**Example Input (Detected Text from ID Card):**  
[
    "الجمهورية التونسية",
    "بطاقة التعريف الوطنية",
    "14006637",
    "اللقب بن حوا الة",
    "الاسم أحمد",
    "بن فتحى بن المبروك",
    "تاريخ الولادة 27 اوت 2001",
    "مؤتها جمال",
    "وجه مكتشف"
]

**Expected JSON Response:**  
{
    "identity_card": {
        "country": "Tunisian Republic",
        "type": "National Identity Card",
        "id_number": "14006637",
        "last_name": "Ben Hawa",
        "first_name": "Ahmed",
        "father_name": "Ben Fathi Ben Mabrouk",
        "date_of_birth": "2001-08-27",
        "place_of_birth": "Moutaa Jemal",
        "issue_date": null,
        "expiry_date": null,
        "face_detected": "Yes"
    }
}

### **Final Requirement:**  
- Do **not** return any additional explanations, comments, or extra text.  
- Output should be **valid JSON only**.
"""

    def extract_id_data(self, text: str) -> Dict[str, Any]:
        """
        Extract structured identity data from raw detected text using Gemini.
        """
        try:
            response = self.model.generate_content(
                contents=[{
                    'parts': [{
                        'text': f"{self.system_prompt}\nInput text: {text}"
                    }]
                }],
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 500,
                }
            )

            if not response.candidates:
                raise ValueError("No response generated")

            raw_text = response.candidates[0].content.parts[0].text
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON found in response: {raw_text}")

            return json.loads(json_match.group())

        except Exception as e:
            raise ValueError(f"Gemini processing failed: {str(e)}")

    def compare_input_with_profile(self, input_data: Dict[str, Any],profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare user input with fetched profile data using Gemini and return a similarity score with explanation.
        """
        
        try:
            prompt = f"""
You are a data validation assistant. Compare two user profile datasets and determine their similarity.

### Instructions:
- Analyze all fields for correctness (e.g., name, birthdate, ID number, etc.).
- Return a JSON with:
  - "similarity_score": number from 0 to 100.
  - "summary": short explanation of the differences or accuracy.

### Input Data:
{json.dumps(input_data, indent=2)}

### Profile Data:
{json.dumps(profile_data, indent=2)}

Return only a JSON object.
"""

            response = self.model.generate_content(
                contents=[{'parts': [{'text': prompt}]}],
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 300,
                }
            )

            if not response.candidates:
                raise ValueError("No response from Gemini")

            raw_text = response.candidates[0].content.parts[0].text
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not json_match:
                raise ValueError(f"No JSON found in Gemini response: {raw_text}")

            return json.loads(json_match.group())

        except Exception as e:
            raise ValueError(f"Gemini comparison failed: {str(e)}")
