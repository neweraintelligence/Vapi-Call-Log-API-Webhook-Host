#!/usr/bin/env python3
"""
Test the webhook endpoint with a sample VAPI payload
"""

import json
import requests
import sys
import os

def test_webhook():
    """Test the webhook with sample data"""
    
    # Sample VAPI End of Call Report payload with phone number
    test_payload = {
        "message": {
            "type": "end-of-call-report",
            "timestamp": 1751243044059,
            "call": {
                "id": "test-call-12345",
                "from": "+15551234567"  # This is the caller's phone number
            },
            "analysis": {
                "summary": "This was a test call to verify phone number extraction is working correctly.",
                "successEvaluation": "true"
            }
        }
    }
    
    print("=== Testing VAPI Webhook Phone Number Extraction ===")
    print()
    print("Test payload:")
    print(json.dumps(test_payload, indent=2))
    print()
    
    # Test the extraction function directly first
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
        from call_manager import CallManager
        
        call_manager = CallManager()
        extracted_phone = call_manager._extract_caller_phone_number(test_payload)
        
        print(f"Direct extraction test:")
        print(f"  Extracted phone number: {extracted_phone}")
        print(f"  Expected: +15551234567")
        
        if extracted_phone == "+15551234567":
            print("  ✓ Phone extraction working correctly!")
        else:
            print("  ✗ Phone extraction failed!")
            return False
        
    except Exception as e:
        print(f"Direct extraction failed: {e}")
        return False
    
    print()
    
    # Test via HTTP webhook (if server is running)
    webhook_url = "http://localhost:5000/webhook/call-summary"
    
    print(f"Testing webhook endpoint: {webhook_url}")
    
    try:
        response = requests.post(
            webhook_url,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('caller_phone_number') == '+15551234567':
                print("✓ Webhook test successful!")
                print("✓ Phone number extracted and stored!")
                return True
            else:
                print("✗ Phone number not found in response")
                return False
        else:
            print(f"✗ Webhook returned error: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to webhook server")
        print("  Make sure your Flask server is running on localhost:5000")
        return False
    except Exception as e:
        print(f"✗ Webhook test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_webhook()
    
    if success:
        print("\n🎉 All tests passed!")
        print("Your phone number extraction is working correctly!")
    else:
        print("\n❌ Tests failed.")
        print("Check the configuration and try again.")