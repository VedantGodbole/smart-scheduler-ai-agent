#!/usr/bin/env python3
"""
Smart Scheduler AI Agent
Main entry point for the application
"""

import sys
import argparse
from config.settings import settings
from src.agent.smart_scheduler import SmartScheduler
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Smart Scheduler AI Agent')
    parser.add_argument('--test', action='store_true', help='Run in test mode (text only)')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice mode')
    
    args = parser.parse_args()
    
    try:
        # Validate settings
        settings.validate()
        
        # Initialize the Smart Scheduler
        scheduler = SmartScheduler()
        
        if args.test:
            # Run in test mode
            scheduler.test_mode()
        else:
            # Run in normal mode
            voice_enabled = not args.no_voice
            print(f"Starting Smart Scheduler...")
            print(f"Voice mode: {'Enabled' if voice_enabled else 'Disabled'}")
            print("Say 'exit' or 'quit' to end the conversation")
            print("-" * 50)
            
            scheduler.start_conversation(voice_enabled=voice_enabled)
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
    
    def extract_meeting_info(self, user_input: str, conversation_context: str) -> Dict:
        """Extract meeting information from user input"""
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
        
        Examples:
        - "1 hour meeting" -> {"duration_minutes": 60}
        - "Tuesday afternoon" -> {"preferred_days": ["Tuesday"], "preferred_times": ["afternoon"]}
        - "not too early" -> {"constraints": ["not_early"]}
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
