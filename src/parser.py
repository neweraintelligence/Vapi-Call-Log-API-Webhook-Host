import re
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class VapiCallParser:
    """
    Parses Vapi webhook payloads into flat dictionaries suitable for Google Sheets
    """
    
    def __init__(self):
        # Phone number regex pattern
        self.phone_pattern = re.compile(r'^\+?1?\d{10,14}$')
        
        # Email regex pattern
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def parse_call_data(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Vapi webhook payload into flat dictionary
        
        Args:
            payload: Raw Vapi webhook JSON payload (end-of-call-report format)
            
        Returns:
            Flat dictionary with standardized column names
        """
        try:
            # Handle both direct payload and nested message formats
            if payload.get('type') == 'end-of-call-report':
                # Direct format
                call_data = payload.get('call', {})
                analysis_data = payload.get('analysis', {})
            elif payload.get('message', {}).get('type') == 'end-of-call-report':
                # Nested message format
                message = payload.get('message', {})
                call_data = message.get('call', {})
                analysis_data = message.get('analysis', {})
            else:
                # Legacy format (fallback)
                call_data = payload.get('call', {})
                analysis_data = {
                    'summary': payload.get('summary', {}).get('text', ''),
                    'structuredData': payload.get('structured', {})
                }
            
            # Extract structured data from analysis
            summary_text = analysis_data.get('summary', '')
            structured_data = analysis_data.get('structuredData', {})
            success_evaluation = analysis_data.get('successEvaluation', '')
            
            # Extract and validate core fields
            parsed = {
                # Core identifiers
                'vapi_call_id': self._safe_get(call_data, 'id', ''),
                'timestamp': self._parse_timestamp(call_data.get('created_at')),
                
                # Call summary from analysis
                'CallSummary': self._clean_text(summary_text),
                
                # Structured customer data from analysis
                'Name': self._format_name(structured_data.get('customer_name', structured_data.get('Name', ''))),
                'Email': self._validate_email(structured_data.get('customer_email', structured_data.get('Email', ''))),
                'PhoneNumber': self._validate_phone(structured_data.get('customer_phone', structured_data.get('PhoneNumber', ''))),
                
                # Call intent and vehicle info
                'CallerIntent': self._validate_intent(structured_data.get('caller_intent', structured_data.get('CallerIntent', ''))),
                'VehicleMake': self._clean_text(structured_data.get('vehicle_make', structured_data.get('VehicleMake', ''))),
                'VehicleModel': self._clean_text(structured_data.get('vehicle_model', structured_data.get('VehicleModel', ''))),
                'VehicleKM': self._parse_numeric(structured_data.get('vehicle_km', structured_data.get('VehicleKM'))),
                
                # Operational fields
                'escalation_status': self._determine_escalation_status(summary_text, structured_data),
                'follow_up_due': self._calculate_follow_up_date(structured_data.get('caller_intent', structured_data.get('CallerIntent', ''))),
                
                # Additional metadata
                'call_duration': call_data.get('duration', 0),
                'call_status': call_data.get('status', 'unknown'),
                'success_evaluation': str(success_evaluation),
                'raw_payload': str(payload)[:500]  # Truncated raw data for debugging
            }
            
            # Log successful parse
            logger.info(f"Successfully parsed call {parsed['vapi_call_id']}")
            
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing call data: {str(e)}")
            raise ValueError(f"Failed to parse call data: {str(e)}")
    
    def _safe_get(self, data: Dict, key: str, default: Any = '') -> Any:
        """Safely extract value from dictionary"""
        return data.get(key, default) if data else default
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> str:
        """Parse ISO 8601 timestamp to local timezone"""
        if not timestamp_str:
            return datetime.now().isoformat()
        
        try:
            # Parse ISO format and convert to local time
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            logger.warning(f"Invalid timestamp format: {timestamp_str}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text fields"""
        if not text:
            return ''
        
        # Remove extra whitespace and limit length
        cleaned = ' '.join(str(text).strip().split())
        return cleaned[:1000]  # Limit to prevent sheet cell overflow
    
    def _format_name(self, name: str) -> str:
        """Format name to title case"""
        if not name:
            return ''
        
        # Title case with basic cleanup
        formatted = ' '.join(word.capitalize() for word in str(name).strip().split())
        return formatted[:100]  # Reasonable name length limit
    
    def _validate_email(self, email: str) -> str:
        """Validate and clean email address"""
        if not email:
            return ''
        
        email = str(email).strip().lower()
        
        if self.email_pattern.match(email):
            return email
        else:
            logger.warning(f"Invalid email format: {email}")
            return f"INVALID: {email}"
    
    def _validate_phone(self, phone: str) -> str:
        """Validate and format phone number"""
        if not phone:
            return ''
        
        # Remove all non-digit characters
        digits_only = re.sub(r'\D', '', str(phone))
        
        # Check if it matches expected pattern
        if self.phone_pattern.match(f"+1{digits_only}") or self.phone_pattern.match(digits_only):
            # Format as (XXX) XXX-XXXX for US numbers
            if len(digits_only) == 10:
                return f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
            elif len(digits_only) == 11 and digits_only[0] == '1':
                return f"({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
            else:
                return digits_only
        else:
            logger.warning(f"Invalid phone format: {phone}")
            return f"INVALID: {phone}"
    
    def _validate_intent(self, intent: str) -> str:
        """Validate caller intent against allowed values"""
        if not intent:
            return 'Unknown'
        
        # Define allowed intents (expand as needed)
        valid_intents = [
            'Oil Change', 'Tire Service', 'Brake Service', 'Engine Repair',
            'Transmission', 'Battery', 'Inspection', 'General Inquiry',
            'Appointment Booking', 'Price Quote', 'Emergency'
        ]
        
        intent_str = str(intent).strip()
        
        # Check for exact match (case insensitive)
        for valid in valid_intents:
            if intent_str.lower() == valid.lower():
                return valid
        
        # If no exact match, return as-is but log
        logger.info(f"Non-standard intent detected: {intent_str}")
        return intent_str[:50]  # Limit length
    
    def _parse_numeric(self, value: Any) -> str:
        """Parse numeric value (like vehicle KM) with validation"""
        if value is None or value == '':
            return ''
        
        try:
            # Try to convert to number and format
            num_value = float(str(value).replace(',', '').replace(' ', ''))
            
            # Reasonable range check for vehicle KM (0 to 999,999)
            if 0 <= num_value <= 999999:
                return f"{int(num_value):,}"  # Format with commas
            else:
                logger.warning(f"Vehicle KM out of reasonable range: {num_value}")
                return f"CHECK: {int(num_value):,}"
                
        except (ValueError, TypeError):
            logger.warning(f"Invalid numeric value: {value}")
            return f"INVALID: {str(value)[:20]}"
    
    def _determine_escalation_status(self, summary: str, structured: Dict[str, Any]) -> str:
        """Determine if call needs escalation based on content"""
        # Keywords that suggest escalation needed
        escalation_keywords = [
            'angry', 'frustrated', 'complaint', 'manager', 'supervisor',
            'emergency', 'urgent', 'asap', 'immediately', 'problem'
        ]
        
        # Check summary for escalation keywords
        summary_lower = str(summary).lower()
        if any(keyword in summary_lower for keyword in escalation_keywords):
            return 'High Priority'
        
        # Check intent for emergency services (try both possible field names)
        intent = structured.get('caller_intent', structured.get('CallerIntent', '')).lower()
        if 'emergency' in intent:
            return 'Emergency'
        
        # Default
        return 'Standard'
    
    def _calculate_follow_up_date(self, intent: str) -> str:
        """Calculate follow-up due date based on intent"""
        if not intent:
            return ''
        
        intent_lower = intent.lower()
        
        # Different intents have different follow-up urgencies
        if 'emergency' in intent_lower:
            # Same day follow-up
            from datetime import timedelta
            follow_up = datetime.now() + timedelta(hours=4)
        elif any(word in intent_lower for word in ['appointment', 'booking']):
            # Next business day
            from datetime import timedelta
            follow_up = datetime.now() + timedelta(days=1)
        elif any(word in intent_lower for word in ['quote', 'price']):
            # 2 business days
            from datetime import timedelta
            follow_up = datetime.now() + timedelta(days=2)
        else:
            # Standard 3 business days
            from datetime import timedelta
            follow_up = datetime.now() + timedelta(days=3)
        
        return follow_up.strftime('%Y-%m-%d') 