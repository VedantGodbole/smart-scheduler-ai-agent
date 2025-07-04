# src/llm/openai_client.py
import json
from typing import List, Dict, Optional
from openai import OpenAI
from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class OpenAIClient:
    def __init__(self):
        # Updated for latest OpenAI SDK (v1.50+)
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def get_completion(self, messages: List[Dict[str, str]], 
                      temperature: float = 0.7, 
                      max_tokens: int = 500) -> Optional[str]:
        """Get completion from OpenAI using latest SDK"""
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
        """Extract meeting information with advanced understanding"""
        
        system_prompt = """You are an expert meeting scheduling assistant with advanced natural language understanding. 
        Extract ALL relevant scheduling information from user input, including complex temporal relationships and constraints.

        Return a JSON object with this structure:
        {
            "duration_minutes": null or number,
            "preferred_days": [],
            "preferred_times": [],
            "constraints": [],
            "intent": "schedule|modify|cancel|clarify|change_requirements|select_slot",
            "needs_clarification": boolean,
            "clarification_question": "string or null",        
            "request_type": "simple|date_calculation|deadline_based|event_relative|requirement_change|slot_selection",
            "event_title": null or string,
            "specific_time": null or string (in "HH:MM" format),
            
            "temporal_relationships": {
                "type": null or "before_event|after_event|relative_date|deadline_based",
                "reference_event": "string description of referenced event",
                "time_buffer_minutes": number,
                "deadline": "deadline description"
            },
            "context_clues": {
                "meeting_type": "sync|standup|presentation|call|chat|usual|quick",
                "attendees_mentioned": boolean,
                "urgency": "low|medium|high",
                "flexibility": "rigid|flexible|very_flexible"
            },
            "modifications": {
                "previous_duration": null,
                "new_duration": null,
                "is_requirement_change": boolean
            },
            "needs_calendar_lookup": boolean
        }

        
        CRITICAL SLOT SELECTION RULES:
        If the user input matches ANY of these patterns, set request_type to "slot_selection" and intent to "select_slot":
        - Single words: "first", "second", "third", "fourth", "fifth"
        - Numbers: "1", "2", "3", "4", "5", "one", "two", "three", "four", "five"
        - Choice phrases: "first choice", "second option", "option one", "option 1"
        - Approval phrases: "first choice looks good", "the first one", "that works"
        - Simple confirmations when options were presented: "yes", "ok", "okay"

        EXAMPLES:
    
        Context: "Available slots shown"
        User: "first" → {"request_type": "slot_selection", "intent": "select_slot"}
        
        Context: "Available slots shown"  
        User: "first choice looks good" → {"request_type": "slot_selection", "intent": "select_slot"}
        
        Context: "Available slots shown"
        User: "2" → {"request_type": "slot_selection", "intent": "select_slot"}
        
        Context: "Available slots shown"
        User: "the second one" → {"request_type": "slot_selection", "intent": "select_slot"}

    
        CRITICAL: Set "request_type" correctly:
        - "date_calculation" for: "last weekday of month", "first monday of next month", "last friday", etc.
        - "deadline_based" for: "before my flight", "before I leave", etc.
        - "event_relative" for: "after my meeting", "before the presentation", etc.
        - "requirement_change" for: "actually", "change to", "make it longer", etc.
        - "simple" for: basic scheduling requests

        EXAMPLES for complex scenarios:
        Deadline-based:
        - "45 minutes before my flight on Friday at 6 PM" → 
          {"duration_minutes": 45, "temporal_relationships": {"type": "deadline_based", "reference_event": "flight on Friday at 6 PM", "deadline": "Friday 6 PM"}}

        Event-relative:
        - "quick chat a day or two after Project Alpha Kick-off" → 
          {"duration_minutes": 15, "temporal_relationships": {"type": "after_event", "reference_event": "Project Alpha Kick-off", "time_buffer_minutes": 1440}, "needs_calendar_lookup": true}

        Calculated dates:
        - "1-hour meeting for the last weekday of this month" → 
          {"duration_minutes": 60, "temporal_relationships": {"type": "relative_date", "reference_event": "last weekday of month"}}

        Requirement changes:
        - "Actually, my colleague needs to join, so we'll need a full hour" → 
          {"intent": "change_requirements", "modifications": {"new_duration": 60, "is_requirement_change": true}, "context_clues": {"attendees_mentioned": true}}

        Pattern recognition:
        - "quick" = 15 minutes, "chat" = 15 minutes, "sync" = 30 minutes, "usual" = needs lookup
        - "before my [event]" = deadline-based, "after my [event]" = sequential
        - "actually" or "wait" = modification intent"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context: {conversation_context}\nUser input: {user_input}"}
        ]
        
        response = self.get_completion(messages, temperature=0.3, max_tokens=600)
        
        try:
            result = json.loads(response) if response else {}
            # Ensure backward compatibility - fill in missing fields
            if 'temporal_relationships' not in result:
                result['temporal_relationships'] = {}
            if 'context_clues' not in result:
                result['context_clues'] = {}
            if 'modifications' not in result:
                result['modifications'] = {}
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response: {response}")
            return self._fallback_extraction(user_input)
    
    def generate_response(self, context: str, available_slots: List[str], 
                         user_input: str) -> str:
        """Generate sophisticated, contextual responses"""
        
        system_prompt = """You are a sophisticated AI scheduling assistant capable of handling complex, ambiguous, and changing requirements with human-like intelligence.

        CORE PRINCIPLES:
        1. **Context Awareness**: Remember and reference previous conversation elements naturally
        2. **Intelligent Clarification**: Ask smart, specific follow-up questions when needed  
        3. **Graceful Adaptation**: Handle requirement changes and conflicts smoothly
        4. **Proactive Problem-Solving**: Offer creative alternatives and solutions
        5. **Natural Conversation**: Sound human, not robotic - be warm and helpful

        RESPONSE STRATEGIES for complex scenarios:

        For Complex Temporal Requests:
        ✅ "I understand you need 45 minutes before your Friday 6 PM flight. I'm looking for slots that end by 5:15 PM to give you buffer time..."
        ✅ "Let me check your calendar for that Project Alpha event first, then find time 1-2 days after it..."

        For Requirement Changes:
        ✅ "No problem at all! Since your colleague is joining, I'll search for hour-long slots instead. Keeping your Tuesday morning preference..."
        ✅ "Got it - switching from 30 minutes to a full hour. Let me check if those same times can be extended..."

        For Ambiguous Requests:
        ✅ "For your usual sync-up, I see you typically do 30 minutes on Tuesdays. Should I look for that pattern?"
        ✅ "When you say 'not too early,' I'm thinking after 9 AM. Does that sound right?"

        For Calendar Dependencies:
        ✅ "I'll need to find your last meeting that day first, then look for evening slots with your decompression time..."
        ✅ "Let me search for that kick-off event, then I can suggest times 1-2 days after..."

        For Conflicts:
        ✅ "Tuesday morning is completely booked, but Tuesday afternoon has several openings. Would 2 PM or 4 PM work?"
        ✅ "No hour-long slots this week with those constraints, but I found some great options next Monday..."

        TONE: Professional but warm, confident but not presumptuous, helpful but not overwhelming.
        Sound like a capable human assistant, not a rigid bot."""
                
        slots_text = "\n".join(available_slots) if available_slots else "No slots currently available"
                
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
            Context: {context}
            Available slots: {slots_text}
            User input: {user_input}

            Generate an intelligent, contextual response:
            """}
        ]
        
        return self.get_completion(messages, max_tokens=400) or "I'm having trouble processing that. Could you please try again?"
    
    def _fallback_extraction(self, user_input: str) -> Dict:
        return {
            "duration_minutes": None,
            "preferred_days": [],
            "preferred_times": [],
            "constraints": [],
            "intent": "schedule",
            "needs_clarification": False,
            "temporal_relationships": {},
            "context_clues": {},
            "modifications": {}
        }
