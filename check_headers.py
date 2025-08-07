#!/usr/bin/env python3
"""
Simple check of sheet headers
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from call_manager import CallManager
    
    # Load environment variables from .env
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    call_manager = CallManager()
    
    print("Checking configuration:")
    print(f"  Sheet ID: {call_manager.spreadsheet_id}")
    print(f"  Sheet Name: {call_manager.sheet_name}")
    print(f"  Expected headers: {call_manager.headers}")
    print()
    
    # Initialize and check the sheet
    call_manager._initialize_service()
    
    # Get actual headers from sheet
    range_name = f"'{call_manager.sheet_name}'!1:1"
    result = call_manager.service.spreadsheets().values().get(
        spreadsheetId=call_manager.spreadsheet_id,
        range=range_name
    ).execute()
    
    actual_headers = result.get('values', [[]])[0] if result.get('values') else []
    
    print("Actual sheet headers:")
    for i, header in enumerate(actual_headers, 1):
        print(f"  {i}. {header}")
    
    print()
    print("Status:")
    if 'caller_phone_number' in actual_headers:
        print("SUCCESS: caller_phone_number column found!")
        pos = actual_headers.index('caller_phone_number') + 1
        print(f"It's in position {pos}")
    else:
        print("MISSING: caller_phone_number column not found")
        print("Please add this column manually to your sheet")
        
except Exception as e:
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()