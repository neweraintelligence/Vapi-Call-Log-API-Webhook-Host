#!/usr/bin/env python3
"""
Test script for multi-agent VAPI call log system
"""

import os
import json
import requests
from datetime import datetime

# Test payloads for different agents
AGENT1_TEST_PAYLOAD = {
    "type": "end-of-call-report",
    "call": {
        "id": "test-call-agent1-123",
        "assistant": {
            "id": "agent1_test_id"  # This should match your AGENT1_ID
        }
    },
    "analysis": {
        "summary": "Test call for Agent 1",
        "structured_data": {
            "Name": "John Doe",
            "Email": "john@example.com",
            "PhoneNumber": "555-1234"
        },
        "success": True
    }
}

AGENT2_TEST_PAYLOAD = {
    "type": "end-of-call-report", 
    "call": {
        "id": "test-call-agent2-456",
        "assistant": {
            "id": "agent2_test_id"  # This should match your AGENT2_ID
        }
    },
    "analysis": {
        "summary": "Test call for Agent 2",
        "structured_data": {
            "Name": "Jane Smith",
            "Email": "jane@example.com", 
            "PhoneNumber": "555-5678"
        },
        "success": True
    }
}

def test_webhook_endpoint():
    """Test the webhook endpoint with both agent payloads"""
    webhook_url = "https://vapi-call-log.onrender.com/webhook"
    
    print("Testing multi-agent webhook system...")
    print(f"Webhook URL: {webhook_url}")
    print("-" * 50)
    
    # Test Agent 1
    print("Testing Agent 1 payload...")
    try:
        response = requests.post(webhook_url, json=AGENT1_TEST_PAYLOAD, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"Error testing Agent 1: {e}")
        print()
    
    # Test Agent 2
    print("Testing Agent 2 payload...")
    try:
        response = requests.post(webhook_url, json=AGENT2_TEST_PAYLOAD, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        print()
    except Exception as e:
        print(f"Error testing Agent 2: {e}")
        print()

def test_health_endpoint():
    """Test the health endpoint"""
    health_url = "https://vapi-call-log.onrender.com/health"
    
    print("Testing health endpoint...")
    print(f"Health URL: {health_url}")
    print("-" * 50)
    
    try:
        response = requests.get(health_url, timeout=30)
        print(f"Status Code: {response.status_code}")
        health_data = response.json()
        print(f"Service: {health_data.get('service')}")
        print(f"Status: {health_data.get('status')}")
        print(f"Agents Configured: {health_data.get('agents_configured')}")
        
        if 'google_sheets' in health_data:
            sheets_health = health_data['google_sheets']
            print(f"Google Sheets Status: {sheets_health.get('status')}")
            if 'sheets' in sheets_health:
                for agent, sheet_info in sheets_health['sheets'].items():
                    print(f"  {agent}: {sheet_info.get('status')} - {sheet_info.get('title', 'Unknown')}")
        print()
    except Exception as e:
        print(f"Error testing health endpoint: {e}")
        print()

def main():
    """Main test function"""
    print("VAPI Multi-Agent Call Log System Test")
    print("=" * 50)
    print()
    
    # Test health first
    test_health_endpoint()
    
    # Test webhook
    test_webhook_endpoint()
    
    print("Test completed!")
    print("\nNext steps:")
    print("1. Check your Google Sheets to see if test data was written")
    print("2. Verify the data went to the correct sheets for each agent")
    print("3. Update the agent IDs in the test payloads to match your actual VAPI agent IDs")

if __name__ == "__main__":
    main() 