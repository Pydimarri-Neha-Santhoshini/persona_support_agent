import json
import logging
from google import genai
from google.genai import types
from src import config

logger = logging.getLogger(__name__)

class Escalator:
    """
    Evaluates customer conversation logs to determine if human escalation is required
    and generates structured handoff summaries.
    """
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.GENERATION_MODEL
        self.sensitive_keywords = config.SENSITIVE_KEYWORDS
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD
        self.frustration_limit = config.FRUSTRATION_LIMIT

    def should_escalate(self, query: str, context_chunks: list[dict], frustration_count: int) -> tuple[bool, str]:
        """
        Assesses escalation conditions.
        
        Args:
            query: The user's current query.
            context_chunks: List of retrieved context chunks.
            frustration_count: The count of consecutive turns the user has been frustrated.
            
        Returns:
            A tuple of (should_escalate_bool, reason_string).
        """
        # 1. Check for sensitive topics / keywords (case-insensitive with word boundaries)
        import re
        query_lower = query.lower()
        for keyword in self.sensitive_keywords:
            pattern = rf"\b{re.escape(keyword.lower())}\b"
            if re.search(pattern, query_lower):
                return True, f"Sensitive topic detected: '{keyword}'"

        # 2. Check for empty context
        if not context_chunks:
            return True, "No relevant documentation found in the knowledge base."

        # 3. Check for low similarity confidence
        best_score = max(chunk["score"] for chunk in context_chunks)
        if best_score < self.confidence_threshold:
            return True, f"Retrieval similarity score ({best_score:.4f}) is below the threshold ({self.confidence_threshold})."

        # 4. Check for persistent frustration
        if frustration_count >= self.frustration_limit:
            return True, f"User has been classified as frustrated for {frustration_count} consecutive turns."

        return False, ""

    def generate_handoff_summary(self, 
                                 query: str, 
                                 persona: str, 
                                 conversation_history: list[dict], 
                                 context_chunks: list[dict]) -> dict:
        """
        Generates a structured JSON summary using Gemini to aid human responders.
        
        Args:
            query: The user's latest query.
            persona: The current customer persona.
            conversation_history: List of past messages (format: [{"role": "user"/"assistant", "content": "..."}]).
            context_chunks: List of context chunks retrieved from the knowledge base.
            
        Returns:
            A dictionary matching the required structured handoff JSON schema.
        """
        # Collect sources used
        docs_used = list(set(chunk["source"] for chunk in context_chunks)) if context_chunks else []

        # Format history for prompt
        history_strings = []
        for turn in conversation_history:
            role = "Customer" if turn.get("role") == "user" else "AI Support Agent"
            history_strings.append(f"{role}: {turn.get('content', '')}")
        
        history_text = "\n".join(history_strings)

        system_instruction = (
            "You are a customer support operations supervisor. Your job is to compile a structured, "
            "professional handoff ticket summary for a human agent. Use the provided conversation logs "
            "and information to generate a clean JSON payload.\n\n"
            "Identify the customer's issue, what steps they have already attempted (or were advised to try "
            "based on the history), and provide a clear, actionable recommendation for the human agent."
        )

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "persona": {"type": "STRING"},
                "issue": {"type": "STRING"},
                "conversation_history": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "documents_used": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "attempted_steps": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "recommendation": {"type": "STRING"}
            },
            "required": ["persona", "issue", "conversation_history", "documents_used", "attempted_steps", "recommendation"]
        }

        prompt = (
            f"Current Message: {query}\n"
            f"Detected Persona: {persona}\n"
            f"Documents Used: {docs_used}\n\n"
            f"CONVERSATION HISTORY:\n{history_text}\n"
        )

        try:
            from src.utils import call_with_backoff
            response = call_with_backoff(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=0.1
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"Error generating handoff summary: {e}")
            # Fallback programmatically constructed summary in case of error
            attempted = []
            for item in history_strings:
                if "clear" in item.lower() or "cache" in item.lower():
                    attempted.append("Browser cache clear")
                if "reset" in item.lower() or "forgot" in item.lower():
                    attempted.append("Password reset request")
            
            if not attempted:
                attempted = ["No standard troubleshooting steps recorded."]

            return {
                "persona": persona,
                "issue": query[:100] + "...",
                "conversation_history": history_strings,
                "documents_used": docs_used,
                "attempted_steps": attempted,
                "recommendation": "Investigate transaction history or account logs manually. Contact user immediately."
            }
