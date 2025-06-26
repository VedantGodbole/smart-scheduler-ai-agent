import re
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from typing import Optional, Tuple, List
import pytz
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class TimeParser:
    def __init__(self, timezone: str = 'UTC'):
        self.timezone = pytz.timezone(timezone)
        self.now = datetime.now(self.timezone)
    
    def parse_duration(self, text: str) -> Optional[int]:
        """Parse meeting duration from text, return minutes"""
        duration_patterns = [
            (r'(\d+)\s*hours?', 60),
            (r'(\d+)\s*hrs?', 60),
            (r'(\d+)\s*h', 60),
            (r'(\d+)\s*minutes?', 1),
            (r'(\d+)\s*mins?', 1),
            (r'(\d+)\s*m(?!\w)', 1),
        ]
        
        text_lower = text.lower()
        
        for pattern, multiplier in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return int(match.group(1)) * multiplier
        
        # Handle written numbers
        number_words = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'half': 0.5, 'quarter': 0.25
        }
        
        for word, num in number_words.items():
            if f"{word} hour" in text_lower:
                return int(num * 60)
        
        return None
    
    def parse_time_preference(self, text: str) -> dict:
        """Parse time preferences from natural language"""
        preferences = {
            'days': [],
            'times': [],
            'constraints': [],
            'relative_dates': []
        }
        
        text_lower = text.lower()
        
        # Day patterns
        days_pattern = r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        days_found = re.findall(days_pattern, text_lower)
        preferences['days'] = [day.capitalize() for day in days_found]
        
        # Time patterns
        time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b',
            r'\b(\d{1,2})\s*(am|pm)\b',
            r'\b(morning|afternoon|evening|night)\b',
            r'\b(early|late)\s+(morning|afternoon|evening)\b'
        ]
        
        for pattern in time_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                preferences['times'].extend(matches)
        
        # Relative date patterns
        relative_patterns = [
            r'\b(next|this)\s+(week|month)\b',
            r'\b(tomorrow|today)\b',
            r'\b(next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(\d+)\s+days?\s+(from\s+now|later)\b'
        ]
        
        for pattern in relative_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                preferences['relative_dates'].extend(matches)
        
        # Constraint patterns
        constraint_patterns = [
            r'\bnot\s+(too\s+)?(early|late)\b',
            r'\bnot\s+on\s+(\w+)\b',
            r'\bafter\s+(\d{1,2}:?\d{0,2})\s*(am|pm)?\b',
            r'\bbefore\s+(\d{1,2}:?\d{0,2})\s*(am|pm)?\b'
        ]
        
        for pattern in constraint_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                preferences['constraints'].extend(matches)
        
        return preferences
    
    def parse_complex_time_request(self, text: str) -> dict:
        """Handle complex time parsing scenarios"""
        result = {
            'type': 'simple',
            'parsed_data': {},
            'needs_calendar_lookup': False
        }
        
        text_lower = text.lower()
        
        # Check for deadline-based requests FIRST (more specific)
        if 'before my flight' in text_lower or 'before I leave' in text_lower:
            result['type'] = 'deadline_based'
            result['needs_calendar_lookup'] = True
            result['parsed_data'] = self._parse_deadline_request(text_lower)
        
        # Check for last/first day patterns
        elif 'last weekday' in text_lower or 'first weekday' in text_lower:
            result['type'] = 'calculated_date'
            result['parsed_data'] = self._parse_calculated_date(text_lower)
        
        # Check for event-relative requests (more general)
        elif 'before my' in text_lower or 'after my' in text_lower:
            result['type'] = 'event_relative'
            result['needs_calendar_lookup'] = True
            
            # Extract the referenced event
            event_match = re.search(r'(before|after)\s+my\s+(.+?)(?:\s+(?:meeting|event|appointment))?(?:\s+(?:on|at))?', text_lower)
            if event_match:
                result['parsed_data'] = {
                    'relation': event_match.group(1),
                    'event_reference': event_match.group(2).strip()
                }
    
        return result
    
    def _parse_calculated_date(self, text: str) -> dict:
        """Parse calculated date expressions"""
        if 'last weekday of this month' in text:
            # Calculate last weekday of current month
            today = self.now.date()
            next_month = today.replace(day=28) + timedelta(days=4)
            last_day = next_month - timedelta(days=next_month.day)
            
            # Find last weekday
            while last_day.weekday() > 4:  # 0-4 are Mon-Fri
                last_day -= timedelta(days=1)
            
            return {
                'target_date': last_day,
                'description': 'last weekday of this month'
            }
        
        return {}
    
    def _parse_deadline_request(self, text: str) -> dict:
        """Parse deadline-based requests"""
        deadline_match = re.search(r'before\s+my\s+(.+?)\s+(?:that\s+)?(?:leaves|departs)?\s+(?:on\s+)?(\w+)\s+at\s+(\d{1,2}:?\d{0,2})\s*(am|pm)?', text)
        
        if deadline_match:
            return {
                'event_type': deadline_match.group(1),
                'day': deadline_match.group(2),
                'time': deadline_match.group(3),
                'period': deadline_match.group(4) or 'pm'
            }
        
        return {}

    def get_time_slots_for_preference(self, preferences: dict, duration_minutes: int) -> List[datetime]:
        """Generate potential time slots based on preferences"""
        slots = []
        base_date = self.now.date()
        
        # Generate slots for next 14 days
        for i in range(14):
            current_date = base_date + timedelta(days=i)
            
            # Skip weekends if not specified
            if current_date.weekday() > 4 and not any(day in ['Saturday', 'Sunday'] for day in preferences.get('days', [])):
                continue
            
            # Generate hourly slots from 9 AM to 5 PM
            for hour in range(9, 18):
                slot_time = datetime.combine(current_date, datetime.min.time().replace(hour=hour))
                slot_time = self.timezone.localize(slot_time)
                slots.append(slot_time)
        
        return slots