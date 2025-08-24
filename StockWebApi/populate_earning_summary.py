#!/usr/bin/env python3
"""
Script to populate the initial earningsummary.json file.

This script should be run once to create the initial earning summary data
for all stocks. After that, the daily job will keep it updated.

Usage:
    python populate_earning_summary.py
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from earning_summary_file_manager import populate_initial_earning_summary

def main():
    """Main function to populate the initial earning summary file."""
    print("Starting initial population of earningsummary.json...")
    print("This may take several minutes depending on the number of stocks...")
    
    try:
        success = populate_initial_earning_summary()
        
        if success:
            print("✅ Successfully populated earningsummary.json!")
            print("The file is now ready and will be updated daily at 9 PM.")
        else:
            print("❌ Failed to populate earningsummary.json")
            print("Check the logs for more details.")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during population: {str(e)}")
        print("Check the logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
