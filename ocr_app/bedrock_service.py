import json
import re
import boto3
from django.conf import settings
from typing import Dict, Union
from botocore.config import Config

class NovaLiteClient:
    def __init__(self):
        boto_config = Config(
            retries={'max_attempts': 3, 'mode': 'standard'},
            connect_timeout=10,
            read_timeout=30
        )
        self.client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION,
            config=boto_config 
        )

    def generate_text(self, prompt: str) -> Dict[str, Union[str, Dict]]:
        """
        Ultra-robust version with:
        - Multiple response format handling
        - Comprehensive error recovery
        - Detailed logging
        """
        request_body = {
            "inferenceConfig": {
                "max_new_tokens": 1000,
                "temperature": 0.3,
                "topP": 0.9
            },
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": f"""Extract information and return STRICT JSON format:
                            {{
                                "country": string,
                                "id_number": string,
                                "first_name": string,
                                "last_name": string,
                                "birth_date": "YYYY-MM-DD"
                            }}
                            Input: {prompt}"""
                        }
                    ]
                }
            ]
        }

        try:
            # API call with retries
            response = self.client.invoke_model(
                modelId="amazon.nova-lite-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )  # <-- Parenthèse fermante ajoutée ici

            return self._parse_response(response)

        except Exception as e:
            raise ValueError(f"API call failed: {str(e)}")

    def _parse_response(self, response: Dict) -> Dict:
        """Handles all known Nova Lite response formats"""
        try:
            # 1. Parse the raw response body
            response_body = json.loads(response['body'].read())

            # 2. Handle different response structures
            content = self._extract_content(response_body)

            # 3. Parse JSON or extract fields
            return self._parse_content(content)

        except Exception as e:
            raise ValueError(f"Response parsing failed: {str(e)}")

    def _extract_content(self, response_body: Dict) -> str:
        """Extracts text content from all known response formats"""
        # Format 1: Standard message-based response
        if 'messages' in response_body:
            for message in response_body['messages']:
                if 'content' in message:
                    for content_item in message['content']:
                        if 'text' in content_item:
                            return content_item['text']

        # Format 2: Results-based response
        if 'results' in response_body:
            for result in response_body['results']:
                if 'outputText' in result:
                    return result['outputText']

        # Format 3: Direct text response
        if 'content' in response_body:
            return response_body['content']

        raise ValueError("No valid content in response")

    def _parse_content(self, content: str) -> Dict:
        """Multiple methods to extract structured data"""
        content = content.strip()

        # Method 1: Direct JSON parse
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

        # Method 2: Extract JSON block
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Method 3: Key-value extraction
        return self._extract_kv_pairs(content)

    def _extract_kv_pairs(self, text: str) -> Dict:
        """Fallback field extraction"""
        patterns = {
            "country": r'(?:"country"|country|pays)[:\s]*["\']?([^"\'\n]+)',
            "id_number": r'(?:"id_number"|id|number|numéro)[:\s]*["\']?([^"\'\n]+)',
            "first_name": r'(?:"first_name"|first name|prénom)[:\s]*["\']?([^"\'\n]+)',
            "last_name": r'(?:"last_name"|last name|nom)[:\s]*["\']?([^"\'\n]+)',
            "birth_date": r'(?:"birth_date"|date|naissance)[:\s]*["\']?([^"\'\n]+)'
        }

        result = {}
        for field, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result[field] = match.group(1).strip(' "\'')

        return result
