#!/usr/bin/env python3
"""
Smart Scheduler AI Agent
Main entry point for the application
"""

import sys
import argparse
from config.settings import settings
from src.agent.smart_scheduler import SmartScheduler
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Smart Scheduler AI Agent')
    parser.add_argument('--test', action='store_true', help='Run in test mode (text only)')
    parser.add_argument('--no-voice', action='store_true', help='Disable voice mode')
    
    args = parser.parse_args()
    
    try:
        # Validate settings
        settings.validate()
        
        # Initialize the Smart Scheduler
        scheduler = SmartScheduler()
        
        if args.test:
            # Run in test mode
            scheduler.test_mode()
        else:
            # Run in normal mode
            voice_enabled = not args.no_voice
            print(f"Starting Smart Scheduler...")
            print(f"Voice mode: {'Enabled' if voice_enabled else 'Disabled'}")
            print("Say 'exit' or 'quit' to end the conversation")
            print("-" * 50)
            
            scheduler.start_conversation(voice_enabled=voice_enabled)
    
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
