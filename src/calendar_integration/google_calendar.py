import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class GoogleCalendarClient:
    def __init__(self):
        self.service = None
        self.calendar_id = settings.GOOGLE_CALENDAR_ID
        self.timezone = pytz.timezone('UTC')
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API"""
        try:
            if not os.path.exists(settings.GOOGLE_CREDENTIALS_PATH):
                raise FileNotFoundError(f"Credentials file not found: {settings.GOOGLE_CREDENTIALS_PATH}")
            
            credentials = Credentials.from_service_account_file(
                settings.GOOGLE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/calendar']
            )
            
            self.service = build('calendar', 'v3', credentials=credentials)
            logger.info("Successfully authenticated with Google Calendar")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Calendar: {e}")
            raise
    
    def get_events(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events within a time range"""
        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info(f"Retrieved {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error retrieving events: {e}")
            return []
    
    # Update your find_free_slots method in google_calendar.py with better debugging:

    def find_free_slots(self, duration_minutes: int, 
                start_date: datetime, 
                end_date: datetime,
                working_hours: tuple = (9, 17),
                include_weekends: bool = True) -> List[Dict]: 
        """Find free time slots of specified duration"""
        try:
            print(f"DEBUG: find_free_slots called with:")
            print(f"  - duration: {duration_minutes} minutes")
            print(f"  - start_date: {start_date}")
            print(f"  - end_date: {end_date}")
            print(f"  - include_weekends: {include_weekends}")
            
            # Get existing events
            events = self.get_events(start_date, end_date)
            
            free_slots = []
            current_date = start_date.date()
            
            while current_date <= end_date.date():
                print(f"DEBUG: Processing date {current_date}, weekday: {current_date.weekday()}")
                
                if include_weekends or current_date.weekday() < 5:  
                    print(f"DEBUG: Including date {current_date}")
                    day_slots = self._find_day_free_slots(
                        current_date, events, duration_minutes, working_hours
                    )
                    print(f"DEBUG: Found {len(day_slots)} slots for {current_date}")
                    free_slots.extend(day_slots)
                else:
                    print(f"DEBUG: Skipping weekend date {current_date}")
                
                current_date += timedelta(days=1)
            
            logger.info(f"Found {len(free_slots)} free slots")
            print(f"DEBUG: Total slots found: {len(free_slots)}")
            
            # Print first few slots for debugging
            for i, slot in enumerate(free_slots[:3]):
                print(f"DEBUG: Slot {i+1}: {slot['formatted_time']}")
            
            return free_slots
            
        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _find_day_free_slots(self, date, events: List[Dict], 
                    duration_minutes: int, working_hours: tuple) -> List[Dict]:
        """Find free slots for a specific day """
        slots = []
        start_hour, end_hour = working_hours
        
        print(f"DEBUG: _find_day_free_slots for {date}")
        print(f"DEBUG: Working hours: {start_hour}:00 to {end_hour}:00")
        
        # Create time slots with consistent timezone handling
        day_start = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        day_start = self.timezone.localize(day_start)
        day_end = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
        day_end = self.timezone.localize(day_end)
        
        print(f"DEBUG: Day range: {day_start} to {day_end}")
        
        # Convert all events to UTC for consistent comparison
        day_events = []
        for event in events:
            event_start = self._parse_event_time(event.get('start', {}))
            event_end = self._parse_event_time(event.get('end', {}))
            
            if event_start and event_end:
                # Convert to UTC if not already
                if event_start.tzinfo != pytz.UTC:
                    event_start = event_start.astimezone(pytz.UTC)
                if event_end.tzinfo != pytz.UTC:
                    event_end = event_end.astimezone(pytz.UTC)
                    
                # Check if event overlaps with our day
                if event_start.date() == date or event_end.date() == date:
                    day_events.append({
                        'start': event_start,
                        'end': event_end,
                        'summary': event.get('summary', 'Busy')
                    })
        
        print(f"DEBUG: Found {len(day_events)} events for {date}")
        for event in day_events:
            print(f"DEBUG: Event: {event['start']} to {event['end']}")
        
        # Sort events by start time
        day_events.sort(key=lambda x: x['start'])
        
        # Find gaps with proper time ordering
        current_time = day_start
        print(f"DEBUG: Starting from: {current_time}")
        
        for event in day_events:
            print(f"DEBUG: Processing event: {event['start']} to {event['end']}")
            
            # Only consider events that intersect with our working hours
            if event['end'] <= day_start or event['start'] >= day_end:
                print(f"DEBUG: Event outside working hours, skipping")
                continue
                
            # Adjust event times to working hours
            event_start = max(event['start'], day_start)
            event_end = min(event['end'], day_end)
            
            # Check if there's a gap before this event
            if current_time < event_start:
                gap_minutes = (event_start - current_time).total_seconds() / 60
                print(f"DEBUG: Gap before event: {gap_minutes} minutes")
                
                if gap_minutes >= duration_minutes:
                    slots.append({
                        'start': current_time,
                        'end': event_start,
                        'duration_available': int(gap_minutes)
                    })
                    print(f"DEBUG: Added gap slot: {current_time} to {event_start}")
            
            current_time = max(current_time, event_end)
            print(f"DEBUG: Updated current_time to: {current_time}")
        
        # Check for slot after last event (ensure proper time ordering)
        if current_time < day_end:
            final_gap_minutes = (day_end - current_time).total_seconds() / 60
            print(f"DEBUG: Final gap: {final_gap_minutes} minutes ({current_time} to {day_end})")
            
            if final_gap_minutes >= duration_minutes:
                slots.append({
                    'start': current_time,
                    'end': day_end,
                    'duration_available': int(final_gap_minutes)
                })
                print(f"DEBUG: Added final slot: {current_time} to {day_end}")
        
        print(f"DEBUG: Total gaps found: {len(slots)}")
        
        # Generate specific time slots within gaps
        valid_slots = []
        for i, slot in enumerate(slots):
            print(f"DEBUG: Processing gap {i+1}: {slot['start']} to {slot['end']} ({slot['duration_available']} min)")
            
            if slot['duration_available'] >= duration_minutes:
                slot_start = slot['start']
                slot_end = slot['end']
                
                # Create hourly slots within the gap, respecting gap boundaries
                while slot_start + timedelta(minutes=duration_minutes) <= slot_end:
                    meeting_end = slot_start + timedelta(minutes=duration_minutes)
                    valid_slots.append({
                        'start': slot_start,
                        'end': meeting_end,
                        'formatted_time': self._format_time_slot(slot_start, meeting_end)
                    })
                    print(f"DEBUG: Created slot: {slot_start.strftime('%I:%M %p')} to {meeting_end.strftime('%I:%M %p')}")
                    slot_start += timedelta(hours=1)  # Move to next hour
        
        print(f"DEBUG: Total valid slots created: {len(valid_slots)}")
        return valid_slots
    
    def _parse_event_time(self, time_dict: Dict) -> Optional[datetime]:
        """Parse event time from Google Calendar format"""
        if 'dateTime' in time_dict:
            return datetime.fromisoformat(time_dict['dateTime'].replace('Z', '+00:00'))
        elif 'date' in time_dict:
            # All-day event
            date_obj = datetime.strptime(time_dict['date'], '%Y-%m-%d').date()
            return self.timezone.localize(datetime.combine(date_obj, datetime.min.time()))
        return None
    
    def _format_time_slot(self, start: datetime, end: datetime) -> str:
        """Format time slot for display in UTC"""
        # Don't convert timezone - keep as UTC
        date_str = start.strftime('%A, %B %d')
        start_time = start.strftime('%I:%M %p').lstrip('0')
        end_time = end.strftime('%I:%M %p').lstrip('0')
        
        return f"{date_str} from {start_time} to {end_time} UTC"
    
    def create_event(self, title: str, start_time: datetime, 
                    end_time: datetime, description: str = "") -> Optional[str]:
        """Create a new calendar event"""
        try:
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(self.timezone),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(self.timezone),
                },
            }
            
            created_event = self.service.events().insert(
                calendarId=self.calendar_id,
                body=event
            ).execute()
            
            event_id = created_event.get('id')
            logger.info(f"Created event with ID: {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return None
    
    def find_event_by_reference(self, reference: str, days_ahead: int = 14) -> Optional[Dict]:
        """Find event by partial name or description"""
        try:
            end_time = datetime.now(self.timezone) + timedelta(days=days_ahead)
            events = self.get_events(datetime.now(self.timezone), end_time)
            
            reference_lower = reference.lower()
            
            for event in events:
                summary = event.get('summary', '').lower()
                description = event.get('description', '').lower()
                
                if reference_lower in summary or reference_lower in description:
                    return {
                        'id': event.get('id'),
                        'summary': event.get('summary'),
                        'start': self._parse_event_time(event.get('start', {})),
                        'end': self._parse_event_time(event.get('end', {}))
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding event by reference: {e}")
            return None
