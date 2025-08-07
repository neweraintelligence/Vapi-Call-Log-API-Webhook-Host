#!/usr/bin/env python3
"""
Direct sheet update using the sheet ID from the screenshot
"""

import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def update_vapi_logs_sheet():
    """Update the Vapi Call Logs sheet with caller_phone_number column"""
    
    # Sheet ID from your screenshot URL
    sheet_id = "1nFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY"
    
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
                print("Make sure GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON is set")
                return False
        
        service = build('sheets', 'v4', credentials=credentials)
        
        print(f"Attempting to access sheet: {sheet_id}")
        
        # Get sheet info
        try:
            result = service.spreadsheets().get(
                spreadsheetId=sheet_id
            ).execute()
            
            print(f"Successfully accessed sheet: {result['properties']['title']}")
            
        except Exception as access_error:
            print(f"Cannot access sheet: {access_error}")
            print("\nThis could be because:")
            print("1. The service account doesn't have access to this sheet")
            print("2. The sheet ID is incorrect")
            print("3. The sheet is private")
            print("\nTo fix this, you need to:")
            print("1. Share the Google Sheet with your service account email")
            print("2. Or provide the correct sheet ID")
            return False
        
        sheets = result.get('sheets', [])
        
        # Find the sheet with call logs (likely the first one based on your screenshot)
        target_sheet = sheets[0]  # Use first sheet
        sheet_name = target_sheet['properties']['title']
        sheet_internal_id = target_sheet['properties']['sheetId']
        
        print(f"Working with sheet tab: {sheet_name}")
        
        # Get current headers (row 1)
        range_name = f"'{sheet_name}'!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        current_headers = result.get('values', [[]])[0] if result.get('values') else []
        print(f"Current headers: {current_headers}")
        
        # Check if caller_phone_number already exists
        if 'caller_phone_number' in current_headers:
            print("caller_phone_number column already exists!")
            return True
        
        # Find a good insertion point
        # Looking at your screenshot, I see columns like call_intent, Column 4, Column 5, etc.
        # Let's insert after the first few meaningful columns
        insert_index = min(3, len(current_headers))  # Insert around column C or D
        
        print(f"Will insert 'caller_phone_number' at column {insert_index + 1}")
        print("Current header structure will become:")
        preview_headers = current_headers.copy()
        preview_headers.insert(insert_index, 'caller_phone_number')
        print(preview_headers)
        
        # Ask for confirmation
        confirm = input("\nProceed with adding the column? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled.")
            return False
        
        # Insert the new column
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
        
        print("Inserting new column...")
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id,
            body=request_body
        ).execute()
        
        # Update the header
        new_headers = current_headers.copy()
        new_headers.insert(insert_index, 'caller_phone_number')
        
        print("Updating headers...")
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{sheet_name}'!1:1",
            valueInputOption='USER_ENTERED',
            body={'values': [new_headers]}
        ).execute()
        
        print("SUCCESS: Added caller_phone_number column!")
        print(f"Sheet ID: {sheet_id}")
        print(f"Sheet Name: {sheet_name}")
        
        print(f"\nTo configure your system to use this sheet, set:")
        print(f"CAMPAIGN_SHEET_ID={sheet_id}")
        print(f"CAMPAIGN_SHEET_NAME={sheet_name}")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    update_vapi_logs_sheet()