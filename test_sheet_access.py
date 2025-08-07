#!/usr/bin/env python3
"""
Test access to the Google Sheet with correct ID
"""

import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def test_sheet_access():
    """Test if we can access the Google Sheet"""
    
    # Load environment variables from .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    sheet_id = os.getenv('CAMPAIGN_SHEET_ID')
    sheet_name = os.getenv('CAMPAIGN_SHEET_NAME')
    
    print(f"Testing sheet access:")
    print(f"  Sheet ID: {sheet_id}")
    print(f"  Sheet Name: {sheet_name}")
    print()
    
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
        
        # Try to access the sheet
        result = service.spreadsheets().get(
            spreadsheetId=sheet_id
        ).execute()
        
        sheet_title = result['properties']['title']
        print(f"SUCCESS: Accessed sheet '{sheet_title}'")
        
        # List all sheet tabs
        sheets = result.get('sheets', [])
        print(f"\nFound {len(sheets)} sheet tabs:")
        for i, sheet in enumerate(sheets, 1):
            tab_name = sheet['properties']['title']
            tab_id = sheet['properties']['sheetId']
            print(f"  {i}. {tab_name} (ID: {tab_id})")
        
        # Check if our target sheet tab exists
        target_sheet = None
        for sheet in sheets:
            if sheet['properties']['title'] == sheet_name:
                target_sheet = sheet
                break
        
        if target_sheet:
            print(f"\n✓ Found target sheet tab: '{sheet_name}'")
        else:
            print(f"\n✗ Target sheet tab '{sheet_name}' not found")
            print("Available tabs:")
            for sheet in sheets:
                print(f"  - {sheet['properties']['title']}")
            return False
        
        # Get headers from the sheet
        range_name = f"'{sheet_name}'!1:1"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        headers = result.get('values', [[]])[0] if result.get('values') else []
        print(f"\nSheet headers ({len(headers)} columns):")
        for i, header in enumerate(headers, 1):
            print(f"  {i}. {header}")
        
        # Check if caller_phone_number column exists
        if 'caller_phone_number' in headers:
            column_index = headers.index('caller_phone_number') + 1
            print(f"\n✓ Found 'caller_phone_number' column at position {column_index}")
            print("✓ Configuration looks good!")
            return True
        else:
            print(f"\n✗ 'caller_phone_number' column not found")
            print("Please add this column to your sheet manually")
            return False
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Make sure the sheet is shared with: vapi-logs@vapi-call-log-464202.iam.gserviceaccount.com")
        print("2. Make sure the service account has 'Editor' permission")
        print("3. Check that the sheet ID and tab name are correct")
        return False

if __name__ == "__main__":
    if test_sheet_access():
        print("\n🎉 Sheet access test successful!")
        print("Your system is ready to capture caller phone numbers!")
    else:
        print("\n❌ Sheet access test failed.")
        print("Please fix the issues above and try again.")