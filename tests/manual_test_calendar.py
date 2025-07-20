#!/usr/bin/env python3
"""
Simple Manual Calendar Test
Just create a test meeting manually to verify everything works
"""

import sys
from datetime import datetime, timedelta
import pytz

# Add the src directory to the path
sys.path.append('.')

def create_test_meeting():
    """Create a simple test meeting"""
    print("📅 Manual Calendar Test")
    print("=" * 30)
    
    try:
        # Import our calendar client
        from src.calendar_integration.google_calendar import GoogleCalendarClient
        
        print("🔌 Connecting to Google Calendar...")
        calendar = GoogleCalendarClient()
        print("✅ Connected successfully!")
        
        # Set up meeting details
        print("\n📝 Setting up test meeting...")
        
        # Create meeting for tomorrow at 2:00 PM IST
        ist_tz = pytz.timezone('Asia/Kolkata')
        tomorrow = datetime.now(ist_tz) + timedelta(days=1)
        
        # Set to 2:00 PM IST tomorrow
        meeting_start = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)
        meeting_end = meeting_start + timedelta(minutes=30)  # 30-minute meeting
        
        # Convert to UTC for API
        meeting_start_utc = meeting_start.astimezone(pytz.UTC)
        meeting_end_utc = meeting_end.astimezone(pytz.UTC)
        
        print(f"📅 Meeting Date: {meeting_start.strftime('%A, %B %d, %Y')}")
        print(f"⏰ Time (IST): {meeting_start.strftime('%I:%M %p')} - {meeting_end.strftime('%I:%M %p')}")
        print(f"⏰ Time (UTC): {meeting_start_utc.strftime('%I:%M %p')} - {meeting_end_utc.strftime('%I:%M %p')}")
        
        # Create the event
        print("\n🔄 Creating calendar event...")
        
        event_title = "[MANUAL TEST] Smart Scheduler Test Meeting"
        description = f"Manual test meeting created at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        event_id = calendar.create_event(
            title=event_title,
            start_time=meeting_start_utc,
            end_time=meeting_end_utc,
            description=description
        )
        
        if event_id:
            print("✅ SUCCESS! Meeting created!")
            print(f"🆔 Event ID: {event_id}")
            print(f"📅 Title: {event_title}")
            print(f"🕐 When: {meeting_start.strftime('%A, %B %d at %I:%M %p IST')}")
            print()
            print("🌐 Check your Google Calendar at: https://calendar.google.com")
            print(f"🔍 Look for the event tomorrow at {meeting_start.strftime('%I:%M %p IST')}")
            
            return True
        else:
            print("❌ Failed to create meeting")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_available_slots():
    """Find available time slots"""
    print("\n📅 Finding Available Slots")
    print("=" * 30)
    
    try:
        from src.calendar_integration.google_calendar import GoogleCalendarClient
        
        calendar = GoogleCalendarClient()
        
        # Look for 30-minute slots in next 2 days
        start_date = datetime.now(pytz.UTC)
        end_date = start_date + timedelta(days=2)
        
        print(f"🔍 Searching for 30-minute slots...")
        print(f"📅 From: {start_date.date()} to {end_date.date()}")
        
        slots = calendar.find_free_slots(30, start_date, end_date)
        
        if slots:
            print(f"\n✅ Found {len(slots)} available slots:")
            
            # Show first 5 slots with IST conversion
            ist_tz = pytz.timezone('Asia/Kolkata')
            
            for i, slot in enumerate(slots[:5], 1):
                start_ist = slot['start'].astimezone(ist_tz)
                end_ist = slot['end'].astimezone(ist_tz)
                
                print(f"  {i}. {start_ist.strftime('%A, %B %d at %I:%M %p')} - {end_ist.strftime('%I:%M %p')} IST")
            
            return slots
        else:
            print("❌ No available slots found")
            return []
            
    except Exception as e:
        print(f"❌ Error finding slots: {e}")
        return []

def main():
    """Main test function"""
    print("🧪 SIMPLE MANUAL TEST")
    print("=" * 50)
    print("Let's test the Smart Scheduler manually!")
    print()
    
    # Test 1: Find available slots
    print("TEST 1: Finding available time slots")
    slots = find_available_slots()
    
    if not slots:
        print("\n⚠️ No slots found, but let's continue with creating a test meeting anyway...")
    
    print("\n" + "-" * 50)
    
    # Test 2: Create a test meeting
    print("TEST 2: Creating a test meeting")
    success = create_test_meeting()
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 MANUAL TEST SUCCESSFUL!")
        print("✅ Smart Scheduler calendar integration is working!")
        print()
        print("💡 Next steps:")
        print("1. Check your Google Calendar for the test meeting")
        print("2. Try running the full Smart Scheduler: python main.py")
        print("3. The voice + AI features should work now!")
    else:
        print("❌ MANUAL TEST FAILED")
        print("💡 Things to check:")
        print("1. Google Calendar credentials")
        print("2. Calendar sharing permissions")
        print("3. Internet connection")

if __name__ == "__main__":
    main()
