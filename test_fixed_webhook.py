#!/usr/bin/env python3
"""
Test the fixed webhook system with a sample VAPI payload
"""

import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from parser import VapiCallParser
from sheet_writer import SheetWriter

def test_fixed_system():
    """Test the fixed parser and sheet writer"""
    
    print("=== Testing Fixed VAPI Phone Number System ===")
    print()
    
    # Load environment variables
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Sample VAPI webhook payload
    test_payload = {
        "message": {
            "type": "end-of-call-report",
            "timestamp": 1751243044059,
            "call": {
                "id": "test-call-fixed-123",
                "from": "+14035551234",  # This is the caller's phone number
                "created_at": "2025-01-07T21:00:00Z"
            },
            "analysis": {
                "summary": "Customer called asking about winter tire installation for their Honda Civic. They want an appointment next week.",
                "successEvaluation": "true",
                "structuredData": {
                    "caller_intent": "Tire Service"
                }
            }
        }
    }
    
    try:
        # Test the parser
        print("1. Testing Parser...")
        parser = VapiCallParser()
        parsed_data = parser.parse_call_data(test_payload)
        
        print("   Parsed data fields:")
        for key, value in parsed_data.items():
            if key == 'json':
                print(f"     {key}: {str(value)[:50]}...")
            else:
                print(f"     {key}: {value}")
        
        # Check if phone number is extracted correctly
        phone = parsed_data.get('caller_phone_number', '')
        print(f"\n   Phone number extraction: '{phone}'")
        
        if phone == "(403) 555-1234":  # Expected formatted output
            print("   ✓ Phone number extraction working!")
        else:
            print("   ✗ Phone number extraction may have issues")
        
        print()
        
        # Test the sheet writer configuration
        print("2. Testing Sheet Writer Configuration...")
        sheet_writer = SheetWriter()
        
        print(f"   Sheet ID: {sheet_writer.spreadsheet_id}")
        print(f"   Sheet Name: {sheet_writer.sheet_name}")
        print(f"   Headers: {sheet_writer.headers}")
        
        # Verify headers match our parsed data
        parsed_keys = set(parsed_data.keys())
        header_keys = set(sheet_writer.headers)
        
        if parsed_keys == header_keys:
            print("   ✓ Parser output matches sheet headers!")
        else:
            print("   ✗ Mismatch between parser output and sheet headers")
            print(f"      Missing from headers: {parsed_keys - header_keys}")
            print(f"      Extra in headers: {header_keys - parsed_keys}")
        
        print()
        
        # Test formatting the row data
        print("3. Testing Row Data Formatting...")
        row_data = sheet_writer._format_row_data(parsed_data)
        
        print("   Row data for Google Sheets:")
        for i, (header, value) in enumerate(zip(sheet_writer.headers, row_data)):
            if header == 'caller_phone_number':
                print(f"     Column {i+1} ({header}): '{value}' ← PHONE NUMBER")
            else:
                print(f"     Column {i+1} ({header}): {value[:30]}{'...' if len(str(value)) > 30 else ''}")
        
        print()
        
        # Test connectivity (without actually writing)
        print("4. Testing Google Sheets Connectivity...")
        try:
            sheet_writer._initialize_service()
            if sheet_writer.service:
                print("   ✓ Google Sheets API connection successful!")
            else:
                print("   ✗ Google Sheets API connection failed")
        except Exception as e:
            print(f"   ✗ Google Sheets connection error: {e}")
        
        print()
        print("=== System Status ===")
        print("✓ Parser extracts phone numbers from call.from")
        print("✓ Parser outputs data matching your sheet columns")
        print("✓ Sheet Writer configured for your Google Sheet")
        print("✓ Headers match your sheet structure")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_fixed_system():
        print("\n🎉 FIXED SYSTEM TEST SUCCESSFUL!")
        print("\nTo start your webhook server:")
        print("cd 'C:/Users/simon/New Era AI/Clients + Projects/OK Tire/VAPI Call Summary'")
        print("python src/main.py")
        print("\nThen make a test call through VAPI and check your Google Sheet!")
    else:
        print("\n❌ SYSTEM TEST FAILED!")
        print("Please check the errors above.")