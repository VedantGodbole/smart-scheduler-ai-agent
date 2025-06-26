import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
from datetime import datetime, timedelta
import pytz

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "test-key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest-key\n-----END PRIVATE KEY-----\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_end_to_end_scheduling_flow(self):
        """Test complete scheduling flow"""
        with patch('src.agent.smart_scheduler.OpenAIClient') as mock_llm, \
             patch('src.agent.smart_scheduler.GoogleCalendarClient') as mock_calendar, \
             patch('src.agent.smart_scheduler.SpeechToText') as mock_stt, \
             patch('src.agent.smart_scheduler.TextToSpeech') as mock_tts:
            
            # Set up mocks
            mock_llm_instance = Mock()
            mock_llm.return_value = mock_llm_instance
            
            mock_calendar_instance = Mock()
            mock_calendar.return_value = mock_calendar_instance
            
            mock_stt_instance = Mock()
            mock_stt.return_value = mock_stt_instance
            
            mock_tts_instance = Mock()
            mock_tts.return_value = mock_tts_instance
            
            # Configure mock responses
            mock_llm_instance.extract_meeting_info.return_value = {
                'duration_minutes': 60,
                'preferred_days': ['Tuesday'],
                'preferred_times': ['afternoon']
            }
            
            mock_calendar_instance.find_free_slots.return_value = [
                {
                    'start': datetime(2024, 6, 25, 14, 0, tzinfo=pytz.UTC),
                    'end': datetime(2024, 6, 25, 15, 0, tzinfo=pytz.UTC),
                    'formatted_time': 'Tuesday, June 25 from 2:00 PM to 3:00 PM'
                }
            ]
            
            mock_calendar_instance.create_event.return_value = 'event-123'
            
            # Import and test
            from src.agent.smart_scheduler import SmartScheduler
            
            scheduler = SmartScheduler()
            scheduler.voice_mode = False  # Use text mode for testing
            
            # Test duration collection
            response = scheduler._handle_duration_collection(
                "I need a 1 hour meeting", 
                {'duration_minutes': 60}
            )
            self.assertIn("1 hour", response)
            
            # Test slot search
            scheduler.conversation.meeting_context['duration_minutes'] = 60
            response = scheduler._search_and_present_slots()
            self.assertIn("available times", response.lower())
    
    def test_time_parsing_integration(self):
        """Test integration of time parsing components"""
        from src.utils.time_parser import TimeParser
        
        parser = TimeParser('UTC')
        
        # Test various duration formats
        test_cases = [
            ("1 hour meeting", 60),
            ("30 minute call", 30),
            ("2 hours session", 120),
            ("45 mins chat", 45)
        ]
        
        for text, expected_minutes in test_cases:
            result = parser.parse_duration(text)
            self.assertEqual(result, expected_minutes, f"Failed for: {text}")
    
    def test_calendar_integration_with_preferences(self):
        """Test calendar integration with user preferences"""
        with patch('src.calendar_integration.google_calendar.build'), \
             patch('src.calendar_integration.google_calendar.Credentials'):
            
            from src.calendar_integration.google_calendar import GoogleCalendarClient
            from src.calendar_integration.calendar_utils import CalendarUtils
            
            calendar = GoogleCalendarClient()
            calendar.service = Mock()
            
            # Mock calendar events
            calendar.get_events = Mock(return_value=[])
            
            # Test free slot finding
            start_date = datetime.now(pytz.UTC)
            end_date = start_date + timedelta(days=1)
            
            slots = calendar.find_free_slots(60, start_date, end_date)
            self.assertIsInstance(slots, list)
    
    def test_conversation_flow_with_mocked_components(self):
        """Test conversation flow with all components mocked"""
        with patch('src.agent.smart_scheduler.OpenAIClient'), \
             patch('src.agent.smart_scheduler.GoogleCalendarClient'), \
             patch('src.agent.smart_scheduler.SpeechToText'), \
             patch('src.agent.smart_scheduler.TextToSpeech'):
            
            from src.agent.conversation_manager import ConversationManager
            
            conversation = ConversationManager()
            
            # Simulate conversation flow
            conversation.add_turn(
                "I need a meeting",
                "How long should it be?",
                {}
            )
            
            conversation.add_turn(
                "1 hour",
                "When would you prefer?",
                {'duration_minutes': 60}
            )
            
            conversation.add_turn(
                "Tuesday afternoon",
                "I found some slots...",
                {'preferred_days': ['Tuesday'], 'preferred_times': ['afternoon']}
            )
            
            # Check conversation state progression
            self.assertEqual(conversation.turn_count, 3)
            self.assertEqual(conversation.meeting_context['duration_minutes'], 60)
            self.assertIn('Tuesday', conversation.meeting_context['preferred_days'])

if __name__ == '__main__':
    unittest.main()
