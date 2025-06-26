import openai
from typing import List, Dict, Optional
from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class OpenAIClient:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI()
    
    def get_completion(self, messages: List[Dict[str, str]], 
                      temperature: float = 0.7, 
                      max_tokens: int = 300) -> Optional[str]:
        """Get completion from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    def extract_meeting_info(self, user_input: str, conversation_context: str) -> Dict:
        """Extract meeting information from user input - IMPROVED PROMPT"""
        system_prompt = """
        You are a meeting scheduling assistant. Extract relevant information from user input.
        Return a JSON object with the following structure:
        {
            "duration_minutes": null or number,
            "preferred_days": [],
            "preferred_times": [],
            "constraints": [],
            "intent": "schedule|modify|cancel|clarify",
            "needs_clarification": boolean,
            "clarification_question": "string or null"
        }
        
        IMPORTANT EXAMPLES:
        - "30-minute slot for tomorrow morning" -> {"duration_minutes": 30, "preferred_times": ["morning"]}
        - "1 hour meeting" -> {"duration_minutes": 60}
        - "Tuesday afternoon" -> {"preferred_days": ["Tuesday"], "preferred_times": ["afternoon"]}
        - "tomorrow morning" -> {"preferred_times": ["morning"]}
        - "not too early" -> {"constraints": ["not_early"]}
        - "quick meeting" -> {"duration_minutes": 15}
        
        Focus on:
        - Duration: convert "hour"->60, "minutes"->exact number, "quick"->15
        - Times: "morning", "afternoon", "evening"
        - Days: specific day names
        - Constraints: "not early", "not late", etc.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {conversation_context}\nUser input: {user_input}"}
        ]
        
        response = self.get_completion(messages, temperature=0.3)
        
        try:
            import json
            return json.loads(response) if response else {}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            return {}
        
    def generate_response(self, context: str, available_slots: List[str], 
                         user_input: str) -> str:
        """Generate conversational response"""
        system_prompt = """
        You are a friendly, efficient meeting scheduling assistant. 
        
        Guidelines:
        - Be conversational and natural
        - Ask for missing information politely
        - Present options clearly
        - Handle conflicts gracefully with alternatives
        - Keep responses concise but helpful
        - Show empathy when no slots are available
        """
        
        slots_text = "\n".join(available_slots) if available_slots else "No slots available"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
            Context: {context}
            Available slots: {slots_text}
            User said: {user_input}
            
            Generate an appropriate response.
            """}
        ]
        
        return self.get_completion(messages) or "I'm having trouble processing that. Could you please try again?"
