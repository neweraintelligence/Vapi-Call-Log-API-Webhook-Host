#!/usr/bin/env python3
"""
Setup configuration for the VAPI system to use your Google Sheet
"""

import os

def setup_config():
    """Setup the configuration"""
    
    print("=== VAPI Call Summary Configuration ===")
    print()
    print("After manually adding the 'caller_phone_number' column to your sheet,")
    print("you need to configure your system to use that sheet.")
    print()
    print("Please provide the following information:")
    print()
    
    # Get sheet ID from user input
    print("1. SHEET ID:")
    print("   - Go to your Google Sheet")
    print("   - Copy the URL from your browser")
    print("   - Extract the ID from: https://docs.google.com/spreadsheets/d/SHEET_ID/edit")
    print()
    sheet_id = input("Enter your Sheet ID: ").strip()
    
    if not sheet_id:
        print("No sheet ID provided. Using default configuration.")
        return False
    
    print()
    print("2. SHEET TAB NAME:")
    print("   - Look at the bottom tabs of your Google Sheet")
    print("   - Enter the name of the tab that contains your call data")
    print("   - (This is probably the first tab)")
    print()
    sheet_name = input("Enter Sheet Tab Name (or press Enter for 'Sheet1'): ").strip()
    if not sheet_name:
        sheet_name = "Sheet1"
    
    print()
    print("=== Configuration Summary ===")
    print(f"Sheet ID: {sheet_id}")
    print(f"Sheet Tab: {sheet_name}")
    print()
    
    # Create .env file content
    env_content = f"""# VAPI Call Summary Configuration
CAMPAIGN_SHEET_ID={sheet_id}
CAMPAIGN_SHEET_NAME={sheet_name}

# Your existing configuration (keep these as they are)
# VAPI_TOKEN=your_vapi_token
# VAPI_PHONE_ID=your_phone_id  
# VAPI_ASSISTANT_ID=your_assistant_id
# GOOGLE_CREDENTIALS_PATH=credentials.json
"""
    
    # Write to .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("Configuration saved to .env file!")
    print()
    print("=== Next Steps ===")
    print("1. Make sure your Google Sheet has the 'caller_phone_number' column")
    print("2. Restart your VAPI webhook system")
    print("3. Test with a call to see if phone numbers are captured")
    print()
    print("=== How to Test ===")
    print("1. Make a test call through VAPI")
    print("2. Check your Google Sheet after the call ends")
    print("3. The caller's phone number should appear in the new column")
    print()
    
    return True

if __name__ == "__main__":
    setup_config()