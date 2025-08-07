#!/usr/bin/env python3
"""
Manual sheet setup - asks user for sheet ID and updates it
"""

import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def manual_setup():
    """Manually ask for sheet ID and update it"""
    
    print("=== Manual Google Sheet Setup ===")
    print()
    print("Please provide your Google Sheet information:")
    print()
    
    # Get sheet ID from user
    print("1. Go to your Google Sheet")
    print("2. Copy the URL from your browser")
    print("3. The URL looks like: https://docs.google.com/spreadsheets/d/SHEET_ID/edit")
    print("4. Copy just the SHEET_ID part")
    print()
    
    sheet_id = input("Enter your Sheet ID: ").strip()
    if not sheet_id:
        print("No sheet ID provided. Exiting.")
        return False
    
    try:
        # Initialize Google Sheets service
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        
        if os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                print("ERROR: No Google credentials found")
                return False
        
        service = build('sheets', 'v4', credentials=credentials)
        
        print(f"\nAttempting to access sheet: {sheet_id}")
        
        # Try to access the sheet
        try:
            result = service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            
            sheet_title = result['properties']['title']
            print(f"SUCCESS: Accessed sheet '{sheet_title}'")
            
        except Exception as access_error:
            print(f"ERROR: Cannot access sheet: {access_error}")
            print("\nMake sure you've shared the sheet with: vapi-logs@vapi-call-log-464202.iam.gserviceaccount.com")
            return False
        
        # List available sheet tabs
        sheets = result.get('sheets', [])
        print(f"\nFound {len(sheets)} sheet tab(s):")
        for i, sheet in enumerate(sheets, 1):
            print(f"  {i}. {sheet['properties']['title']}")
        
        # Ask which sheet tab to use
        if len(sheets) == 1:
            selected_sheet = sheets[0]
            print(f"\nUsing the only sheet tab: {selected_sheet['properties']['title']}")
        else:
            try:
                choice = int(input(f"\nSelect sheet tab (1-{len(sheets)}): ")) - 1
                if 0 <= choice < len(sheets):
                    selected_sheet = sheets[choice]
                else:
                    print("Invalid choice. Using first sheet.")
                    selected_sheet = sheets[0]
            except ValueError:
                print("Invalid input. Using first sheet.")
                selected_sheet = sheets[0]
        
        sheet_name = selected_sheet['properties']['title']
        sheet_internal_id = selected_sheet['properties']['sheetId']
        
        print(f"\nWorking with sheet tab: '{sheet_name}'")
        
        # Get current headers
        range_name = f"'{sheet_name}'!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        current_headers = result.get('values', [[]])[0] if result.get('values') else []
        print(f"\nCurrent headers: {current_headers}")
        
        # Check if caller_phone_number already exists
        if 'caller_phone_number' in current_headers:
            print("\nThe 'caller_phone_number' column already exists!")
            
            # Configure environment variables anyway
            print(f"\nTo use this sheet in your system, set these environment variables:")
            print(f"CAMPAIGN_SHEET_ID={sheet_id}")
            print(f"CAMPAIGN_SHEET_NAME={sheet_name}")
            return True
        
        # Ask where to insert the column
        print(f"\nCurrent columns ({len(current_headers)} total):")
        for i, header in enumerate(current_headers, 1):
            print(f"  {i}. {header}")
        
        # Suggest insertion point
        suggested_index = len(current_headers)
        for i, header in enumerate(current_headers):
            if 'phone' in header.lower():
                suggested_index = i + 1
                break
        
        print(f"\nSuggested insertion point: position {suggested_index + 1} (after column {suggested_index})")
        
        try:
            user_choice = input(f"Insert at position (1-{len(current_headers) + 1}) or press Enter for suggested: ").strip()
            if user_choice:
                insert_index = int(user_choice) - 1
                if insert_index < 0:
                    insert_index = 0
                elif insert_index > len(current_headers):
                    insert_index = len(current_headers)
            else:
                insert_index = suggested_index
        except ValueError:
            insert_index = suggested_index
        
        print(f"\nWill insert 'caller_phone_number' at position {insert_index + 1}")
        
        # Show preview
        preview_headers = current_headers.copy()
        preview_headers.insert(insert_index, 'caller_phone_number')
        print("New header structure will be:")
        for i, header in enumerate(preview_headers, 1):
            marker = " <- NEW" if header == 'caller_phone_number' else ""
            print(f"  {i}. {header}{marker}")
        
        # Confirm
        confirm = input("\nProceed with adding the column? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return False
        
        # Insert the column
        print("\nInserting new column...")
        request_body = {
            'requests': [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_internal_id,
                        'dimension': 'COLUMNS',
                        'startIndex': insert_index,
                        'endIndex': insert_index + 1
                    },
                    'inheritFromBefore': False
                }
            }]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body=request_body
        ).execute()
        
        # Update headers
        print("Updating headers...")
        new_headers = current_headers.copy()
        new_headers.insert(insert_index, 'caller_phone_number')
        
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{sheet_name}'!1:1",
            valueInputOption='USER_ENTERED',
            body={'values': [new_headers]}
        ).execute()
        
        print("\n" + "="*50)
        print("SUCCESS! Added 'caller_phone_number' column!")
        print("="*50)
        print(f"Sheet ID: {sheet_id}")
        print(f"Sheet Name: {sheet_name}")
        print(f"Column added at position: {insert_index + 1}")
        
        print(f"\nTo configure your VAPI system to use this sheet:")
        print(f"1. Set environment variable: CAMPAIGN_SHEET_ID={sheet_id}")
        print(f"2. Set environment variable: CAMPAIGN_SHEET_NAME={sheet_name}")
        print(f"3. Restart your VAPI webhook system")
        print(f"\nNow when VAPI sends end-of-call reports, the caller's phone number")
        print(f"will be extracted and stored in the 'caller_phone_number' column!")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    manual_setup()