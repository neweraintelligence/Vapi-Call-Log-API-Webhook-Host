#!/usr/bin/env python3
"""
Script to find and list accessible Google Sheets
"""

import os
import sys
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def find_accessible_sheets():
    """Find Google Sheets that the service account can access"""
    
    try:
        # Initialize Google Sheets service
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        
        if os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']
            )
        else:
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_info = json.loads(creds_json)
                credentials = service_account.Credentials.from_service_account_info(
                    creds_info,
                    scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                raise ValueError("No Google credentials found")
        
        # Try to access Drive API to list spreadsheets
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
            
            # Search for Google Sheets files
            results = drive_service.files().list(
                q="mimeType='application/vnd.google-apps.spreadsheet'",
                pageSize=20,
                fields="nextPageToken, files(id, name, webViewLink)"
            ).execute()
            
            files = results.get('files', [])
            
            if files:
                print("Found accessible Google Sheets:")
                print("=" * 50)
                for i, file in enumerate(files, 1):
                    print(f"{i}. Name: {file['name']}")
                    print(f"   ID: {file['id']}")
                    print(f"   URL: {file.get('webViewLink', 'N/A')}")
                    print()
                
                return files
            else:
                print("No Google Sheets found that the service account can access.")
                return []
                
        except Exception as drive_error:
            print(f"Could not access Drive API: {drive_error}")
            print("Trying direct sheet access instead...")
            
            # If Drive API doesn't work, let's try some common sheet IDs
            # or ask the user to provide one
            sheets_service = build('sheets', 'v4', credentials=credentials)
            
            print("\nPlease provide the Google Sheet ID manually.")
            print("You can find it in the URL: docs.google.com/spreadsheets/d/SHEET_ID/edit")
            sheet_id = input("Enter Sheet ID: ").strip()
            
            if sheet_id:
                try:
                    result = sheets_service.spreadsheets().get(
                        spreadsheetId=sheet_id
                    ).execute()
                    
                    print(f"Successfully accessed sheet: {result['properties']['title']}")
                    return [{'id': sheet_id, 'name': result['properties']['title']}]
                    
                except Exception as sheet_error:
                    print(f"Could not access sheet {sheet_id}: {sheet_error}")
                    return []
            
            return []
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def update_specific_sheet(sheet_id, sheet_name=None):
    """Update a specific sheet with the caller_phone_number column"""
    
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
                raise ValueError("No Google credentials found")
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Get sheet info
        result = service.spreadsheets().get(
            spreadsheetId=sheet_id
        ).execute()
        
        sheets = result.get('sheets', [])
        
        # Use provided sheet name or first sheet
        target_sheet = None
        if sheet_name:
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    target_sheet = sheet
                    break
        
        if not target_sheet:
            target_sheet = sheets[0]  # Use first sheet
        
        sheet_title = target_sheet['properties']['title']
        sheet_id_internal = target_sheet['properties']['sheetId']
        
        print(f"Working with sheet: {sheet_title}")
        
        # Get current headers
        range_name = f"{sheet_title}!1:1"
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
        
        # Find insertion point (after any phone column, or at end)
        insert_index = len(current_headers)
        for i, header in enumerate(current_headers):
            if 'phone' in header.lower():
                insert_index = i + 1
                break
        
        print(f"Will insert 'caller_phone_number' at position {insert_index + 1}")
        
        # Insert column
        request_body = {
            'requests': [{
                'insertDimension': {
                    'range': {
                        'sheetId': sheet_id_internal,
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
        new_headers = current_headers.copy()
        new_headers.insert(insert_index, 'caller_phone_number')
        
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{sheet_title}!1:1",
            valueInputOption='USER_ENTERED',
            body={'values': [new_headers]}
        ).execute()
        
        print("Successfully added caller_phone_number column!")
        print(f"Sheet ID: {sheet_id}")
        print(f"Sheet Name: {sheet_title}")
        
        return True
        
    except Exception as e:
        print(f"Error updating sheet: {str(e)}")
        return False

if __name__ == "__main__":
    print("Finding accessible Google Sheets...")
    sheets = find_accessible_sheets()
    
    if sheets:
        print("\nSelect a sheet to update:")
        for i, sheet in enumerate(sheets, 1):
            print(f"{i}. {sheet['name']} (ID: {sheet['id']})")
        
        try:
            choice = int(input("Enter choice (number): ")) - 1
            if 0 <= choice < len(sheets):
                selected_sheet = sheets[choice]
                print(f"\nUpdating sheet: {selected_sheet['name']}")
                success = update_specific_sheet(selected_sheet['id'])
                
                if success:
                    print(f"\nTo configure your system, set these environment variables:")
                    print(f"CAMPAIGN_SHEET_ID={selected_sheet['id']}")
                    print(f"CAMPAIGN_SHEET_NAME={selected_sheet['name']}")
            else:
                print("Invalid choice")
        except (ValueError, IndexError):
            print("Invalid input")
    else:
        print("No sheets found or accessible.")