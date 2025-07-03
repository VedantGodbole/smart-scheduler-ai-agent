from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class CalendarUtils:
    @staticmethod
    def filter_slots_by_preferences(slots: List[Dict], preferences: Dict) -> List[Dict]:
        """ENHANCED: Filter slots with target date support"""
        filtered_slots = []
        
        print(f"DEBUG: Filtering {len(slots)} slots with preferences: {preferences}")
        
        # Get target date from conversation context if available
        target_date = preferences.get('target_date')
        
        for slot in slots:
            slot_start = slot['start']
            slot_date = slot_start.date()
            slot_hour = slot_start.hour
            
            # CHECK 1: Target date (like tomorrow or calculated date) - HIGHEST PRIORITY
            if target_date and slot_date != target_date:
                print(f"DEBUG: Slot {slot_date} doesn't match target {target_date}")
                continue
            
            # CHECK 2: Day preferences (only if no target date)
            if not target_date:
                preferred_days = preferences.get('days', [])
                if preferred_days:
                    day_name = slot_start.strftime('%A')
                    if day_name not in preferred_days:
                        continue
            
            # CHECK 3: Time preferences
            preferred_times = preferences.get('times', [])
            if preferred_times:
                matches_time = False
                for pref in preferred_times:
                    pref_lower = str(pref).lower()
                    if 'morning' in pref_lower:
                        if 'late' in pref_lower and 10 <= slot_hour < 12:
                            matches_time = True
                            break
                        elif 'late' not in pref_lower and 9 <= slot_hour < 12:
                            matches_time = True
                            break
                    elif 'afternoon' in pref_lower and 12 <= slot_hour < 18:
                        matches_time = True
                        break
                    elif 'evening' in pref_lower and 18 <= slot_hour < 22:
                        matches_time = True
                        break
                
                if not matches_time:
                    print(f"DEBUG: Slot at {slot_hour}:00 doesn't match time preferences {preferred_times}")
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
