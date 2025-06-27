#!/usr/bin/env python3
"""
Quick test without Google Sheets - just tests the parsing logic
"""

import json
import sys
import os

# Add src to path
sys.path.append('src')

from parser import VapiCallParser

def quick_test():
    """Test just the parsing logic"""
    
    print("🧪 Quick Test - Vapi Payload Parsing")
    print("=" * 50)
    
    # Load test payload
    with open('test_payload.json', 'r') as f:
        payload = json.load(f)
    
    # Initialize parser
    parser = VapiCallParser()
    
    try:
        # Parse the payload
        parsed_data = parser.parse_call_data(payload)
        
        print("✅ Parsing successful!")
        print()
        print("📋 Parsed Data:")
        print("-" * 30)
        
        for key, value in parsed_data.items():
            if key != 'raw_payload':  # Skip the long raw payload
                print(f"{key:18}: {value}")
        
        print()
        print("🎉 Your webhook logic is working!")
        print("Ready to deploy to the cloud.")
        
        return True
        
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        return False

if __name__ == '__main__':
    quick_test() 