#!/usr/bin/env python3
"""
Debug script to examine Vapi payload structure
"""

def debug_payload_structure():
    """Debug the actual payload structure from your log"""
    
    # This is the raw payload from your log (truncated)
    sample_payload = {
        'message': {
            'timestamp': 1751243044059,
            'type': 'end-of-call-report',
            'analysis': {
                'summary': 'This call was a brief interaction where the user stated they were "just testing" the virtual assistant. No customer name, contact information, services of interest, or appointment details were provided. No specific questions or requests were made beyond the testing comment. The call was not transferred, and no message was left; the customer ended the call.',
                'successEvaluation': 'false'
            },
            'artifact': '...'  # truncated
        }
    }
    
    print("=== Debugging Payload Structure ===")
    print()
    
    # Check if it's nested message format
    if sample_payload.get('message', {}).get('type') == 'end-of-call-report':
        print("✅ Detected nested message format")
        message = sample_payload.get('message', {})
        
        # Look for call data in different possible locations
        print("\n=== Looking for call data ===")
        
        # Check if call data is in the message
        if 'call' in message:
            call_data = message['call']
            print(f"Found call data in message.call: {call_data}")
        else:
            print("❌ No call data found in message.call")
        
        # Check if call data is at the root level
        if 'call' in sample_payload:
            call_data = sample_payload['call']
            print(f"Found call data at root level: {call_data}")
        else:
            print("❌ No call data found at root level")
        
        # Check for phone number in different possible locations
        print("\n=== Looking for phone number ===")
        
        # Check message.call.from
        if 'call' in message and 'from' in message['call']:
            print(f"✅ Phone number found in message.call.from: {message['call']['from']}")
        else:
            print("❌ No phone number in message.call.from")
        
        # Check root level call.from
        if 'call' in sample_payload and 'from' in sample_payload['call']:
            print(f"✅ Phone number found in root call.from: {sample_payload['call']['from']}")
        else:
            print("❌ No phone number in root call.from")
        
        # Check for other possible phone number fields
        print("\n=== Checking other possible phone fields ===")
        for key, value in message.items():
            if 'phone' in key.lower() or 'from' in key.lower():
                print(f"Found potential phone field '{key}': {value}")
        
        # Check analysis for structured data
        analysis = message.get('analysis', {})
        if 'structuredData' in analysis:
            print(f"\n✅ Found structured data: {analysis['structuredData']}")
        else:
            print("\n❌ No structured data found in analysis")
    
    print("\n=== Recommendation ===")
    print("The payload seems to be missing the call metadata (like 'from' phone number).")
    print("This could be because:")
    print("1. The call was a test call without real phone metadata")
    print("2. The payload structure is different than expected")
    print("3. The phone number is in a different field name")
    print()
    print("To debug further, you can:")
    print("1. Check the full raw payload in your logs")
    print("2. Make a real call (not a test) to see if phone data appears")
    print("3. Check Vapi documentation for the exact payload structure")

if __name__ == "__main__":
    debug_payload_structure() 