from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class ConversationManager:
    def __init__(self):
        self.conversation_history: List[Dict] = []
        self.meeting_context = {
            'duration_minutes': None,
            'preferred_days': [],
            'preferred_times': [],
            'constraints': [],
            'confirmed_slot': None,
            'status': 'initial'  # initial, collecting_info, showing_options, confirming, completed
        }
        self.turn_count = 0
    
    def add_turn(self, user_input: str, agent_response: str, extracted_info: Dict = None):
        """Add a conversation turn"""
        self.turn_count += 1
        
        turn = {
            'turn': self.turn_count,
            'timestamp': datetime.now(),
            'user_input': user_input,
            'agent_response': agent_response,
            'extracted_info': extracted_info or {}
        }
        
        self.conversation_history.append(turn)
        
        # Update meeting context with extracted info
        if extracted_info:
            self._update_meeting_context(extracted_info)
        
        logger.info(f"Added conversation turn {self.turn_count}")
    
    def _update_meeting_context(self, extracted_info: Dict):
        """Update meeting context with new information"""
        if 'duration_minutes' in extracted_info and extracted_info['duration_minutes']:
            self.meeting_context['duration_minutes'] = extracted_info['duration_minutes']
        
        if 'preferred_days' in extracted_info:
            for day in extracted_info['preferred_days']:
                if day not in self.meeting_context['preferred_days']:
                    self.meeting_context['preferred_days'].append(day)
        
        if 'preferred_times' in extracted_info:
            for time in extracted_info['preferred_times']:
                if time not in self.meeting_context['preferred_times']:
                    self.meeting_context['preferred_times'].append(time)
        
        if 'constraints' in extracted_info:
            for constraint in extracted_info['constraints']:
                if constraint not in self.meeting_context['constraints']:
                    self.meeting_context['constraints'].append(constraint)
    
    def get_context_summary(self) -> str:
        """Get a summary of the current conversation context"""
        context_parts = []
        
        if self.meeting_context['duration_minutes']:
            context_parts.append(f"Duration: {self.meeting_context['duration_minutes']} minutes")
        
        if self.meeting_context['preferred_days']:
            context_parts.append(f"Preferred days: {', '.join(self.meeting_context['preferred_days'])}")
        
        if self.meeting_context['preferred_times']:
            context_parts.append(f"Preferred times: {', '.join(map(str, self.meeting_context['preferred_times']))}")
        
        if self.meeting_context['constraints']:
            context_parts.append(f"Constraints: {', '.join(map(str, self.meeting_context['constraints']))}")
        
        return " | ".join(context_parts) if context_parts else "No specific preferences set"
    
    def is_information_complete(self) -> bool:
        """Check if we have enough information to search for slots"""
        return self.meeting_context['duration_minutes'] is not None
    
    def get_missing_information(self) -> List[str]:
        """Get list of missing required information"""
        missing = []
        
        if not self.meeting_context['duration_minutes']:
            missing.append("meeting duration")
        
        return missing
    
    def should_ask_for_preferences(self) -> bool:
        """Check if we should ask for time/day preferences"""
        return (self.meeting_context['duration_minutes'] is not None and 
                not self.meeting_context['preferred_days'] and 
                not self.meeting_context['preferred_times'])
    
    def get_conversation_state(self) -> str:
        """Get current conversation state"""
        # Check for completed state first
        if self.meeting_context['confirmed_slot']:
            return "completed"
        elif not self.meeting_context['duration_minutes']:
            return "collecting_duration"
        elif self.should_ask_for_preferences():
            return "collecting_preferences"
        else:
            return "searching_slots"
    
    def set_target_date(self, target_date):
        """Set specific target date for scheduling"""
        self.meeting_context['target_date'] = target_date
        logger.info(f"Set target date: {target_date}")

    def reset_context(self):
        """Reset conversation context for new meeting"""
        self.meeting_context = {
            'duration_minutes': None,
            'preferred_days': [],
            'preferred_times': [],
            'constraints': [],
            'confirmed_slot': None,
            'status': 'initial',
            'target_date': None  # ADD this line
        }
        logger.info("Reset conversation context")
