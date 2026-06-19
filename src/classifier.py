import json
import logging
from google import genai
from google.genai import types
from src import config

# Set up logger
logger = logging.getLogger(__name__)

class PersonaClassifier:
    """
    Classifies customer messages into target personas: Technical Expert,
    Frustrated User, or Business Executive, utilizing Gemini structured JSON outputs.
    """
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.CLASSIFIER_MODEL

    def classify(self, message: str) -> dict:
        """
        Classifies the incoming message content.
        
        Args:
            message: The string message sent by the user.
            
        Returns:
            A dictionary containing:
            - persona: 'Technical Expert', 'Frustrated User', or 'Business Executive'
            - confidence: Float value representing confidence
            - reasoning: String explanation of the classification
        """
        if not message.strip():
            return {
                "persona": "Business Executive",
                "confidence": 1.0,
                "reasoning": "Empty message default."
            }

        system_instruction = (
            "You are an advanced customer sentiment and language analysis engine. "
            "Your task is to analyze the vocabulary, tone, punctuation, and structural context "
            "of an incoming support message and classify it into exactly one of three customer personas:\n\n"
            "1. 'Technical Expert': Uses developer jargon, refers to APIs, error logs, configuration settings, "
            "endpoints, databases, or headers. Requests technical diagnostics.\n"
            "2. 'Frustrated User': Expresses emotional anger, complaints, writes in caps, uses exclamation marks, "
            "or uses phrases like 'nothing works', 'broken', 'immediate help', 'demand a refund'.\n"
            "3. 'Business Executive': Brief, concise, focused on operational impact, ROI, timelines, status reports, "
            "and business resolution. Skips technical configuration details.\n\n"
            "You must return a valid JSON object matching the defined schema."
        )

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "persona": {
                    "type": "STRING",
                    "enum": ["Technical Expert", "Frustrated User", "Business Executive"]
                },
                "confidence": {"type": "NUMBER"},
                "reasoning": {"type": "STRING"}
            },
            "required": ["persona", "confidence", "reasoning"]
        }

        try:
            from src.utils import call_with_backoff
            response = call_with_backoff(
                self.client.models.generate_content,
                model=self.model_name,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.1
                )
            )
            
            # Parse and return JSON response
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Error during persona classification: {e}")
            # Safe default fallback in case of errors
            return {
                "persona": "Frustrated User" if any(x in message.lower() for x in ["fail", "error", "broken", "angry"]) else "Technical Expert",
                "confidence": 0.5,
                "reasoning": f"Fallback classification triggered due to API error: {str(e)}"
            }
