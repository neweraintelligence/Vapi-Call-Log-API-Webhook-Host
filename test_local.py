#!/usr/bin/env python3
"""
Local test script for the webhook endpoint
Run this to test your setup before deployment
"""

import json
import requests
import time
from src.main import app

def test_local_webhook():
    """Test the webhook endpoint locally"""
    
    # Load test payload
    with open('test_payload.json', 'r') as f:
        payload = json.load(f)
    
    print("🧪 Testing webhook endpoint locally...")
    print("=" * 50)
    
    # Start Flask app in test mode
    with app.test_client() as client:
        
        # Test health endpoint
        print("1. Testing health endpoint...")
        health_response = client.get('/health')
        print(f"   Status: {health_response.status_code}")
        print(f"   Response: {health_response.get_json()}")
        print()
        
        # Test webhook parsing (without writing to sheets)
        print("2. Testing payload parsing...")
        test_response = client.post('/test', 
                                   json=payload,
                                   headers={'Content-Type': 'application/json'})
        
        print(f"   Status: {test_response.status_code}")
        
        if test_response.status_code == 200:
            parsed_data = test_response.get_json()['parsed_data']
            print("   ✅ Parsing successful!")
            print(f"   📞 Call ID: {parsed_data['vapi_call_id']}")
            print(f"   👤 Customer: {parsed_data['Name']}")
            print(f"   📧 Email: {parsed_data['Email']}")
            print(f"   📱 Phone: {parsed_data['PhoneNumber']}")
            print(f"   🎯 Intent: {parsed_data['CallerIntent']}")
            print(f"   🚨 Priority: {parsed_data['escalation_status']}")
        else:
            print(f"   ❌ Parsing failed: {test_response.get_json()}")
        
        print()
        print("🎉 Local testing complete!")
        print("If parsing works, you're ready to deploy!")

if __name__ == '__main__':
    test_local_webhook() 