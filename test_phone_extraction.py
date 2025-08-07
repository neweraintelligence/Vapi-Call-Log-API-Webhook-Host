#!/usr/bin/env python3
"""
Test script for phone number extraction functionality
"""

import sys
import os
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from call_manager import CallManager

def test_phone_extraction():
    """Test various phone number extraction scenarios"""
    
    call_manager = CallManager()
    
    # Test case 1: Phone number in message.call.from
    test_payload_1 = {
        'message': {
            'type': 'end-of-call-report',
            'call': {
                'id': 'test-call-id-1',
                'from': '+15551234567'
            },
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    # Test case 2: Phone number in call.from (root level)
    test_payload_2 = {
        'call': {
            'id': 'test-call-id-2',
            'from': '+15557654321'
        },
        'message': {
            'type': 'end-of-call-report',
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    # Test case 3: Phone number in message.call.customer.number
    test_payload_3 = {
        'message': {
            'type': 'end-of-call-report',
            'call': {
                'id': 'test-call-id-3',
                'customer': {
                    'number': '+15558765432'
                }
            },
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    # Test case 4: Phone number in artifact (JSON string)
    test_payload_4 = {
        'message': {
            'type': 'end-of-call-report',
            'call': {
                'id': 'test-call-id-4'
            },
            'artifact': '{"from": "+15559876543", "other_data": "test"}',
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    # Test case 5: Phone number in artifact (dict)
    test_payload_5 = {
        'message': {
            'type': 'end-of-call-report',
            'call': {
                'id': 'test-call-id-5'
            },
            'artifact': {
                'caller_number': '+15551928374',
                'other_data': 'test'
            },
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    # Test case 6: No phone number found
    test_payload_6 = {
        'message': {
            'type': 'end-of-call-report',
            'call': {
                'id': 'test-call-id-6'
            },
            'analysis': {
                'summary': 'Test call summary'
            }
        }
    }
    
    test_cases = [
        ("message.call.from", test_payload_1, "+15551234567"),
        ("root call.from", test_payload_2, "+15557654321"),
        ("message.call.customer.number", test_payload_3, "+15558765432"),
        ("artifact JSON string", test_payload_4, "+15559876543"),
        ("artifact dict", test_payload_5, "+15551928374"),
        ("no phone number", test_payload_6, None)
    ]
    
    print("=== Testing Phone Number Extraction ===\n")
    
    all_passed = True
    
    for test_name, payload, expected in test_cases:
        print(f"Testing: {test_name}")
        result = call_manager._extract_caller_phone_number(payload)
        
        if result == expected:
            print(f"  PASS: Found '{result}' (expected: '{expected}')")
        else:
            print(f"  FAIL: Found '{result}' (expected: '{expected}')")
            all_passed = False
        print()
    
    # Test phone number formatting
    print("=== Testing Phone Number Formatting ===\n")
    
    format_test_cases = [
        ("+1 (555) 123-4567", "+15551234567"),
        ("555-123-4567", "+5551234567"),
        ("1-555-123-4567", "+15551234567"),
        ("+15551234567", "+15551234567"),
        ("(555) 123-4567", "+5551234567")
    ]
    
    for input_phone, expected_output in format_test_cases:
        result = call_manager._format_caller_phone_number(input_phone)
        print(f"Input: '{input_phone}' -> Output: '{result}' (Expected: '{expected_output}')")
        
        if result == expected_output:
            print("  PASS")
        else:
            print("  FAIL")
            all_passed = False
        print()
    
    if all_passed:
        print("All tests passed!")
    else:
        print("Some tests failed. Please check the implementation.")
    
    return all_passed

if __name__ == "__main__":
    test_phone_extraction()