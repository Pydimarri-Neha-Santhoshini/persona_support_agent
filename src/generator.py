import logging
from google import genai
from google.genai import types
from src import config

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """
    Generates persona-adaptive customer support responses grounded strictly
    in retrieved knowledge base context documents.
    """
    def __init__(self):
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.model_name = config.GENERATION_MODEL

    def generate_response(self, query: str, persona: str, context_chunks: list[dict]) -> str:
        """
        Generates a grounded response adapted to the user's detected persona.
        
        Args:
            query: The user's customer support question.
            persona: The detected persona ('Technical Expert', 'Frustrated User', 'Business Executive').
            context_chunks: List of retrieved context dictionaries containing 'text', 'source', 'page', 'score'.
            
        Returns:
            The generated response string.
        """
        # If no context chunks are retrieved, immediately return the required default message.
        if not context_chunks:
            return "I could not find sufficient information in the knowledge base."

        # Format context text for prompt grounding
        formatted_context = ""
        for idx, chunk in enumerate(context_chunks):
            formatted_context += f"--- DOCUMENT CHUNK {idx+1} (Source: {chunk['source']}, Page: {chunk['page']}) ---\n"
            formatted_context += f"{chunk['text']}\n\n"

        # Base grounding rules enforced for all models
        base_grounding_rules = (
            "CRITICAL RESPONSE RULE:\n"
            "- You must generate your response based ONLY on the provided FACTUAL CONTEXT DOCUMENTS below.\n"
            "- Do not assume, infer, or hallucinate information that is not explicitly stated in the context.\n"
            "- If the context documents do not contain the answer or details required to address the user query, "
            "you must respond EXACTLY with the text: 'I could not find sufficient information in the knowledge base.'\n"
            "- Do not refer to the context documents, 'chunks', 'document 1', or 'sources' directly in your response to the user. "
            "Simply present the facts as your direct answer.\n\n"
        )

        # Style guidelines depending on the classified customer persona
        if persona == "Technical Expert":
            style_instruction = (
                "YOUR PERSONA: Technical Expert\n"
                "STYLE INSTRUCTIONS:\n"
                "- Write in a highly detailed, professional, and engineering-centric tone.\n"
                "- Provide technical details, configuration parameters, code/command blocks, or root-cause explanations "
                "available in the context.\n"
                "- Present troubleshooting procedures as structured, sequential steps (1, 2, 3, etc.)."
            )
        elif persona == "Frustrated User":
            style_instruction = (
                "YOUR PERSONA: Empathetic Support Agent\n"
                "STYLE INSTRUCTIONS:\n"
                "- Write in a highly empathetic, warm, and reassuring tone.\n"
                "- Begin your response with a compassionate and sincere validation of their trouble (e.g., "
                "'I completely understand how frustrating it is when... and I want to assure you that I am here to help you get this resolved right away.').\n"
                "- Avoid complex technical jargon, console codes, or details that might confuse or stress the user further.\n"
                "- Present the troubleshooting actions as a simple, clear, and action-oriented bulleted list.\n"
                "- Emphasize that you are guiding them step-by-step."
            )
        else:  # Business Executive
            style_instruction = (
                "YOUR PERSONA: Client Relations Director\n"
                "STYLE INSTRUCTIONS:\n"
                "- Write in an extremely concise, professional, and outcome-oriented tone.\n"
                "- Focus on direct business impact, resolution guidance, and timelines for recovery.\n"
                "- Do not include developer jargon, long configuration logs, or granular troubleshooting commands.\n"
                "- Keep the response brief (aim for 2-4 sentences max)."
            )

        # Combine all parts into the system instruction prompt
        system_instruction = (
            f"{base_grounding_rules}"
            f"{style_instruction}\n\n"
            f"FACTUAL CONTEXT DOCUMENTS:\n{formatted_context}"
        )

        try:
            from src.utils import call_with_backoff
            response = call_with_backoff(
                self.client.models.generate_content,
                model=self.model_name,
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2  # Keep temperature low for deterministic grounding
                )
            )
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error during response generation: {e}")
            return "I apologize, but I encountered an issue generating a response. Please try again."
