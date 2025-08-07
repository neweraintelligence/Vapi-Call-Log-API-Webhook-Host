#!/usr/bin/env python3
"""
Debug script to check webhook payloads and phone number extraction
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from call_manager import CallManager

def debug_recent_calls():
    """Debug recent calls to see what data we have"""
    
    print("=== Debugging VAPI Phone Number Issue ===")
    print()
    
    # Load environment
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    try:
        call_manager = CallManager()
        call_manager._initialize_service()
        
        print("1. Checking recent calls in Google Sheet...")
        
        # Get recent call data
        range_name = f"'{call_manager.sheet_name}'!A:O"  # Get more columns to see all data
        result = call_manager.service.spreadsheets().values().get(
            spreadsheetId=call_manager.spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if len(values) <= 1:
            print("   No call data found in sheet")
            return
        
        headers = values[0]
        print(f"   Sheet headers: {headers}")
        
        # Find relevant columns
        id_col = headers.index('id') if 'id' in headers else None
        summary_col = headers.index('summary') if 'summary' in headers else None
        phone_col = headers.index('caller_phone_number') if 'caller_phone_number' in headers else None
        json_col = headers.index('json') if 'json' in headers else None
        
        print(f"   Key columns - ID: {id_col}, Summary: {summary_col}, Phone: {phone_col}, JSON: {json_col}")
        print()
        
        print("2. Recent calls analysis:")
        
        # Look at recent calls (last 5)
        recent_calls = values[1:6]  # Skip header, get first 5 data rows
        
        for i, row in enumerate(recent_calls, 1):
            # Pad row to match headers
            while len(row) < len(headers):
                row.append('')
            
            call_id = row[id_col] if id_col is not None else f"Row {i}"
            summary = row[summary_col] if summary_col is not None else "No summary"
            phone = row[phone_col] if phone_col is not None else "No phone"
            json_data = row[json_col] if json_col is not None else "No JSON"
            
            print(f"   Call {i}: {call_id}")
            print(f"     Summary: {summary[:60]}...")
            print(f"     Caller Phone: {phone}")
            
            # If there's JSON data, let's analyze it for phone numbers
            if json_data and json_data != "No JSON" and json_data.strip():
                print(f"     JSON data length: {len(json_data)} characters")
                try:
                    parsed_json = json.loads(json_data)
                    print("     JSON parsed successfully")
                    
                    # Try to extract phone number from this JSON
                    extracted_phone = call_manager._extract_caller_phone_number(parsed_json)
                    print(f"     Phone extraction result: {extracted_phone}")
                    
                    # Look for phone-like patterns in the JSON
                    json_str = str(parsed_json).lower()
                    phone_indicators = ['phone', 'from', 'number', 'caller', 'customer']
                    found_indicators = [ind for ind in phone_indicators if ind in json_str]
                    if found_indicators:
                        print(f"     Found phone-related fields: {found_indicators}")
                    
                except json.JSONDecodeError:
                    print("     JSON parsing failed")
                except Exception as e:
                    print(f"     JSON analysis error: {e}")
            else:
                print("     No JSON data available")
            
            print()
        
        print("3. Recommendations:")
        
        # Check if any calls have phone numbers
        calls_with_phones = sum(1 for row in recent_calls if len(row) > phone_col and row[phone_col] and row[phone_col].strip())
        
        if calls_with_phones == 0:
            print("   - No caller phone numbers found in any recent calls")
            print("   - This suggests the webhook isn't extracting phone numbers")
            print()
            print("   Possible causes:")
            print("     1. Webhook code hasn't been restarted with new phone extraction")
            print("     2. VAPI payloads don't contain phone number data")
            print("     3. Phone number is in a different field than expected")
            print()
            print("   Next steps:")
            print("     1. Restart your webhook server")
            print("     2. Check the raw JSON payloads in the 'json' column")
            print("     3. Make a test call and examine the payload structure")
        else:
            print(f"   - Found {calls_with_phones} calls with phone numbers - system is working!")
        
        return recent_calls
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def suggest_fixes():
    """Suggest fixes based on the analysis"""
    
    print("=== Troubleshooting Steps ===")
    print()
    print("1. RESTART YOUR WEBHOOK SERVER")
    print("   - The phone extraction code has been added")
    print("   - But your running server doesn't have the new code")
    print("   - Stop and restart your Flask/webhook application")
    print()
    print("2. CHECK VAPI CONFIGURATION")
    print("   - Make sure VAPI is sending End of Call Reports to your webhook")
    print("   - Verify the webhook URL is correct")
    print("   - Check that calls are actually triggering the webhook")
    print()
    print("3. EXAMINE PAYLOAD STRUCTURE")
    print("   - Look at the 'json' column in your sheet")
    print("   - See if phone numbers are present in the raw data")
    print("   - The phone might be in a different field than expected")
    print()
    print("4. TEST WITH A SIMPLE CALL")
    print("   - Make a test call through VAPI")
    print("   - Check if the webhook is called")
    print("   - Examine the raw JSON payload received")

if __name__ == "__main__":
    recent_calls = debug_recent_calls()
    print()
    suggest_fixes()