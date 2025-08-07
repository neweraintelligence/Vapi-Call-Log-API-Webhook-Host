#!/usr/bin/env python3
"""
Direct update using the sheet ID from the screenshot URL
"""

import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Try different possible sheet IDs based on URL patterns
possible_sheet_ids = [
    "1nFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY",  # From screenshot URL
    "1rnFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY",  # In case first char is different
]

def try_update_sheet():
    """Try to update the sheet with different possible IDs"""
    
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
        
        # Try each possible sheet ID
        for sheet_id in possible_sheet_ids:
            print(f"Trying sheet ID: {sheet_id}")
            
            try:
                result = service.spreadsheets().get(
                    spreadsheetId=sheet_id
                ).execute()
                
                sheet_title = result['properties']['title']
                print(f"SUCCESS: Found sheet '{sheet_title}'")
                
                # Work with this sheet
                return update_sheet_with_caller_column(service, sheet_id, result)
                
            except Exception as e:
                print(f"  Failed: {str(e)}")
                continue
        
        print("\nCould not access any sheet with the tried IDs.")
        print("Please check:")
        print("1. The sheet URL is correct")
        print("2. You've shared the sheet with: vapi-logs@vapi-call-log-464202.iam.gserviceaccount.com")
        print("3. The service account has 'Editor' permission")
        
        return False
        
    except Exception as e:
        print(f"Service initialization error: {str(e)}")
        return False

def update_sheet_with_caller_column(service, sheet_id, sheet_info):
    """Update the sheet with caller_phone_number column"""
    
    try:
        sheets = sheet_info.get('sheets', [])
        if not sheets:
            print("No sheet tabs found")
            return False
        
        # Use the first sheet tab
        target_sheet = sheets[0]
        sheet_name = target_sheet['properties']['title']
        sheet_internal_id = target_sheet['properties']['sheetId']
        
        print(f"Working with sheet tab: '{sheet_name}'")
        
        # Get current headers
        range_name = f"'{sheet_name}'!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        current_headers = result.get('values', [[]])[0] if result.get('values') else []
        print(f"Current headers ({len(current_headers)} columns): {current_headers}")
        
        # Check if caller_phone_number already exists
        if 'caller_phone_number' in current_headers:
            print("Column 'caller_phone_number' already exists!")
            print_config_instructions(sheet_id, sheet_name)
            return True
        
        # Find insertion point - insert after column 3 (seems like a good spot based on your sheet)
        insert_index = min(3, len(current_headers))
        
        print(f"Will insert 'caller_phone_number' at position {insert_index + 1}")
        
        # Preview the change
        preview_headers = current_headers.copy()
        preview_headers.insert(insert_index, 'caller_phone_number')
        print("New header structure:")
        for i, header in enumerate(preview_headers, 1):
            marker = " <- NEW" if header == 'caller_phone_number' else ""
            print(f"  {i}. {header}{marker}")
        
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
        print("Updating column header...")
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{sheet_name}'!{chr(65 + insert_index)}1",  # Convert index to column letter
            valueInputOption='USER_ENTERED',
            body={'values': [['caller_phone_number']]}
        ).execute()
        
        print("\n" + "="*60)
        print("SUCCESS! Added 'caller_phone_number' column to your sheet!")
        print("="*60)
        
        print_config_instructions(sheet_id, sheet_name)
        
        return True
        
    except Exception as e:
        print(f"Error updating sheet: {str(e)}")
        return False

def print_config_instructions(sheet_id, sheet_name):
    """Print configuration instructions"""
    print(f"\nSheet Details:")
    print(f"  ID: {sheet_id}")
    print(f"  Tab: {sheet_name}")
    
    print(f"\nTo configure your VAPI system:")
    print(f"1. Set: CAMPAIGN_SHEET_ID={sheet_id}")
    print(f"2. Set: CAMPAIGN_SHEET_NAME={sheet_name}")
    print(f"3. Restart your webhook system")
    print(f"\nNow your system will capture caller phone numbers from VAPI end-of-call reports!")

if __name__ == "__main__":
    try_update_sheet()