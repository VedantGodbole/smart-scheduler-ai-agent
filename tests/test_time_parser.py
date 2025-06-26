import unittest
from datetime import datetime, timedelta
import pytz
from src.utils.time_parser import TimeParser

class TestTimeParser(unittest.TestCase):
    def setUp(self):
        self.parser = TimeParser('UTC')
    
    def test_parse_duration_hours(self):
        """Test parsing duration in hours"""
        self.assertEqual(self.parser.parse_duration("1 hour"), 60)
        self.assertEqual(self.parser.parse_duration("2 hours"), 120)
        self.assertEqual(self.parser.parse_duration("half hour"), 30)
    
    def test_parse_duration_minutes(self):
        """Test parsing duration in minutes"""
        self.assertEqual(self.parser.parse_duration("30 minutes"), 30)
        self.assertEqual(self.parser.parse_duration("45 mins"), 45)
        self.assertEqual(self.parser.parse_duration("15 m"), 15)
    
    def test_parse_time_preference_days(self):
        """Test parsing day preferences"""
        prefs = self.parser.parse_time_preference("Tuesday afternoon")
        self.assertIn("Tuesday", prefs['days'])
        self.assertIn("afternoon", [str(t) for t in prefs['times']])
    
    def test_parse_time_preference_constraints(self):
        """Test parsing time constraints"""
        prefs = self.parser.parse_time_preference("not too early and not on Wednesday")
        self.assertTrue(len(prefs['constraints']) > 0)
    
    def test_complex_time_request(self):
        """Test complex time parsing"""
        result = self.parser.parse_complex_time_request("before my flight on Friday at 6 PM")
        self.assertEqual(result['type'], 'deadline_based')
        self.assertTrue(result['needs_calendar_lookup'])
