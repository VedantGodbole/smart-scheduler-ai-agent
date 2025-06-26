import time
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pytz

from src.llm.openai_client import OpenAIClient
from src.voice.speech_to_text import SpeechToText
from src.voice.text_to_speech import TextToSpeech
from src.calendar_integration.google_calendar import GoogleCalendarClient
from src.calendar_integration.calendar_utils import CalendarUtils
from src.agent.conversation_manager import ConversationManager
from src.utils.time_parser import TimeParser
from src.utils.logger import setup_logger
from config.settings import settings

logger = setup_logger(__name__)

class SmartScheduler:
    def __init__(self):
        self.llm_client = OpenAIClient()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.calendar = GoogleCalendarClient()
        self.conversation = ConversationManager()
        self.time_parser = TimeParser('UTC')
        
        # Conversation state
        self.is_running = False
        self.voice_mode = True
        
        # Timing settings for better user experience
        self.pause_after_agent_response = 3  # Seconds to pause after agent speaks
        self.pause_after_user_speaks = 1     # Seconds to pause after user speaks
        self.listening_timeout = 15.0          # Longer timeout for voice input
        
        logger.info("Smart Scheduler initialized")
    
    def start_conversation(self, voice_enabled: bool = True):
        """Start the scheduling conversation"""
        self.voice_mode = voice_enabled
        self.is_running = True
        
        # Check microphone availability for voice mode
        if self.voice_mode and not self.stt.is_microphone_available():
            logger.warning("Microphone not available, switching to text mode")
            self.voice_mode = False
        
        welcome_message = "Hello! I'm your Smart Scheduler. I can help you find and schedule a meeting. What would you like to schedule?"
        
        self._deliver_response(welcome_message)
        self._pause_for_user_processing()
        
        self.conversation_loop()
    
    def conversation_loop(self):
        """Main conversation loop with improved pacing"""
        while self.is_running:
            try:
                # Get user input with appropriate timeout
                user_input = self._get_user_input()
                if not user_input:
                    self._handle_no_input()
                    continue
                
                # Brief pause after user speaks (for natural flow)
                if self.voice_mode:
                    time.sleep(self.pause_after_user_speaks)
                
                # Check for exit commands
                if self._is_exit_command(user_input):
                    self._handle_exit()
                    break
                
                # Process the input and generate response
                response = self._process_user_input(user_input)
                
                # Deliver response with appropriate pacing
                self._deliver_response(response)
                
                # Check if conversation is complete
                if self.conversation.get_conversation_state() == "completed":
                    self._handle_completion()
                    break
                
                # Pause before next iteration to give user time to think
                self._pause_for_user_processing()
                
            except KeyboardInterrupt:
                self._handle_exit()
                break
            except Exception as e:
                logger.error(f"Error in conversation loop: {e}")
                error_msg = "I'm sorry, I encountered an error. Could you please try again?"
                self._deliver_response(error_msg)
                self._pause_for_user_processing()
    
    def _get_user_input(self) -> Optional[str]:
        """Get input from user (voice or text) with better prompting"""
        if self.voice_mode:
            print("\n🎤 I'm listening... (speak now)")
            user_input = self.stt.listen_and_transcribe(timeout=self.listening_timeout)
            if user_input:
                print(f"👤 You said: {user_input}")
            return user_input
        else:
            try:
                print()  # Add space for readability
                return input("👤 You: ").strip()
            except EOFError:
                return None
    
    def _deliver_response(self, response: str):
        """Deliver response to user with better formatting and pacing"""
        print(f"\n🤖 Agent: {response}")
        
        if self.voice_mode:
            # Wait a moment before speaking (so user can read)
            time.sleep(0.5)
            self.tts.speak(response, block=True)  # Wait for speech to complete
    
    def _pause_for_user_processing(self):
        """Add appropriate pause for user to process and respond"""
        if self.voice_mode:
            time.sleep(self.pause_after_agent_response)
    
    def _handle_no_input(self):
        """Handle cases where no input is received"""
        if self.voice_mode:
            print("🔇 I didn't hear anything. Let me try again...")
            time.sleep(1)
            # Try one more time with a prompt
            print("🎤 Please speak now...")
            user_input = self.stt.listen_and_transcribe(timeout=10.0)
            if user_input:
                print(f"👤 You said: {user_input}")
                return user_input
            else:
                self._deliver_response("I'm having trouble hearing you. Would you like to switch to text mode? You can type your response.")
                # Offer to switch to text mode
                backup_input = input("👤 Type your response (or press Enter to continue with voice): ").strip()
                if backup_input:
                    self.voice_mode = False
                    print("📝 Switched to text mode.")
                    return backup_input
        return None
    
    def _is_exit_command(self, user_input: str) -> bool:
        """Check if user wants to exit"""
        exit_phrases = ['exit', 'quit', 'goodbye', 'bye', 'stop', 'cancel', 'end']
        return any(phrase in user_input.lower() for phrase in exit_phrases)
    
    def _process_user_input(self, user_input: str) -> str:
        """Process user input and generate appropriate response"""
        try:
            # Show processing indicator for longer operations
            if self.voice_mode:
                print("🤔 Processing...")
            
            # Extract information from user input
            context = self.conversation.get_context_summary()
            extracted_info = self.llm_client.extract_meeting_info(user_input, context)
            
            # Parse time-related information
            duration = self.time_parser.parse_duration(user_input)
            if duration:
                extracted_info['duration_minutes'] = duration
            
            preferences = self.time_parser.parse_time_preference(user_input)
            if preferences['days']:
                extracted_info['preferred_days'] = preferences['days']
            if preferences['times']:
                extracted_info['preferred_times'] = preferences['times']
            if preferences['constraints']:
                extracted_info['constraints'] = preferences['constraints']
            
            # Handle different conversation states
            state = self.conversation.get_conversation_state()
            
            if state == "collecting_duration":
                response = self._handle_duration_collection(user_input, extracted_info)
            elif state == "collecting_preferences":
                response = self._handle_preferences_collection(user_input, extracted_info)
            elif state == "searching_slots":
                response = self._handle_slot_search(user_input, extracted_info)
            else:
                response = self._handle_general_input(user_input, extracted_info)
            
            # Add turn to conversation history
            self.conversation.add_turn(user_input, response, extracted_info)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return "I'm sorry, I had trouble understanding that. Could you please rephrase?"
    
    def _handle_duration_collection(self, user_input: str, extracted_info: Dict) -> str:
        """Handle collecting meeting duration"""
        if extracted_info.get('duration_minutes'):
            duration = extracted_info['duration_minutes']
            self.conversation.meeting_context['duration_minutes'] = duration
            
            if duration == 60:
                duration_text = "1 hour"
            elif duration < 60:
                duration_text = f"{duration} minutes"
            else:
                hours = duration // 60
                minutes = duration % 60
                duration_text = f"{hours} hour{'s' if hours > 1 else ''}"
                if minutes > 0:
                    duration_text += f" and {minutes} minutes"
            
            return f"Perfect! I'll look for a {duration_text} meeting slot. Do you have any preferred days or times? For example, you could say 'Tuesday afternoon' or 'weekday mornings'."
        else:
            return "I'd be happy to help you schedule a meeting. How long should the meeting be? You can say something like '1 hour' or '30 minutes'."
    
    def _handle_preferences_collection(self, user_input: str, extracted_info: Dict) -> str:
        """Handle collecting time preferences - FIXED"""
        
        # Parse time preferences using the enhanced parser
        preferences = self.time_parser.parse_time_preference(user_input)
        
        # Update meeting context with ALL preference types
        if preferences.get('days'):
            current_days = self.conversation.meeting_context.get('preferred_days', [])
            self.conversation.meeting_context['preferred_days'] = list(set(current_days + preferences['days']))
        
        if preferences.get('times'):
            current_times = self.conversation.meeting_context.get('preferred_times', [])
            self.conversation.meeting_context['preferred_times'] = list(set(current_times + preferences['times']))
        
        if preferences.get('constraints'):
            current_constraints = self.conversation.meeting_context.get('constraints', [])
            self.conversation.meeting_context['constraints'] = list(set(current_constraints + preferences['constraints']))
        
        # CRITICAL FIX: Store relative dates
        if preferences.get('relative_dates'):
            self.conversation.meeting_context['relative_dates'] = preferences['relative_dates']
        
        # Also update from extracted_info
        for key in ['preferred_days', 'preferred_times', 'constraints']:
            if key in extracted_info and extracted_info[key]:
                current_list = self.conversation.meeting_context.get(key, [])
                current_list.extend(extracted_info[key])
                self.conversation.meeting_context[key] = list(set(current_list))
        
        print(f"DEBUG: Updated meeting context: {self.conversation.meeting_context}")
        
        # Search for available slots
        return self._search_and_present_slots()
    
    def _handle_slot_search(self, user_input: str, extracted_info: Dict) -> str:
        """Handle slot selection or modification"""
        # Check if user is selecting a slot
        if any(word in user_input.lower() for word in ['first', 'second', 'third', '1', '2', '3', 'yes', 'that works']):
            return self._handle_slot_selection(user_input)
        
        # Check if user wants to modify search
        elif any(word in user_input.lower() for word in ['different', 'other', 'alternative', 'change']):
            return self._search_and_present_slots(suggest_alternatives=True)
        
        # Otherwise, treat as new preferences
        else:
            return self._handle_preferences_collection(user_input, extracted_info)
    
    def _handle_general_input(self, user_input: str, extracted_info: Dict) -> str:
        """Handle general conversation input"""
        # Check if this is an initial scheduling request
        if any(word in user_input.lower() for word in ['schedule', 'meeting', 'book', 'appointment']):
            if not extracted_info.get('duration_minutes'):
                return "I'd be happy to help you schedule a meeting. How long should the meeting be?"
            else:
                return self._handle_duration_collection(user_input, extracted_info)
        
        # Generate contextual response using LLM
        context = self.conversation.get_context_summary()
        return self.llm_client.generate_response(context, [], user_input)
    
    def _search_and_present_slots(self, suggest_alternatives: bool = False) -> str:
        """Search for available slots and present them to user - FIXED"""
        try:
            duration = self.conversation.meeting_context['duration_minutes']
            if not duration:
                return "I need to know the meeting duration first. How long should the meeting be?"
            
            # Show search indicator
            if self.voice_mode:
                print("🔍 Searching your calendar...")
                time.sleep(1)
            
            # FIXED: Better date range logic
            preferences = {
                'days': self.conversation.meeting_context.get('preferred_days', []),
                'times': self.conversation.meeting_context.get('preferred_times', []),
                'constraints': self.conversation.meeting_context.get('constraints', []),
                'relative_dates': self.conversation.meeting_context.get('relative_dates', [])
            }
            
            # Determine date range based on preferences
            if preferences.get('relative_dates'):
                # If they said "tomorrow", search only tomorrow
                start_date = datetime.now(pytz.UTC)
                for rd in preferences['relative_dates']:
                    if rd.get('target_date'):
                        target_date = rd['target_date']
                        start_date = datetime.combine(target_date, datetime.min.time())
                        start_date = pytz.UTC.localize(start_date)
                        end_date = start_date + timedelta(days=1)
                        break
                else:
                    # Default range
                    end_date = start_date + timedelta(days=14)
            else:
                # Default range
                start_date = datetime.now(pytz.UTC)
                end_date = start_date + timedelta(days=14)
            
            print(f"DEBUG: Searching from {start_date.date()} to {end_date.date()}")
            
            # Get available slots
            all_slots = self.calendar.find_free_slots(duration, start_date, end_date)
            
            if not all_slots:
                return "I'm sorry, I couldn't find any available slots in the specified time range. Would you like me to check a different time period?"
            
            print(f"DEBUG: Found {len(all_slots)} total slots")
            
            # Filter by preferences using the FIXED method
            filtered_slots = CalendarUtils.filter_slots_by_preferences(all_slots, preferences)
            
            if not filtered_slots:
                # Suggest alternatives
                if suggest_alternatives:
                    # Show some slots from the next day or different times
                    alternative_slots = all_slots[:5]  # Just show first 5 available
                    intro = "I couldn't find slots matching your exact preferences, but here are some alternatives:"
                else:
                    # First time, suggest nearby alternatives intelligently
                    tomorrow_date = (datetime.now() + timedelta(days=1)).date()
                    afternoon_slots = [s for s in all_slots if s['start'].date() == tomorrow_date and 12 <= s['start'].hour < 18]
                    
                    if afternoon_slots:
                        intro = "I couldn't find morning slots tomorrow, but I found these afternoon options:"
                        alternative_slots = afternoon_slots[:3]
                    else:
                        # Show next day options
                        next_day_slots = [s for s in all_slots if s['start'].date() > tomorrow_date]
                        intro = "Tomorrow morning is busy, but here are some options for the next few days:"
                        alternative_slots = next_day_slots[:5]
                
                if alternative_slots:
                    return self._format_slot_options(alternative_slots, intro)
                else:
                    return "I'm sorry, I couldn't find any suitable slots. Would you like to try different preferences?"
            
            return self._format_slot_options(filtered_slots[:5], "Great! I found these available times:")
            
        except Exception as e:
            logger.error(f"Error searching for slots: {e}")
            return "I'm having trouble accessing the calendar right now. Could you please try again in a moment?"

    
    def _format_slot_options(self, slots: List[Dict], intro: str) -> str:
        """Format available slots for presentation with better readability"""
        if not slots:
            return "No available slots found."
        
        response = intro + "\n\n"
        
        for i, slot in enumerate(slots[:5], 1):
            response += f"{i}. {slot['formatted_time']}\n"
        
        response += "\nWhich option works best for you? You can say the number (like 'one' or '1') or describe your choice (like 'the first one')."
        
        # Store slots for selection
        self.conversation.meeting_context['available_slots'] = slots[:5]
        
        return response.strip()
    
    def _handle_slot_selection(self, user_input: str) -> str:
        """Handle user selecting a time slot"""
        available_slots = self.conversation.meeting_context.get('available_slots', [])
        
        if not available_slots:
            return "I don't have any slots to choose from. Let me search again."
        
        # Parse selection
        selection_index = None
        user_lower = user_input.lower()
        
        # Check for number selection
        for i in range(1, len(available_slots) + 1):
            if str(i) in user_input or self._number_to_word(i) in user_lower:
                selection_index = i - 1
                break
        
        # Check for position words
        if 'first' in user_lower:
            selection_index = 0
        elif 'second' in user_lower:
            selection_index = 1
        elif 'third' in user_lower:
            selection_index = 2
        
        if selection_index is not None and 0 <= selection_index < len(available_slots):
            selected_slot = available_slots[selection_index]
            
            # Show booking indicator
            if self.voice_mode:
                print("📅 Creating calendar event...")
                time.sleep(1)
            
            # Create the calendar event
            event_title = f"Meeting ({self.conversation.meeting_context['duration_minutes']} min)"
            event_id = self.calendar.create_event(
                title=event_title,
                start_time=selected_slot['start'],
                end_time=selected_slot['end'],
                description="Scheduled via Smart Scheduler"
            )
            
            if event_id:
                self.conversation.meeting_context['confirmed_slot'] = selected_slot
                return f"Perfect! I've scheduled your meeting for {selected_slot['formatted_time']}. The meeting has been added to your calendar."
            else:
                return "I had trouble creating the calendar event. Would you like to try a different time slot?"
        else:
            return "I didn't understand which option you'd like. Could you please say the number (like '1' or 'first') or try again?"
    
    def _number_to_word(self, num: int) -> str:
        """Convert number to word"""
        words = {1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five'}
        return words.get(num, str(num))
    
    def _handle_completion(self):
        """Handle conversation completion"""
        completion_message = "Great! Your meeting has been scheduled successfully. Is there anything else you'd like to schedule?"
        self._deliver_response(completion_message)
        
        # Give extra time for user to think about this question
        if self.voice_mode:
            time.sleep(2)
        
        # Ask if user wants to schedule another meeting
        response = self._get_user_input()
        if response and any(word in response.lower() for word in ['yes', 'another', 'more', 'schedule']):
            self.conversation.reset_context()
            self._deliver_response("Sure! Let's schedule another meeting. How long should this one be?")
            self._pause_for_user_processing()
        else:
            self._handle_exit()
    
    def _handle_exit(self):
        """Handle conversation exit"""
        goodbye_message = "Thank you for using Smart Scheduler! Have a great day!"
        self._deliver_response(goodbye_message)
        self.is_running = False
        
    def test_mode(self):
        """Run in test mode without voice"""
        self.voice_mode = False
        print("Smart Scheduler Test Mode")
        print("Type 'exit' to quit")
        print("-" * 40)
        
        self.start_conversation(voice_enabled=False)
