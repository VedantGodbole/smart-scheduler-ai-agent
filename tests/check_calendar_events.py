#!/usr/bin/env python3
"""
Check Calendar Events Script
This script checks what events exist in your calendar and helps debug visibility issues.
"""

import os
from datetime import datetime, timedelta
import pytz
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

def check_calendar_events():
    """Check what events are in the calendar"""
    
    try:
        # Initialize Google Calendar client
        credentials_path = 'credentials/google_credentials.json'
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        
        # Get calendar ID from environment or use 'primary'
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        print(f"🔍 Checking calendar: {calendar_id}")
        
        # Search for events in the next 7 days
        now = datetime.now(pytz.UTC)
        end_time = now + timedelta(days=7)
        
        print(f"📅 Searching for events from {now.date()} to {end_time.date()}")
        
        # Get events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        print(f"\n📊 Found {len(events)} events:")
        print("=" * 60)
        
        if not events:
            print("❌ No events found!")
            print("\n💡 Possible reasons:")
            print("1. Events were created in a different calendar")
            print("2. Service account doesn't have access to your personal calendar") 
            print("3. Wrong calendar ID in settings")
            return False
        
        # Display events
        for i, event in enumerate(events, 1):
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            summary = event.get('summary', 'No title')
            event_id = event.get('id', 'No ID')
            
            # Parse datetime for display
            if 'T' in start:  # dateTime format
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                time_str = f"{start_dt.strftime('%A, %B %d at %I:%M %p')} - {end_dt.strftime('%I:%M %p')} UTC"
            else:  # date format (all-day)
                time_str = f"All day on {start}"
            
            print(f"{i}. 📅 {summary}")
            print(f"   ⏰ {time_str}")
            print(f"   🆔 ID: {event_id}")
            
            # Check if this might be our Smart Scheduler event
            if 'meeting' in summary.lower() or 'smart scheduler' in summary.lower():
                print("   ⭐ This looks like a Smart Scheduler event!")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking calendar: {e}")
        return False

def check_calendar_list():
    """Check which calendars the service account can access"""
    
    try:
        credentials_path = 'credentials/google_credentials.json'
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        
        print("\n🔍 Checking accessible calendars...")
        
        # Get calendar list
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        print(f"📊 Service account has access to {len(calendars)} calendars:")
        
        for cal in calendars:
            cal_id = cal.get('id', 'unknown')
            summary = cal.get('summary', 'No name')
            access_role = cal.get('accessRole', 'unknown')
            primary = ' (PRIMARY)' if cal.get('primary', False) else ''
            
            print(f"  📅 {summary}{primary}")
            print(f"      🆔 ID: {cal_id}")
            print(f"      🔐 Access: {access_role}")
            print()
        
        return calendars
        
    except Exception as e:
        print(f"❌ Error checking calendar list: {e}")
        return []

def search_for_specific_event(event_id):
    """Search for a specific event by ID"""
    
    if not event_id:
        print("❌ No event ID provided")
        return False
    
    try:
        credentials_path = 'credentials/google_credentials.json'
        credentials = Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/calendar']
        )
        
        service = build('calendar', 'v3', credentials=credentials)
        calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        print(f"\n🔍 Searching for event ID: {event_id}")
        
        # Try to get the specific event
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        
        print("✅ Event found!")
        print(f"📅 Title: {event.get('summary', 'No title')}")
        print(f"⏰ Start: {event['start'].get('dateTime', event['start'].get('date'))}")
        print(f"⏰ End: {event['end'].get('dateTime', event['end'].get('date'))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Event not found or error: {e}")
        return False

def main():
    """Main function"""
    print("🔍 Calendar Event Checker")
    print("=" * 50)
    
    # Check accessible calendars
    calendars = check_calendar_list()
    
    # Check events in the calendar
    check_calendar_events()
    
    # Search for the specific event that was just created
    print("\n" + "=" * 50)
    print("🔍 Searching for the Smart Scheduler event...")
    
    # The event ID from your log: mf9qbn2tmjut41aehuqrciih0c
    event_id = "mf9qbn2tmjut41aehuqrciih0c"
    search_for_specific_event(event_id)
    
    print("\n💡 Troubleshooting Tips:")
    print("1. Check if the event is in your personal Google Calendar at calendar.google.com")
    print("2. The event might be in the service account's calendar, not yours")
    print("3. Try refreshing your calendar view")
    print("4. Check if you shared your calendar with the service account properly")

if __name__ == "__main__":
    main()
