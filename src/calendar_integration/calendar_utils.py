from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class CalendarUtils:
    @staticmethod
    def filter_slots_by_preferences(slots: List[Dict], preferences: Dict) -> List[Dict]:
        """Filter available slots based on user preferences - FIXED"""
        filtered_slots = []
        
        print(f"DEBUG: Filtering {len(slots)} slots with preferences: {preferences}")
        
        for slot in slots:
            slot_start = slot['start']
            slot_date = slot_start.date()
            slot_hour = slot_start.hour
            
            # CHECK 1: Relative dates (like "tomorrow") - THIS WAS MISSING
            relative_dates = preferences.get('relative_dates', [])
            if relative_dates:
                target_dates = [rd.get('target_date') for rd in relative_dates if rd.get('target_date')]
                if target_dates and slot_date not in target_dates:
                    print(f"DEBUG: Slot {slot_date} not in target dates {target_dates}")
                    continue
            
            # CHECK 2: Day preferences
            preferred_days = preferences.get('days', [])
            if preferred_days:
                day_name = slot_start.strftime('%A')
                if day_name not in preferred_days:
                    continue
            
            # CHECK 3: Time preferences - FIXED LOGIC
            time_preferences = preferences.get('times', [])
            if time_preferences:
                matches_time = False
                for pref in time_preferences:
                    if pref == 'morning' and 6 <= slot_hour < 12:
                        matches_time = True
                        break
                    elif pref == 'afternoon' and 12 <= slot_hour < 18:
                        matches_time = True
                        break
                    elif pref == 'evening' and 18 <= slot_hour < 22:
                        matches_time = True
                        break
                
                if not matches_time:
                    print(f"DEBUG: Slot at {slot_hour}:00 doesn't match time preferences {time_preferences}")
                    continue
            
            # CHECK 4: Constraints
            constraints = preferences.get('constraints', [])
            violates_constraint = False
            for constraint in constraints:
                if constraint == 'not_early' and slot_hour < 9:
                    violates_constraint = True
                    break
            
            if violates_constraint:
                continue
            
            filtered_slots.append(slot)
        
        print(f"DEBUG: Filtered to {len(filtered_slots)} matching slots")
        return filtered_slots
    
    @staticmethod
    def _matches_time_preference(hour: int, time_preferences: List) -> bool:
        """Check if hour matches time preferences"""
        for pref in time_preferences:
            if isinstance(pref, str):
                if 'morning' in pref.lower() and 6 <= hour < 12:
                    return True
                elif 'afternoon' in pref.lower() and 12 <= hour < 17:
                    return True
                elif 'evening' in pref.lower() and 17 <= hour < 22:
                    return True
            elif isinstance(pref, tuple) and len(pref) >= 2:
                # Handle time ranges like ('2', '00', 'pm')
                try:
                    pref_hour = int(pref[0])
                    if len(pref) > 2 and pref[2].lower() == 'pm' and pref_hour != 12:
                        pref_hour += 12
                    if hour == pref_hour:
                        return True
                except (ValueError, IndexError):
                    continue
        
        return len(time_preferences) == 0  # No preference means any time is okay
    
    @staticmethod
    def _violates_constraints(slot_time: datetime, constraints: List) -> bool:
        """Check if slot violates any constraints"""
        hour = slot_time.hour
        
        for constraint in constraints:
            if isinstance(constraint, tuple):
                constraint_text = ' '.join(str(c) for c in constraint)
            else:
                constraint_text = str(constraint)
            
            constraint_lower = constraint_text.lower()
            
            # Check "not early" constraint
            if 'not' in constraint_lower and 'early' in constraint_lower:
                if hour < 10:  # Before 10 AM is considered early
                    return True
            
            # Check "not late" constraint
            if 'not' in constraint_lower and 'late' in constraint_lower:
                if hour > 16:  # After 4 PM is considered late
                    return True
            
            # Check "not on [day]" constraint
            if 'not on' in constraint_lower:
                day_name = slot_time.strftime('%A').lower()
                if day_name in constraint_lower:
                    return True
        
        return False
    
    @staticmethod
    def suggest_alternatives(original_preferences: Dict, all_slots: List[Dict]) -> List[Dict]:
        """Suggest alternative time slots when preferred ones aren't available"""
        alternatives = []
        
        # If no slots match preferences, suggest closest alternatives
        if not all_slots:
            return alternatives
        
        # Group slots by day
        slots_by_day = {}
        for slot in all_slots:
            day = slot['start'].strftime('%A')
            if day not in slots_by_day:
                slots_by_day[day] = []
            slots_by_day[day].append(slot)
        
        # Suggest different days if preferred day is busy
        preferred_days = original_preferences.get('days', [])
        if preferred_days:
            for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
                if day not in preferred_days and day in slots_by_day:
                    alternatives.extend(slots_by_day[day][:2])  # Add first 2 slots
        
        # Suggest different times if preferred time is busy
        preferred_times = original_preferences.get('times', [])
        if preferred_times and 'morning' in str(preferred_times).lower():
            # Suggest afternoon slots
            afternoon_slots = [s for s in all_slots if 12 <= s['start'].hour < 17]
            alternatives.extend(afternoon_slots[:2])
        
        return alternatives[:5]  # Return max 5 alternatives
