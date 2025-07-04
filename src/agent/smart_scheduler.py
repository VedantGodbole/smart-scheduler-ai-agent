import time
from typing import Optional, List, Dict
from datetime import datetime, timedelta
import pytz
import re

from src.llm.openai_client import OpenAIClient
# from src.voice.speech_to_text import SpeechToText
from src.voice.text_to_speech import TextToSpeech
from src.voice.deepgram_stt import DeepgramSTT
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
        # self.stt = SpeechToText()
        self.stt = DeepgramSTT()
        self.tts = TextToSpeech()
        self.calendar = GoogleCalendarClient()
        self.conversation = ConversationManager()
        self.time_parser = TimeParser('UTC')
        
        # Conversation state
        self.is_running = False
        self.voice_mode = True
        
        # Timing settings for better user experience
        self.pause_after_agent_response = 2  # Seconds to pause after agent speaks
        self.pause_after_user_speaks = 1     # Seconds to pause after user speaks
        self.listening_timeout = 35.0          # Longer timeout for voice input
        
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
    
    def schedule_meeting(self, summary, start_dt, duration_minutes, description=""):
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        event = create_event(summary, start_dt, end_dt, description)
        return f"✅ Event '{event.get('summary')}' scheduled at {event.get('start').get('dateTime')}"

    def upcoming_meetings(self, count=5):
        events = list_events(max_results=count)
        if not events:
            return "No upcoming events found."
        return "\n".join([f"{e['summary']} at {e['start']['dateTime']}" for e in events])


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
            time.sleep(1)
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
        """ENHANCED: Process user input with smart routing"""
        try:
            if self.voice_mode:
                print("🤔 Processing...")
            
            context = self.conversation.get_context_summary()
            extracted_info = self.llm_client.extract_meeting_info(user_input, context)
            
            print(f"DEBUG: Extracted info: {extracted_info}")
            
            # Route based on request type
            request_type = extracted_info.get('request_type', 'simple')
            intent = extracted_info.get('intent', '')
            print(f"DEBUG: Request type: {request_type}")
            print(f"DEBUG: Intent: {intent}")
            
            # Check conversation state
            state = self.conversation.get_conversation_state()
            print(f"DEBUG: Conversation state: {state}")
            
            if request_type == 'slot_selection' or intent == 'select_slot':
                print("DEBUG: Routing DIRECTLY to slot_selection")
                response = self._handle_slot_selection(user_input)
            elif request_type == 'requirement_change':
                print("DEBUG: Routing to requirement_change")
                response = self._handle_requirement_change(user_input, extracted_info)
            elif request_type == 'deadline_based':
                print("DEBUG: Routing to deadline_based")
                response = self._handle_deadline_request(user_input, extracted_info)
            elif request_type == 'date_calculation':
                print("DEBUG: Routing to date_calculation")
                response = self._handle_date_calculation(user_input, extracted_info)
            elif request_type == 'event_relative':
                print("DEBUG: Routing to event_relative")
                response = self._handle_event_relative(user_input, extracted_info)
            else:
                print("DEBUG: Routing to simple_request")
                response = self._handle_simple_request(user_input, extracted_info)
            
            # Add turn to conversation history
            self.conversation.add_turn(user_input, response, extracted_info)
            return response
            
        except Exception as e:
            logger.error(f"Error processing: {e}")
            import traceback
            traceback.print_exc()
            return "I'm sorry, I had trouble understanding that. Could you please rephrase?"

    def _handle_slot_search(self, user_input: str, extracted_info: Dict) -> str:
        """Handle slot selection or modification"""
        print(f"DEBUG: _handle_slot_search called with: {user_input}")
        
        user_lower = user_input.lower()
        
        pure_selection_patterns = [
            r'^(first|second|third|fourth|fifth)$',
            r'^[1-5]$',
            r'^(one|two|three|four|five)$',
            r'^(yes|ok|okay|that works|sounds good|perfect)$'
        ]

        # Exclude words that are part of scheduling requests
        scheduling_words = ['find', 'schedule', 'book', 'meeting', 'slot', 'time', 'tomorrow', 'morning', 'afternoon', 'evening']
        duration_words = ['min', 'minute', 'minutes', 'hour', 'hours']
        
        # Check if this is a pure selection (no scheduling or duration words)
        is_pure_selection = any(re.match(pattern, user_lower.strip()) for pattern in pure_selection_patterns)
        has_scheduling_words = any(word in user_lower for word in scheduling_words)
        has_duration_words = any(word in user_lower for word in duration_words)
        
        print(f"DEBUG: Is pure selection: {is_pure_selection}")
        print(f"DEBUG: Has scheduling words: {has_scheduling_words}")
        print(f"DEBUG: Has duration words: {has_duration_words}")
        
        # Only treat as slot selection if it's clearly a selection and no scheduling/duration context
        if is_pure_selection and not has_scheduling_words and not has_duration_words:
            print("DEBUG: Treating as slot selection")
            return self._handle_slot_selection(user_input)
        elif any(word in user_lower for word in ['different', 'other', 'alternative', 'change']):
            print("DEBUG: Detected search modification request")
            return self._search_and_present_slots(suggest_alternatives=True)
        else:
            # If they mention duration or scheduling, search for slots
            print("DEBUG: Treating as new search request")
            return self._search_and_present_slots()
                
    def _handle_simple_request(self, user_input: str, extracted_info: Dict) -> str:
        """Handle simple scheduling requests like 'tomorrow morning'"""
        print(f"DEBUG: _handle_simple_request called with: {user_input}")
        print(f"DEBUG: Extracted info: {extracted_info}")
        
        # Enhanced duration extraction
        duration = extracted_info.get('duration_minutes')
        if duration:
            self.conversation.meeting_context['duration_minutes'] = duration
            print(f"DEBUG: Set duration to {duration}")
        
        # Store event title
        event_title = extracted_info.get('event_title')
        if event_title:
            self.conversation.meeting_context['event_title'] = event_title
            print(f"DEBUG: Set event title to {event_title}")

        # Enhanced time parsing for "tomorrow"
        preferred_days = extracted_info.get('preferred_days', [])
        preferred_times = extracted_info.get('preferred_times', [])
        
        print(f"DEBUG: Preferred days: {preferred_days}")
        print(f"DEBUG: Preferred times: {preferred_times}")
        
        # Handle "tomorrow" properly
        if 'tomorrow' in preferred_days:
            tomorrow_date = (datetime.now() + timedelta(days=1)).date()
            self.conversation.meeting_context['target_date'] = tomorrow_date
            preferred_days.remove('tomorrow')
            print(f"DEBUG: Set target_date to {tomorrow_date}")
        
        # Update context
        if preferred_days:
            self.conversation.meeting_context['preferred_days'] = preferred_days
        if preferred_times:
            self.conversation.meeting_context['preferred_times'] = preferred_times
        
        # Existing state logic
        state = self.conversation.get_conversation_state()
        print(f"DEBUG: Conversation state in simple_request: {state}")
        
        if state == "collecting_duration":
            print("DEBUG: Going to duration_collection")
            return self._handle_duration_collection(user_input, extracted_info)
        elif state == "collecting_preferences":
            print("DEBUG: Going to preferences_collection")
            return self._handle_preferences_collection(user_input, extracted_info)
        elif state == "searching_slots":
            print("DEBUG: Going to slot_search")
            return self._handle_slot_search(user_input, extracted_info)
        else:
            print("DEBUG: Going to general_input")
            return self._handle_general_input(user_input, extracted_info)
    
    def _handle_requirement_change(self, user_input: str, extracted_info: Dict) -> str:
        """Handle 'Actually, need full hour' type changes"""
        modifications = extracted_info.get('modifications', {})
        
        if modifications.get('new_duration'):
            new_duration = modifications['new_duration']
            old_duration = self.conversation.meeting_context.get('duration_minutes')
            self.conversation.meeting_context['duration_minutes'] = new_duration
            
            return f"No problem! I'll search for {new_duration}-minute slots instead. Let me find what's available..."
        
        return "I understand you want to make a change. Could you clarify what you'd like to modify?"
    
    def _handle_deadline_request(self, user_input: str, extracted_info: Dict) -> str:
        """Handle 'before my flight Friday 6 PM' requests"""
        temporal = extracted_info.get('temporal_info', {})
        deadline = temporal.get('deadline', '')
        
        # Parse deadline (simplified for now)
        if 'friday' in deadline.lower() and '6 pm' in deadline.lower():
            # Calculate end time (Friday 6 PM minus buffer)
            next_friday = self._get_next_weekday('friday')
            deadline_time = datetime.combine(next_friday, datetime.min.time().replace(hour=18))
            search_end = deadline_time - timedelta(minutes=30)  # 30 min buffer
            
            duration = extracted_info.get('duration_minutes', 45)
            self.conversation.meeting_context['duration_minutes'] = duration
            
            # Search with deadline constraint
            slots = self.calendar.find_free_slots(duration, datetime.now(pytz.UTC), search_end)
            
            if slots:
                return self._format_slot_options(slots[:5], f"Perfect! Here are {duration}-minute slots that end before your Friday 6 PM flight:")
            else:
                return "I couldn't find any slots that end before your Friday flight. Would you like to try earlier in the week?"
        
        return "I understand you have a deadline, but I need more specific timing information. Could you clarify when exactly?"
    
    def _handle_date_calculation(self, user_input: str, extracted_info: Dict) -> str:
        """Handle 'last weekday of month' requests"""
        duration = extracted_info.get('duration_minutes', 60)
        self.conversation.meeting_context['duration_minutes'] = duration
        
        # Calculate last weekday
        last_day = self._calculate_last_weekday_of_month()
        
        # Store the calculated date
        self.conversation.meeting_context['target_date'] = last_day
        
        print(f"DEBUG: Calculated last weekday: {last_day}")

        return self._search_and_present_slots()
    
    def _handle_event_relative(self, user_input: str, extracted_info: Dict) -> str:
        """Handle 'after my Project Alpha meeting' requests"""
        temporal = extracted_info.get('temporal_info', {})
        reference_event = temporal.get('reference_event', '')
        
        # Extract search terms
        search_terms = self._extract_calendar_search_terms(reference_event)
        print(f"🔍 Looking for: {search_terms}")
        
        found_event = self.calendar.find_event_by_reference(search_terms)
        
        if found_event:
            return f"I found your {search_terms} event. Let me find available times after that..."
        else:
            return f"I couldn't find the '{search_terms}' event in your calendar. Could you check the name or try describing it differently?"
    
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
        """Handle collecting time preferences"""
        
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
        
        # Store relative dates
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

    def _handle_slot_selection(self, user_input: str) -> str:
        """Handle user selecting a time slot"""
        available_slots = self.conversation.meeting_context.get('available_slots', [])
        
        if not available_slots:
            # If no slots, search for them instead of saying we don't have any
            print("DEBUG: No slots available, searching...")
            
            # Check if we have enough info to search
            duration = self.conversation.meeting_context.get('duration_minutes')
            if duration:
                print(f"DEBUG: Have duration {duration}, searching for slots")
                return self._search_and_present_slots()
            else:
                print("DEBUG: No duration, asking for it")
                return "I need to know how long the meeting should be. How many minutes would you like?"
        
        # Parse selection (rest of existing logic)
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
            meeting_context = self.conversation.meeting_context
            event_title = meeting_context.get('event_title', f"Meeting ({meeting_context.get('duration_minutes', 30)} min)")
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
        """Search for available slots and present them to user"""
        try:
            duration = self.conversation.meeting_context['duration_minutes']
            if not duration:
                return "I need to know the meeting duration first. How long should the meeting be?"
            
            if self.voice_mode:
                print("🔍 Searching your calendar...")
                time.sleep(1)
            
            # Get preferences 
            preferences = {
                'days': self.conversation.meeting_context.get('preferred_days', []),
                'times': self.conversation.meeting_context.get('preferred_times', []),
                'constraints': self.conversation.meeting_context.get('constraints', []),
                'target_date': self.conversation.meeting_context.get('target_date')
            }
            
            # Determine date range
            if preferences.get('target_date'):
                target_date = preferences['target_date']
                start_date = datetime.combine(target_date, datetime.min.time())
                start_date = pytz.UTC.localize(start_date)
                end_date = start_date + timedelta(days=1)
                include_weekends = True
                
                preferred_times = preferences.get('times', [])
                if 'morning' in preferred_times:
                    working_hours = (9, 12)  # 9 AM to 12 PM for morning
                elif 'afternoon' in preferred_times:
                    working_hours = (12, 18)  # 12 PM to 6 PM for afternoon  
                elif 'evening' in preferred_times:
                    working_hours = (18, 22)  # 6 PM to 10 PM for evening
                else:
                    working_hours = (9, 22)  # Full day 9 AM to 10 PM

            else:   
                start_date = datetime.now(pytz.UTC)
                end_date = start_date + timedelta(days=14)
                include_weekends = False 
                working_hours = (9, 17)
            
            print(f"DEBUG: Searching from {start_date.date()} to {end_date.date()}")
            print(f"DEBUG: Include weekends: {include_weekends}")
            
            # Always call with include_weekends parameter
            all_slots = self.calendar.find_free_slots(
                duration, 
                start_date, 
                end_date, 
                working_hours=working_hours,  
                include_weekends=include_weekends
            )
            
            print(f"DEBUG: Found {len(all_slots)} total slots before filtering")
            
            filtered_slots = CalendarUtils.filter_slots_by_preferences(all_slots, preferences)
            
            print(f"DEBUG: Found {len(filtered_slots)} slots after filtering")
            
            if filtered_slots:
                return self._format_slot_options(filtered_slots[:5], "Great! I found these available times:")
            else:
                if all_slots:
                    return f"I found {len(all_slots)} available slots, but none match your preferences for {target_date.strftime('%A, %B %d') if preferences.get('target_date') else 'your selected timeframe'}. Would you like to see all available options or try different timing?"
                else:
                    return "I couldn't find any available slots in the specified timeframe. Would you like to try a different day or time?"
                
        except Exception as e:
            logger.error(f"Error searching for slots: {e}")
            import traceback
            traceback.print_exc()
            return "I'm having trouble accessing the calendar right now. Could you please try again in a moment?"
    
    def _format_slot_options(self, slots: List[Dict], intro: str) -> str:
        """Format available slots for presentation with better readability"""
        if not slots:
            return "No available slots found."
        
        response = intro + "\n\n"
        
        for i, slot in enumerate(slots[:5], 1):
            response += f"{i}. {slot['formatted_time']}\n"
        
        if self.voice_mode:
            response += "\nWhich option would you prefer? Just say the number, like 'two' or 'option three'."
        else:
            response += "\nWhich option works best for you? You can type the number (1, 2, 3...) or describe your choice."
        
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
    
    def _get_next_weekday(self, day_name: str) -> datetime.date:
        """Get next occurrence of weekday"""
        days = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
        target = days[day_name.lower()]
        current = datetime.now().weekday()
        days_ahead = target - current
        if days_ahead <= 0:
            days_ahead += 7
        return (datetime.now() + timedelta(days=days_ahead)).date()

    def _calculate_last_weekday_of_month(self) -> datetime.date:
        """Calculate last weekday of current month"""
        today = datetime.now().date()
        if today.month == 12:
            last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        while last_day.weekday() > 4:  # Go back to find weekday
            last_day -= timedelta(days=1)
        return last_day
    
    def _extract_calendar_search_terms(self, reference_event: str) -> str:
        """Extract search terms from event reference"""
        import re
        words = re.findall(r'\b\w+\b', reference_event.lower())
        important = [w for w in words if w not in ['my', 'the', 'a', 'meeting', 'event'] and len(w) > 2]
        return ' '.join(important[:2])
    
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
