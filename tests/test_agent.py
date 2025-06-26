import unittest
from unittest.mock import Mock, patch, MagicMock
from src.agent.smart_scheduler import SmartScheduler
from src.agent.conversation_manager import ConversationManager

class TestConversationManager(unittest.TestCase):
    def setUp(self):
        self.conversation = ConversationManager()
    
    def test_add_turn(self):
        """Test adding conversation turns"""
        user_input = "I need a 1 hour meeting"
        agent_response = "Sure! When would you like to schedule it?"
        extracted_info = {'duration_minutes': 60}
        
        self.conversation.add_turn(user_input, agent_response, extracted_info)
        
        self.assertEqual(self.conversation.turn_count, 1)
        self.assertEqual(len(self.conversation.conversation_history), 1)
        self.assertEqual(self.conversation.meeting_context['duration_minutes'], 60)
    
    def test_context_summary(self):
        """Test context summary generation"""
        self.conversation.meeting_context['duration_minutes'] = 60
        self.conversation.meeting_context['preferred_days'] = ['Tuesday']
        
        summary = self.conversation.get_context_summary()
        self.assertIn("Duration: 60 minutes", summary)
        self.assertIn("Preferred days: Tuesday", summary)
    
    def test_information_completeness(self):
        """Test checking if information is complete"""
        # Initially incomplete
        self.assertFalse(self.conversation.is_information_complete())
        
        # Complete after setting duration
        self.conversation.meeting_context['duration_minutes'] = 60
        self.assertTrue(self.conversation.is_information_complete())
    
    def test_missing_information(self):
        """Test identifying missing information"""
        missing = self.conversation.get_missing_information()
        self.assertIn("meeting duration", missing)
        
        self.conversation.meeting_context['duration_minutes'] = 60
        missing = self.conversation.get_missing_information()
        self.assertEqual(len(missing), 0)
    
    def test_conversation_states(self):
        """Test conversation state transitions"""
        # Initial state
        self.assertEqual(self.conversation.get_conversation_state(), "collecting_duration")
        
        # After setting duration
        self.conversation.meeting_context['duration_minutes'] = 60
        self.assertEqual(self.conversation.get_conversation_state(), "collecting_preferences")
        
        # After confirming slot
        self.conversation.meeting_context['confirmed_slot'] = {'start': 'mock_time'}
        self.assertEqual(self.conversation.get_conversation_state(), "completed")

class TestSmartScheduler(unittest.TestCase):
    def setUp(self):
        with patch('src.agent.smart_scheduler.OpenAIClient'), \
             patch('src.agent.smart_scheduler.SpeechToText'), \
             patch('src.agent.smart_scheduler.TextToSpeech'), \
             patch('src.agent.smart_scheduler.GoogleCalendarClient'):
            self.scheduler = SmartScheduler()
    
    def test_exit_command_detection(self):
        """Test exit command detection"""
        self.assertTrue(self.scheduler._is_exit_command("exit"))
        self.assertTrue(self.scheduler._is_exit_command("I want to quit"))
        self.assertTrue(self.scheduler._is_exit_command("goodbye"))
        self.assertFalse(self.scheduler._is_exit_command("I need a meeting"))
    
    def test_number_to_word_conversion(self):
        """Test number to word conversion"""
        self.assertEqual(self.scheduler._number_to_word(1), "one")
        self.assertEqual(self.scheduler._number_to_word(2), "two")
        self.assertEqual(self.scheduler._number_to_word(3), "three")
    
    @patch('src.agent.smart_scheduler.SmartScheduler._get_user_input')
    def test_conversation_loop_exit(self, mock_input):
        """Test conversation loop with exit command"""
        mock_input.return_value = "exit"
        
        # Set is_running to True so the loop actually runs
        self.scheduler.is_running = True
        
        # Mock _deliver_response on the instance
        with patch.object(self.scheduler, '_deliver_response') as mock_deliver:
            self.scheduler.conversation_loop()
            
            # Should have delivered some goodbye message
            mock_deliver.assert_called()
            self.assertFalse(self.scheduler.is_running)
            
            # Check that the message contains goodbye-like content
            call_args = mock_deliver.call_args[0][0]  # Get the first argument of the call
            self.assertTrue(any(word in call_args.lower() for word in ['thank', 'goodbye', 'bye', 'great day']))
