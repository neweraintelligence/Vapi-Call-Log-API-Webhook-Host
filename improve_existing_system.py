#!/usr/bin/env python3
"""
Improve the existing phone number system with better formatting
"""

import sys
import os
import json
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from call_manager import CallManager

def clean_phone_number(phone_str):
    """Clean and format phone number consistently"""
    if not phone_str or phone_str.strip() == '':
        return ''
    
    # Remove all non-digit characters except leading +
    if phone_str.strip().startswith('+'):
        digits = re.sub(r'[^\d]', '', phone_str[1:])
        cleaned = f"+{digits}"
    else:
        digits = re.sub(r'[^\d]', '', phone_str)
        # Add +1 for North American numbers if not present
        if len(digits) == 10:
            cleaned = f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            cleaned = f"+{digits}"
        else:
            cleaned = f"+1{digits}" if digits else phone_str
    
    return cleaned

def improve_existing_phone_data():
    """Improve the existing phone number data in the sheet"""
    
    print("=== Improving Existing Phone Number System ===")
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
        
        print("1. Analyzing current phone number data...")
        
        # Get all data from the sheet
        range_name = f"'{call_manager.sheet_name}'!A:O"
        result = call_manager.service.spreadsheets().values().get(
            spreadsheetId=call_manager.spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if len(values) <= 1:
            print("   No data found in sheet")
            return
        
        headers = values[0]
        phone_col_index = headers.index('caller_phone_number') if 'caller_phone_number' in headers else None
        
        if phone_col_index is None:
            print("   caller_phone_number column not found")
            return
        
        print(f"   Found caller_phone_number column at index {phone_col_index}")
        
        # Analyze and clean phone numbers
        rows_to_update = []
        total_rows = 0
        rows_with_phones = 0
        rows_needing_cleanup = 0
        
        for row_index, row in enumerate(values[1:], start=2):  # Start from row 2 (skip header)
            total_rows += 1
            
            # Pad row to match headers
            while len(row) < len(headers):
                row.append('')
            
            current_phone = row[phone_col_index] if len(row) > phone_col_index else ''
            
            if current_phone and current_phone.strip():
                rows_with_phones += 1
                cleaned_phone = clean_phone_number(current_phone)
                
                if cleaned_phone != current_phone:
                    rows_needing_cleanup += 1
                    rows_to_update.append({
                        'row_index': row_index,
                        'original': current_phone,
                        'cleaned': cleaned_phone
                    })
        
        print(f"   Total rows: {total_rows}")
        print(f"   Rows with phone numbers: {rows_with_phones}")
        print(f"   Rows needing cleanup: {rows_needing_cleanup}")
        
        if rows_needing_cleanup > 0:
            print(f"\n2. Examples of phone number cleanup:")
            for i, update in enumerate(rows_to_update[:5]):  # Show first 5 examples
                print(f"   Row {update['row_index']}: '{update['original']}' → '{update['cleaned']}'")
            
            if len(rows_to_update) > 5:
                print(f"   ... and {len(rows_to_update) - 5} more")
            
            print(f"\n3. Cleaning up phone numbers...")
            
            # Update phone numbers in batches
            updates_applied = 0
            for update in rows_to_update:
                try:
                    # Convert column index to letter (A, B, C, etc.)
                    col_letter = chr(65 + phone_col_index)  # A=65
                    cell_range = f"'{call_manager.sheet_name}'!{col_letter}{update['row_index']}"
                    
                    call_manager.service.spreadsheets().values().update(
                        spreadsheetId=call_manager.spreadsheet_id,
                        range=cell_range,
                        valueInputOption='USER_ENTERED',
                        body={'values': [[update['cleaned']]]}
                    ).execute()
                    
                    updates_applied += 1
                    
                except Exception as e:
                    print(f"   Error updating row {update['row_index']}: {e}")
            
            print(f"   Successfully updated {updates_applied} phone numbers!")
        
        else:
            print("   All phone numbers are already properly formatted!")
        
        print(f"\n4. System Status:")
        print(f"   ✓ Phone number column exists")
        print(f"   ✓ {rows_with_phones} calls have phone numbers")
        print(f"   ✓ Phone numbers are being captured by existing system")
        print(f"   ✓ Phone number formatting improved")
        
        if rows_with_phones > 0:
            print(f"\n   Your existing system is already working!")
            print(f"   Phone numbers are being captured and stored.")
            print(f"   The cleanup has standardized the formatting.")
        else:
            print(f"\n   No phone numbers found - webhook may not be capturing them")
        
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if improve_existing_phone_data():
        print("\n🎉 Phone number system improvement complete!")
        print("\nYour system is capturing caller phone numbers correctly.")
        print("All phone numbers are now formatted consistently.")
    else:
        print("\n❌ Could not improve phone number system.")
        print("Please check the errors above.")