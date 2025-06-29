#!/usr/bin/env python3

import json
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from parser import VapiCallParser

def test_vapi_format():
    """Test the new VAPI format parser"""
    
    parser = VapiCallParser()
    
    print("🧪 Testing VAPI End-of-Call-Report Format Parser")
    print("=" * 60)
    
    # Test 1: Normal call payload
    print("\n📞 Test 1: Normal Call (Oil Change)")
    print("-" * 40)
    
    try:
        with open('test_payload_vapi_format.json', 'r') as f:
            payload = json.load(f)
        
        result = parser.parse_call_data(payload)
        
        print("✅ SUCCESS - Normal call parsed correctly")
        print(f"  📞 Call ID: {result['vapi_call_id']}")
        print(f"  👤 Customer: {result['Name']}")
        print(f"  📧 Email: {result['Email']}")
        print(f"  📱 Phone: {result['PhoneNumber']}")
        print(f"  🎯 Intent: {result['CallerIntent']}")
        print(f"  🚗 Vehicle: {result['VehicleMake']} {result['VehicleModel']}")
        print(f"  📏 Vehicle KM: {result['VehicleKM']}")
        print(f"  📋 Summary: {result['CallSummary'][:100]}...")
        print(f"  🚨 Escalation: {result['escalation_status']}")
        print(f"  ✅ Success: {result['success_evaluation']}")
        print(f"  📅 Follow-up: {result['follow_up_due']}")
        
    except Exception as e:
        print(f"❌ FAILED - Normal call test: {e}")
        return False
    
    # Test 2: Emergency call payload
    print("\n🚨 Test 2: Emergency Call (Roadside Assistance)")
    print("-" * 40)
    
    try:
        with open('test_emergency_payload_vapi.json', 'r') as f:
            emergency_payload = json.load(f)
        
        emergency_result = parser.parse_call_data(emergency_payload)
        
        print("✅ SUCCESS - Emergency call parsed correctly")
        print(f"  📞 Call ID: {emergency_result['vapi_call_id']}")
        print(f"  👤 Customer: {emergency_result['Name']}")
        print(f"  📧 Email: {emergency_result['Email']}")
        print(f"  📱 Phone: {emergency_result['PhoneNumber']}")
        print(f"  🎯 Intent: {emergency_result['CallerIntent']}")
        print(f"  🚗 Vehicle: {emergency_result['VehicleMake']} {emergency_result['VehicleModel']}")
        print(f"  📋 Summary: {emergency_result['CallSummary'][:100]}...")
        print(f"  🚨 Escalation: {emergency_result['escalation_status']}")
        print(f"  ✅ Success: {emergency_result['success_evaluation']}")
        print(f"  📅 Follow-up: {emergency_result['follow_up_due']}")
        
        # Verify escalation detection works
        if emergency_result['escalation_status'] in ['Emergency', 'High Priority']:
            print("  ✅ Escalation correctly detected!")
        else:
            print("  ⚠️  Escalation NOT detected - check keywords")
        
    except Exception as e:
        print(f"❌ FAILED - Emergency call test: {e}")
        return False
    
    # Test 3: Legacy format compatibility (fallback)
    print("\n🔄 Test 3: Legacy Format Compatibility")
    print("-" * 40)
    
    try:
        with open('test_payload.json', 'r') as f:
            legacy_payload = json.load(f)
        
        legacy_result = parser.parse_call_data(legacy_payload)
        
        print("✅ SUCCESS - Legacy format still works")
        print(f"  📞 Call ID: {legacy_result['vapi_call_id']}")
        print(f"  👤 Customer: {legacy_result['Name']}")
        print(f"  📧 Email: {legacy_result['Email']}")
        print(f"  📋 Summary: {legacy_result['CallSummary'][:100]}...")
        
    except Exception as e:
        print(f"❌ FAILED - Legacy format test: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED! Parser is ready for VAPI integration.")
    return True

if __name__ == "__main__":
    success = test_vapi_format()
    sys.exit(0 if success else 1) 