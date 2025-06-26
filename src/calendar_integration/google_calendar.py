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
    
    def find_free_slots(self, duration_minutes: int, 
                       start_date: datetime, 
                       end_date: datetime,
                       working_hours: tuple = (9, 17)) -> List[Dict]:
        """Find free time slots of specified duration"""
        try:
            # Get existing events
            events = self.get_events(start_date, end_date)
            
            free_slots = []
            current_date = start_date.date()
            
            while current_date <= end_date.date():
                # Skip weekends
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    day_slots = self._find_day_free_slots(
                        current_date, events, duration_minutes, working_hours
                    )
                    free_slots.extend(day_slots)
                
                current_date += timedelta(days=1)
            
            logger.info(f"Found {len(free_slots)} free slots")
            return free_slots
            
        except Exception as e:
            logger.error(f"Error finding free slots: {e}")
            return []
    
    def _find_day_free_slots(self, date, events: List[Dict], 
                           duration_minutes: int, working_hours: tuple) -> List[Dict]:
        """Find free slots for a specific day"""
        slots = []
        start_hour, end_hour = working_hours
        
        # Create time slots for the day
        day_start = datetime.combine(date, datetime.min.time().replace(hour=start_hour))
        day_start = self.timezone.localize(day_start)
        day_end = datetime.combine(date, datetime.min.time().replace(hour=end_hour))
        day_end = self.timezone.localize(day_end)
        
        # Get events for this day
        day_events = []
        for event in events:
            event_start = self._parse_event_time(event.get('start', {}))
            event_end = self._parse_event_time(event.get('end', {}))
            
            if event_start and event_end:
                if event_start.date() == date:
                    day_events.append({
                        'start': event_start,
                        'end': event_end,
                        'summary': event.get('summary', 'Busy')
                    })
        
        # Sort events by start time
        day_events.sort(key=lambda x: x['start'])
        
        # Find gaps between events
        current_time = day_start
        
        for event in day_events:
            # Check if there's a gap before this event
            if (event['start'] - current_time).total_seconds() >= duration_minutes * 60:
                slots.append({
                    'start': current_time,
                    'end': event['start'],
                    'duration_available': int((event['start'] - current_time).total_seconds() / 60)
                })
            
            current_time = max(current_time, event['end'])
        
        # Check for slot after last event
        if (day_end - current_time).total_seconds() >= duration_minutes * 60:
            slots.append({
                'start': current_time,
                'end': day_end,
                'duration_available': int((day_end - current_time).total_seconds() / 60)
            })
        
        # Filter slots that can accommodate the meeting duration
        valid_slots = []
        for slot in slots:
            if slot['duration_available'] >= duration_minutes:
                # Create specific time slots within this gap
                slot_start = slot['start']
                while (slot['end'] - slot_start).total_seconds() >= duration_minutes * 60:
                    valid_slots.append({
                        'start': slot_start,
                        'end': slot_start + timedelta(minutes=duration_minutes),
                        'formatted_time': self._format_time_slot(slot_start, slot_start + timedelta(minutes=duration_minutes))
                    })
                    slot_start += timedelta(hours=1)  # Check hourly intervals
        
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
        """Format time slot for display"""
        start_local = start.astimezone()
        end_local = end.astimezone()
        
        date_str = start_local.strftime('%A, %B %d')
        start_time = start_local.strftime('%I:%M %p').lstrip('0')
        end_time = end_local.strftime('%I:%M %p').lstrip('0')
        
        return f"{date_str} from {start_time} to {end_time}"
    
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
