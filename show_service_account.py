#!/usr/bin/env python3
"""
Show the service account email that needs access to Google Sheets
"""

import os
import json

def show_service_account_email():
    """Display the service account email"""
    
    try:
        credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        
        if os.path.exists(credentials_path):
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
        else:
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_json:
                creds_data = json.loads(creds_json)
            else:
                print("ERROR: No Google credentials found")
                print("Make sure GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON is set")
                return
        
        service_account_email = creds_data.get('client_email', 'Not found')
        project_id = creds_data.get('project_id', 'Not found')
        
        print("=== Google Service Account Info ===")
        print(f"Service Account Email: {service_account_email}")
        print(f"Project ID: {project_id}")
        print()
        print("=== Next Steps ===")
        print("1. Copy the service account email above")
        print("2. Open your Google Sheet: https://docs.google.com/spreadsheets/d/1nFsqGTf90C6Yl2lW69_mZLJLKQ2NVKxlDtxuy3u2SoY/edit")
        print("3. Click the 'Share' button")
        print("4. Paste the service account email")
        print("5. Set permission to 'Editor'")
        print("6. Uncheck 'Notify people'")
        print("7. Click 'Share'")
        print("8. Then run the update script again")
        
    except Exception as e:
        print(f"Error reading credentials: {str(e)}")

if __name__ == "__main__":
    show_service_account_email()