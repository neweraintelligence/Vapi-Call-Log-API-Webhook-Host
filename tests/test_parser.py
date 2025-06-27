import pytest
import json
from datetime import datetime
from src.parser import VapiCallParser

class TestVapiCallParser:
    """Test suite for VapiCallParser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = VapiCallParser()
        
        # Sample valid payload
        self.valid_payload = {
            "call": {
                "id": "call_12345",
                "created_at": "2024-01-15T10:30:00Z",
                "duration": 180,
                "status": "completed"
            },
            "summary": {
                "text": "Customer called about oil change for their 2019 Honda Civic with 45000 km. Scheduled appointment for next week."
            },
            "structured": {
                "Name": "john doe",
                "Email": "john.doe@email.com",
                "PhoneNumber": "5551234567",
                "CallerIntent": "Oil Change",
                "VehicleMake": "Honda",
                "VehicleModel": "Civic",
                "VehicleKM": "45000"
            }
        }
    
    def test_parse_valid_payload(self):
        """Test parsing a complete valid payload"""
        result = self.parser.parse_call_data(self.valid_payload)
        
        assert result['vapi_call_id'] == 'call_12345'
        assert result['Name'] == 'John Doe'  # Should be title case
        assert result['Email'] == 'john.doe@email.com'
        assert result['PhoneNumber'] == '(555) 123-4567'  # Should be formatted
        assert result['CallerIntent'] == 'Oil Change'
        assert result['VehicleMake'] == 'Honda'
        assert result['VehicleModel'] == 'Civic'
        assert result['VehicleKM'] == '45,000'
        assert result['escalation_status'] == 'Standard'
        assert len(result['follow_up_due']) == 10  # YYYY-MM-DD format
    
    def test_parse_empty_payload(self):
        """Test parsing empty or minimal payload"""
        empty_payload = {}
        result = self.parser.parse_call_data(empty_payload)
        
        assert result['vapi_call_id'] == ''
        assert result['Name'] == ''
        assert result['Email'] == ''
        assert result['CallerIntent'] == 'Unknown'
        assert result['escalation_status'] == 'Standard'
    
    def test_parse_missing_call_section(self):
        """Test payload missing call section"""
        payload = {
            "summary": {"text": "Test summary"},
            "structured": {"Name": "Test User"}
        }
        result = self.parser.parse_call_data(payload)
        
        assert result['vapi_call_id'] == ''
        assert result['Name'] == 'Test User'
        assert isinstance(result['timestamp'], str)
    
    def test_timestamp_parsing(self):
        """Test various timestamp formats"""
        # Valid ISO format
        assert '2024-01-15' in self.parser._parse_timestamp('2024-01-15T10:30:00Z')
        
        # Invalid format should return current time
        result = self.parser._parse_timestamp('invalid-timestamp')
        assert len(result) == 19  # YYYY-MM-DD HH:MM:SS format
        
        # None timestamp
        result = self.parser._parse_timestamp(None)
        assert len(result) == 19
    
    def test_name_formatting(self):
        """Test name formatting to title case"""
        assert self.parser._format_name('john doe') == 'John Doe'
        assert self.parser._format_name('MARY SMITH') == 'Mary Smith'
        assert self.parser._format_name('jean-claude van damme') == 'Jean-Claude Van Damme'
        assert self.parser._format_name('') == ''
        assert self.parser._format_name('   spaced   name   ') == 'Spaced Name'
    
    def test_email_validation(self):
        """Test email validation and formatting"""
        # Valid emails
        assert self.parser._validate_email('test@example.com') == 'test@example.com'
        assert self.parser._validate_email('User@Domain.COM') == 'user@domain.com'
        
        # Invalid emails
        assert 'INVALID:' in self.parser._validate_email('not-an-email')
        assert 'INVALID:' in self.parser._validate_email('missing@domain')
        assert 'INVALID:' in self.parser._validate_email('@missing-local.com')
        
        # Empty email
        assert self.parser._validate_email('') == ''
        assert self.parser._validate_email(None) == ''
    
    def test_phone_validation(self):
        """Test phone number validation and formatting"""
        # Valid US numbers
        assert self.parser._validate_phone('5551234567') == '(555) 123-4567'
        assert self.parser._validate_phone('15551234567') == '(555) 123-4567'
        assert self.parser._validate_phone('(555) 123-4567') == '(555) 123-4567'
        assert self.parser._validate_phone('+1-555-123-4567') == '(555) 123-4567'
        
        # Invalid numbers
        assert 'INVALID:' in self.parser._validate_phone('123')
        assert 'INVALID:' in self.parser._validate_phone('not-a-number')
        
        # Empty phone
        assert self.parser._validate_phone('') == ''
    
    def test_intent_validation(self):
        """Test caller intent validation"""
        # Valid intents (case insensitive)
        assert self.parser._validate_intent('oil change') == 'Oil Change'
        assert self.parser._validate_intent('BRAKE SERVICE') == 'Brake Service'
        assert self.parser._validate_intent('Emergency') == 'Emergency'
        
        # Unknown intent
        result = self.parser._validate_intent('Custom Intent')
        assert result == 'Custom Intent'
        
        # Empty intent
        assert self.parser._validate_intent('') == 'Unknown'
        assert self.parser._validate_intent(None) == 'Unknown'
    
    def test_numeric_parsing(self):
        """Test numeric value parsing (VehicleKM)"""
        # Valid numbers
        assert self.parser._parse_numeric('45000') == '45,000'
        assert self.parser._parse_numeric('123456') == '123,456'
        assert self.parser._parse_numeric('1,234') == '1,234'
        assert self.parser._parse_numeric(45000) == '45,000'
        
        # Edge cases
        assert self.parser._parse_numeric('0') == '0'
        assert self.parser._parse_numeric('') == ''
        assert self.parser._parse_numeric(None) == ''
        
        # Invalid numbers
        assert 'INVALID:' in self.parser._parse_numeric('not-a-number')
        
        # Out of range
        assert 'CHECK:' in self.parser._parse_numeric('9999999')
    
    def test_escalation_status_determination(self):
        """Test escalation status logic"""
        # Standard call
        standard_payload = {
            "summary": {"text": "Regular oil change inquiry"},
            "structured": {"CallerIntent": "Oil Change"}
        }
        assert self.parser._determine_escalation_status(standard_payload) == 'Standard'
        
        # High priority keywords in summary
        urgent_payload = {
            "summary": {"text": "Customer is very angry about the service"},
            "structured": {}
        }
        assert self.parser._determine_escalation_status(urgent_payload) == 'High Priority'
        
        # Emergency intent
        emergency_payload = {
            "summary": {"text": "Routine call"},
            "structured": {"CallerIntent": "Emergency"}
        }
        assert self.parser._determine_escalation_status(emergency_payload) == 'Emergency'
    
    def test_follow_up_date_calculation(self):
        """Test follow-up date calculation based on intent"""
        # Emergency - should be today
        emergency_date = self.parser._calculate_follow_up_date('Emergency')
        assert len(emergency_date) == 10  # YYYY-MM-DD format
        
        # Appointment - next day
        appointment_date = self.parser._calculate_follow_up_date('Appointment Booking')
        assert len(appointment_date) == 10
        
        # Quote - 2 days
        quote_date = self.parser._calculate_follow_up_date('Price Quote')
        assert len(quote_date) == 10
        
        # Standard - 3 days
        standard_date = self.parser._calculate_follow_up_date('General Inquiry')
        assert len(standard_date) == 10
        
        # Empty intent
        empty_date = self.parser._calculate_follow_up_date('')
        assert empty_date == ''
    
    def test_text_cleaning(self):
        """Test text cleaning and length limits"""
        # Normal text
        assert self.parser._clean_text('  Normal text  ') == 'Normal text'
        
        # Multiple spaces
        assert self.parser._clean_text('Multiple   spaces   here') == 'Multiple spaces here'
        
        # Very long text (should be truncated)
        long_text = 'x' * 2000
        result = self.parser._clean_text(long_text)
        assert len(result) <= 1000
        
        # Empty/None text
        assert self.parser._clean_text('') == ''
        assert self.parser._clean_text(None) == ''
    
    def test_error_handling(self):
        """Test error handling for malformed payloads"""
        # Non-dict payload should raise error
        with pytest.raises(Exception):
            self.parser.parse_call_data("not-a-dict")
        
        # Payload with non-string values should be handled gracefully
        weird_payload = {
            "call": {"id": 12345},  # Number instead of string
            "structured": {
                "Name": ["list", "instead", "of", "string"],
                "VehicleKM": {"nested": "dict"}
            }
        }
        
        # Should not raise exception, but convert values to strings
        result = self.parser.parse_call_data(weird_payload)
        assert result['vapi_call_id'] == '12345'
        assert isinstance(result['Name'], str)
    
    def test_payload_with_extra_fields(self):
        """Test handling payload with additional unknown fields"""
        payload_with_extras = self.valid_payload.copy()
        payload_with_extras['unknown_section'] = {'random': 'data'}
        payload_with_extras['structured']['UnknownField'] = 'unknown_value'
        
        # Should parse successfully, ignoring unknown fields
        result = self.parser.parse_call_data(payload_with_extras)
        assert result['vapi_call_id'] == 'call_12345'
        assert result['Name'] == 'John Doe'
        
        # Unknown fields should not appear in result
        assert 'UnknownField' not in result
    
    def test_special_characters_handling(self):
        """Test handling of special characters in various fields"""
        special_payload = {
            "call": {"id": "call_special_123"},
            "summary": {"text": "Customer with àccénts & spëcial chars $#@"},
            "structured": {
                "Name": "José María O'Connor-Smith",
                "Email": "test+tag@domain-name.co.uk",
                "VehicleMake": "BMW-X5",
                "VehicleModel": "330i/M-Sport"
            }
        }
        
        result = self.parser.parse_call_data(special_payload)
        
        # Should handle special characters gracefully
        assert 'José María' in result['Name']
        assert result['Email'] == 'test+tag@domain-name.co.uk'
        assert result['VehicleMake'] == 'BMW-X5'
        assert 'àccénts' in result['CallSummary']

# Integration test with realistic payloads
class TestRealisticPayloads:
    """Test with realistic Vapi webhook payloads"""
    
    def setup_method(self):
        self.parser = VapiCallParser()
    
    def test_oil_change_booking(self):
        """Test typical oil change booking call"""
        payload = {
            "call": {
                "id": "call_oil_change_001",
                "created_at": "2024-01-15T14:30:00Z",
                "duration": 145,
                "status": "completed"
            },
            "summary": {
                "text": "Customer Sarah Wilson called to schedule an oil change for her 2020 Toyota Camry with 35,000 kilometers. She's available next Tuesday morning and prefers full synthetic oil. No other services needed at this time."
            },
            "structured": {
                "Name": "sarah wilson",
                "Email": "s.wilson@email.com",
                "PhoneNumber": "416-555-0123",
                "CallerIntent": "Oil Change",
                "VehicleMake": "Toyota",
                "VehicleModel": "Camry",
                "VehicleKM": "35000"
            }
        }
        
        result = self.parser.parse_call_data(payload)
        
        assert result['vapi_call_id'] == 'call_oil_change_001'
        assert result['Name'] == 'Sarah Wilson'
        assert result['Email'] == 's.wilson@email.com'
        assert result['PhoneNumber'] == '(416) 555-0123'
        assert result['CallerIntent'] == 'Oil Change'
        assert result['VehicleKM'] == '35,000'
        assert result['escalation_status'] == 'Standard'
        assert 'Sarah Wilson' in result['CallSummary']
    
    def test_emergency_call(self):
        """Test emergency roadside assistance call"""
        payload = {
            "call": {
                "id": "call_emergency_001",
                "created_at": "2024-01-15T08:15:00Z",
                "duration": 90,
                "status": "completed"
            },
            "summary": {
                "text": "URGENT: Customer stranded on Highway 401 with flat tire. Vehicle is 2018 Ford F-150, needs immediate roadside assistance. Customer sounds stressed but is in safe location."
            },
            "structured": {
                "Name": "Mike Thompson",
                "Email": "",
                "PhoneNumber": "647-555-9999",
                "CallerIntent": "Emergency",
                "VehicleMake": "Ford",
                "VehicleModel": "F-150",
                "VehicleKM": ""
            }
        }
        
        result = self.parser.parse_call_data(payload)
        
        assert result['escalation_status'] == 'Emergency'
        assert result['CallerIntent'] == 'Emergency'
        assert 'URGENT' in result['CallSummary']
        # Follow-up should be same day for emergency
        follow_up = datetime.strptime(result['follow_up_due'], '%Y-%m-%d')
        today = datetime.now().date()
        assert follow_up.date() == today

if __name__ == '__main__':
    pytest.main([__file__]) 