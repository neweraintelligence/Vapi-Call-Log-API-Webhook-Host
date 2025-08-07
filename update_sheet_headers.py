#!/usr/bin/env python3
"""
Script to add caller_phone_number column to existing Google Sheet
"""

import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def update_sheet_headers():
    """Add caller_phone_number column to the existing sheet"""
    
    # Get sheet ID from the URL in your screenshot
    # The URL shows: docs.google.com/spreadsheets/d/1nFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY/edit
    spreadsheet_id = "1nFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY"
    
    # Initialize Google Sheets service
    try:
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
                raise ValueError("No Google credentials found")
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Get current sheet structure
        print("Getting current sheet structure...")
        result = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        sheets = result.get('sheets', [])
        for sheet in sheets:
            sheet_name = sheet['properties']['title']
            print(f"Found sheet: {sheet_name}")
        
        # Let's work with the first sheet (which appears to be your call logs)
        sheet_name = sheets[0]['properties']['title']
        print(f"Working with sheet: {sheet_name}")
        
        # Get current headers (row 1)
        range_name = f"{sheet_name}!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        current_headers = result.get('values', [[]])[0] if result.get('values') else []
        print(f"Current headers: {current_headers}")
        
        # Check if caller_phone_number column already exists
        if 'caller_phone_number' in current_headers:
            print("✅ caller_phone_number column already exists!")
            return
        
        # Find a good place to insert the caller_phone_number column
        # Let's insert it after any existing phone number column or at a logical spot
        insert_index = len(current_headers)  # Default to end
        
        # Look for existing phone-related columns
        for i, header in enumerate(current_headers):
            if 'phone' in header.lower():
                insert_index = i + 1
                break
        
        # Insert the new column header
        new_headers = current_headers.copy()
        new_headers.insert(insert_index, 'caller_phone_number')
        
        print(f"New headers will be: {new_headers}")
        
        # Ask for confirmation
        response = input(f"Add 'caller_phone_number' column at position {insert_index + 1}? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
        
        # Insert the new column by inserting a column and then updating headers
        # First, insert a blank column
        request_body = {
            'requests': [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheets[0]['properties']['sheetId'],
                        'dimension': 'COLUMNS',
                        'startIndex': insert_index,
                        'endIndex': insert_index + 1
                    },
                    'inheritFromBefore': False
                }
            }]
        }
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()
        
        # Now update the header row
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!1:1",
            valueInputOption='USER_ENTERED',
            body={'values': [new_headers]}
        ).execute()
        
        print("✅ Successfully added caller_phone_number column!")
        print(f"📋 Sheet ID: {spreadsheet_id}")
        print(f"📋 Sheet Name: {sheet_name}")
        print()
        print("To configure your system to use this sheet, set these environment variables:")
        print(f"CAMPAIGN_SHEET_ID={spreadsheet_id}")
        print(f"CAMPAIGN_SHEET_NAME={sheet_name}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    update_sheet_headers()