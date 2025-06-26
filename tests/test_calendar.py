import unittest
import os
import json
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.calendar_integration.google_calendar import GoogleCalendarClient
from src.calendar_integration.calendar_utils import CalendarUtils

class TestRealCalendarIntegration(unittest.TestCase):
    """Integration tests with real Google Calendar API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up once for all tests - check if we can run real tests"""
        cls.can_run_real_tests = cls._check_real_calendar_setup()
        
        if cls.can_run_real_tests:
            print("✅ Real calendar credentials found - running integration tests")
            cls.calendar = GoogleCalendarClient()
        else:
            print("⚠️ Real calendar credentials not found - skipping integration tests")
    
    @classmethod
    def _check_real_calendar_setup(cls) -> bool:
        """Check if we have real Google Calendar credentials"""
        credentials_path = 'credentials/google_credentials.json'
        
        # Check if credentials file exists
        if not os.path.exists(credentials_path):
            print(f"❌ Credentials file not found: {credentials_path}")
            return False
        
        # Check if credentials file is valid JSON
        try:
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
                required_fields = ['type', 'project_id', 'client_email', 'private_key']
                for field in required_fields:
                    if field not in creds:
                        print(f"❌ Missing field in credentials: {field}")
                        return False
                print(f"✅ Found service account: {creds['client_email']}")
                return True
        except json.JSONDecodeError:
            print("❌ Invalid JSON in credentials file")
            return False
        except Exception as e:
            print(f"❌ Error reading credentials: {e}")
            return False
    
    def setUp(self):
        """Skip tests if real calendar setup not available"""
        if not self.can_run_real_tests:
            self.skipTest("Real Google Calendar credentials not available")
    
    def test_calendar_authentication(self):
        """Test that we can authenticate with Google Calendar"""
        print("\n🔐 Testing Google Calendar authentication...")
        
        # This should not raise an exception if authentication works
        self.assertIsNotNone(self.calendar.service)
        print("✅ Successfully authenticated with Google Calendar API")
    
    def test_get_events(self):
        """Test getting real events from calendar"""
        print("\n📅 Testing real calendar event retrieval...")
        
        # Get events for next 7 days
        start_time = datetime.now(pytz.UTC)
        end_time = start_time + timedelta(days=7)
        
        print(f"🔍 Searching for events from {start_time.date()} to {end_time.date()}")
        
        events = self.calendar.get_events(start_time, end_time)
        
        # Should return a list (even if empty)
        self.assertIsInstance(events, list)
        
        print(f"📊 Found {len(events)} events in the next 7 days")
        
        # Print first few events for debugging
        for i, event in enumerate(events[:3]):
            summary = event.get('summary', 'No title')
            start = event.get('start', {})
            print(f"  {i+1}. {summary} - {start}")
    
    def test_find_free_slots(self):
        """Test finding real free slots in calendar"""
        print("\n🔍 Testing real free slot finding...")
        
        # Look for 30-minute slots in next 3 days
        start_date = datetime.now(pytz.UTC)
        end_date = start_date + timedelta(days=3)
        duration_minutes = 30
        
        print(f"🔍 Looking for {duration_minutes}-minute slots from {start_date.date()} to {end_date.date()}")
        
        free_slots = self.calendar.find_free_slots(duration_minutes, start_date, end_date)
        
        # Should return a list
        self.assertIsInstance(free_slots, list)
        
        print(f"📊 Found {len(free_slots)} available {duration_minutes}-minute slots")
        
        # Print first few slots
        for i, slot in enumerate(free_slots[:5]):
            print(f"  {i+1}. {slot.get('formatted_time', 'No format')}")
        
        # Verify slot structure
        if free_slots:
            first_slot = free_slots[0]
            self.assertIn('start', first_slot)
            self.assertIn('end', first_slot)
            self.assertIn('formatted_time', first_slot)
            self.assertIsInstance(first_slot['start'], datetime)
            self.assertIsInstance(first_slot['end'], datetime)
    
    def test_time_parsing_with_calendar(self):
        """Test time parsing with real calendar data"""
        print("\n⏰ Testing time parsing with calendar context...")
        
        from src.utils.time_parser import TimeParser
        parser = TimeParser('UTC')
        
        # Test various duration parsing
        test_cases = [
            ("1 hour meeting", 60),
            ("30 minute call", 30),
            ("quick 15 min sync", 15),
            ("2 hour workshop", 120)
        ]
        
        for text, expected_minutes in test_cases:
            result = parser.parse_duration(text)
            self.assertEqual(result, expected_minutes)
            print(f"✅ '{text}' → {result} minutes")
    
    def test_calendar_utils_filtering(self):
        """Test calendar utils with slot data"""
        print("\n🔧 Testing calendar utilities with data...")
        
        # Get real slots
        start_date = datetime.now(pytz.UTC)
        end_date = start_date + timedelta(days=2)
        
        real_slots = self.calendar.find_free_slots(60, start_date, end_date)
        
        if not real_slots:
            print("⚠️ No free slots found - creating mock slots for testing")
            # Create some test slots if calendar is empty
            real_slots = [
                {
                    'start': datetime.now(pytz.UTC).replace(hour=10, minute=0),
                    'end': datetime.now(pytz.UTC).replace(hour=11, minute=0),
                    'formatted_time': 'Mock morning slot'
                },
                {
                    'start': datetime.now(pytz.UTC).replace(hour=14, minute=0),
                    'end': datetime.now(pytz.UTC).replace(hour=15, minute=0),
                    'formatted_time': 'Mock afternoon slot'
                }
            ]
        
        # Test filtering by afternoon preference
        preferences = {'days': [], 'times': ['afternoon'], 'constraints': []}
        filtered_slots = CalendarUtils.filter_slots_by_preferences(real_slots, preferences)
        
        print(f"📊 Original slots: {len(real_slots)}")
        print(f"📊 Afternoon slots: {len(filtered_slots)}")
        
        # Verify filtering worked
        for slot in filtered_slots:
            hour = slot['start'].hour
            self.assertTrue(12 <= hour < 17, f"Slot at {hour}:00 is not afternoon")
    
    def test_create_and_delete_test_event(self):
        """Test creating and deleting a real calendar event"""
        print("\n📝 Testing real event creation and deletion...")
        
        # Create a test event
        start_time = datetime.now(pytz.UTC) + timedelta(days=1)
        start_time = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        
        event_title = f"[TEST] Smart Scheduler Test Event {start_time.strftime('%Y%m%d_%H%M')}"
        
        print(f"📝 Creating test event: {event_title}")
        print(f"⏰ Time: {start_time} to {end_time}")
        
        event_id = self.calendar.create_event(
            title=event_title,
            start_time=start_time,
            end_time=end_time,
            description="Automated test event - safe to delete"
        )
        
        # Verify event was created
        self.assertIsNotNone(event_id)
        print(f"✅ Created event with ID: {event_id}")
        
        # Clean up - delete the test event
        try:
            self.calendar.service.events().delete(
                calendarId=self.calendar.calendar_id,
                eventId=event_id
            ).execute()
            print(f"🗑️ Cleaned up test event: {event_id}")
        except Exception as e:
            print(f"⚠️ Could not clean up test event {event_id}: {e}")
    
    def test_real_calendar_permissions(self):
        """Test that service account has proper calendar permissions"""
        print("\n🔒 Testing calendar permissions...")
        
        try:
            # Try to get calendar metadata
            calendar_list = self.calendar.service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            
            print(f"📊 Service account has access to {len(calendars)} calendars:")
            
            for cal in calendars:
                cal_id = cal.get('id', 'unknown')
                summary = cal.get('summary', 'No name')
                access_role = cal.get('accessRole', 'unknown')
                print(f"  📅 {summary} ({cal_id}) - Access: {access_role}")
            
            # Check if we have write access to primary calendar
            primary_calendar = next((cal for cal in calendars if cal.get('id') == 'primary'), None)
            if primary_calendar:
                access_role = primary_calendar.get('accessRole', 'none')
                self.assertIn(access_role, ['owner', 'writer'], 
                             f"Insufficient permissions: {access_role}")
                print(f"✅ Has {access_role} access to primary calendar")
            else:
                print("⚠️ Primary calendar not found in accessible calendars")
                
        except Exception as e:
            self.fail(f"Permission test failed: {e}")

if __name__ == '__main__':
    # Custom test runner with more verbose output
    import sys
    
    print("🧪 Running Real Google Calendar Integration Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRealCalendarIntegration)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("🎉 All real calendar integration tests passed!")
    else:
        print("❌ Some real calendar integration tests failed")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
