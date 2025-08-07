import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from threading import Lock
import schedule
from googleapiclient.discovery import build
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class CallManager:
    """
    Manages outbound calling campaigns with rate limiting and queue processing
    """
    
    def __init__(self):
        # VAPI Configuration
        self.vapi_token = os.getenv('VAPI_TOKEN')
        self.vapi_phone_id = os.getenv('VAPI_PHONE_ID')
        self.vapi_assistant_id = os.getenv('VAPI_ASSISTANT_ID')
        self.vapi_base_url = "https://api.vapi.ai"
        
        # Google Sheets Configuration
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        self.spreadsheet_id = os.getenv('CAMPAIGN_SHEET_ID')
        self.sheet_name = os.getenv('CAMPAIGN_SHEET_NAME', 'Campaign')
        
        # Rate limiting configuration
        self.calls_per_batch = int(os.getenv('CALLS_PER_BATCH', '5'))
        self.batch_interval_minutes = int(os.getenv('BATCH_INTERVAL_MINUTES', '5'))
        
        # Internal state
        self.is_running = False
        self.campaign_lock = Lock()
        self.service = None
        
        # Campaign headers for Google Sheets
        self.headers = [
            'name', 'phone_number', 'caller_phone_number', 'attempt_count', 'status', 'last_called', 
            'next_call_time', 'call_summary', 'vapi_call_id', 'notes'
        ]
        
        # Status values
        self.STATUS_QUEUED = "QUEUED"
        self.STATUS_CALLING = "CALLING"
        self.STATUS_COMPLETED = "COMPLETED"
        self.STATUS_FAILED = "FAILED"
        self.STATUS_SUMMARY_RECEIVED = "SUMMARY_RECEIVED"
    
    def _initialize_service(self):
        """Initialize Google Sheets API service"""
        if self.service:
            return
            
        try:
            if os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    creds_info = json.loads(creds_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_info,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                else:
                    raise ValueError("No Google credentials found")
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Google Sheets API service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            raise
    
    def start_campaign(self, target_calls: int = None) -> Dict[str, Any]:
        """
        Start outbound calling campaign
        
        Args:
            target_calls: Maximum number of calls to make (None for unlimited)
            
        Returns:
            Dict with campaign status
        """
        with self.campaign_lock:
            if self.is_running:
                return {"error": "Campaign already running"}
            
            try:
                self._initialize_service()
                
                # Get queued calls
                queued_calls = self._get_queued_calls()
                
                if not queued_calls:
                    return {"error": "No queued calls found"}
                
                # Limit calls if target specified
                if target_calls:
                    queued_calls = queued_calls[:target_calls]
                
                self.is_running = True
                
                # Schedule batch processing
                schedule.every(self.batch_interval_minutes).minutes.do(
                    self._process_batch
                )
                
                logger.info(f"Campaign started with {len(queued_calls)} calls")
                
                # Process first batch immediately
                self._process_batch()
                
                return {
                    "status": "started",
                    "total_calls": len(queued_calls),
                    "batch_size": self.calls_per_batch,
                    "interval_minutes": self.batch_interval_minutes
                }
                
            except Exception as e:
                self.is_running = False
                logger.error(f"Failed to start campaign: {str(e)}")
                return {"error": str(e)}
    
    def stop_campaign(self) -> Dict[str, Any]:
        """Stop the current campaign"""
        with self.campaign_lock:
            if not self.is_running:
                return {"error": "No campaign running"}
            
            self.is_running = False
            schedule.clear()
            
            logger.info("Campaign stopped")
            return {"status": "stopped"}
    
    def get_campaign_status(self) -> Dict[str, Any]:
        """Get current campaign status and statistics"""
        try:
            self._initialize_service()
            
            # Get call statistics
            stats = self._get_call_statistics()
            
            return {
                "is_running": self.is_running,
                "statistics": stats,
                "configuration": {
                    "calls_per_batch": self.calls_per_batch,
                    "batch_interval_minutes": self.batch_interval_minutes
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get campaign status: {str(e)}")
            return {"error": str(e)}
    
    def _get_queued_calls(self) -> List[Dict[str, Any]]:
        """Get all queued calls from Google Sheets"""
        try:
            range_name = f"{self.sheet_name}!A:J"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                return []
            
            # Skip header row
            calls = []
            for i, row in enumerate(values[1:], start=2):
                # Pad row to ensure all columns exist
                while len(row) < len(self.headers):
                    row.append('')
                
                call_data = dict(zip(self.headers, row))
                call_data['row_number'] = i
                
                # Only include queued calls
                if call_data.get('status') == self.STATUS_QUEUED:
                    calls.append(call_data)
            
            return calls
            
        except Exception as e:
            logger.error(f"Failed to get queued calls: {str(e)}")
            return []
    
    def _process_batch(self):
        """Process a batch of calls"""
        if not self.is_running:
            return
        
        try:
            # Get next batch of calls
            queued_calls = self._get_queued_calls()
            batch = queued_calls[:self.calls_per_batch]
            
            if not batch:
                logger.info("No more queued calls, stopping campaign")
                self.stop_campaign()
                return
            
            logger.info(f"Processing batch of {len(batch)} calls")
            
            for call in batch:
                self._make_call(call)
                time.sleep(1)  # Brief delay between calls
            
        except Exception as e:
            logger.error(f"Error processing batch: {str(e)}")
    
    def _make_call(self, call_data: Dict[str, Any]) -> bool:
        """
        Make a single outbound call via VAPI
        
        Args:
            call_data: Call information from spreadsheet
            
        Returns:
            bool: Success status
        """
        try:
            # Update status to CALLING
            self._update_call_status(
                call_data['row_number'], 
                self.STATUS_CALLING,
                last_called=datetime.now().isoformat()
            )
            
            # Prepare VAPI request
            headers = {
                'Authorization': f'Bearer {self.vapi_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'phoneNumberId': self.vapi_phone_id,
                'assistantId': self.vapi_assistant_id,
                'customer': {
                    'number': call_data['phone_number']
                },
                'metadata': {
                    'customer_name': call_data['name'],
                    'row_number': str(call_data['row_number']),
                    'attempt': str(int(call_data.get('attempt_count', '0')) + 1)
                }
            }
            
            # Make the call
            response = requests.post(
                f"{self.vapi_base_url}/call/phone",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                call_response = response.json()
                vapi_call_id = call_response.get('id', '')
                
                # Update with success status
                self._update_call_status(
                    call_data['row_number'],
                    self.STATUS_COMPLETED,
                    vapi_call_id=vapi_call_id,
                    attempt_count=int(call_data.get('attempt_count', '0')) + 1
                )
                
                logger.info(f"Call initiated for {call_data['name']}: {vapi_call_id}")
                return True
                
            else:
                # Update with failed status
                self._update_call_status(
                    call_data['row_number'],
                    self.STATUS_FAILED,
                    notes=f"API Error: {response.status_code}",
                    attempt_count=int(call_data.get('attempt_count', '0')) + 1
                )
                
                logger.error(f"Call failed for {call_data['name']}: {response.status_code}")
                return False
                
        except Exception as e:
            # Update with failed status
            self._update_call_status(
                call_data['row_number'],
                self.STATUS_FAILED,
                notes=f"Error: {str(e)}",
                attempt_count=int(call_data.get('attempt_count', '0')) + 1
            )
            
            logger.error(f"Exception making call for {call_data['name']}: {str(e)}")
            return False
    
    def _update_call_status(self, row_number: int, status: str, **kwargs):
        """
        Update call record in Google Sheets
        
        Args:
            row_number: Row number in sheet
            status: New status
            **kwargs: Additional fields to update
        """
        try:
            # Get current row data
            range_name = f"{self.sheet_name}!{row_number}:{row_number}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            current_row = result.get('values', [[]])[0]
            
            # Pad row to ensure all columns exist
            while len(current_row) < len(self.headers):
                current_row.append('')
            
            # Update specific fields
            updates = dict(zip(self.headers, current_row))
            updates['status'] = status
            
            # Apply additional updates
            for key, value in kwargs.items():
                if key in self.headers:
                    updates[key] = str(value)
            
            # Convert back to row format
            updated_row = [updates.get(header, '') for header in self.headers]
            
            # Update the sheet
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body={'values': [updated_row]}
            ).execute()
            
        except Exception as e:
            logger.error(f"Failed to update call status: {str(e)}")
    
    def _get_call_statistics(self) -> Dict[str, int]:
        """Get call statistics from spreadsheet"""
        try:
            range_name = f"{self.sheet_name}!D:D"  # Status column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:  # Only header or empty
                return {}
            
            # Count statuses (skip header)
            status_counts = {}
            for row in values[1:]:
                if row:
                    status = row[0]
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            return status_counts
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {}
    
    def update_call_summary(self, vapi_call_id: str, call_summary: str, caller_phone_number: str = None) -> bool:
        """
        Update call with summary received from webhook
        
        Args:
            vapi_call_id: VAPI call ID
            call_summary: Call summary text
            caller_phone_number: Phone number of the caller (optional)
            
        Returns:
            bool: Success status
        """
        try:
            self._initialize_service()
            
            # Find the row with this call ID
            range_name = f"{self.sheet_name}!H:H"  # vapi_call_id column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            for i, row in enumerate(values[1:], start=2):  # Skip header
                if row and row[0] == vapi_call_id:
                    # Prepare update kwargs
                    update_kwargs = {'call_summary': call_summary}
                    if caller_phone_number:
                        update_kwargs['caller_phone_number'] = caller_phone_number
                    
                    # Update this row with summary and caller phone number
                    self._update_call_status(
                        i,
                        self.STATUS_SUMMARY_RECEIVED,
                        **update_kwargs
                    )
                    
                    logger.info(f"Updated call {vapi_call_id} with summary")
                    return True
            
            logger.warning(f"Call ID {vapi_call_id} not found in campaign sheet")
            return False
            
        except Exception as e:
            logger.error(f"Failed to update call summary: {str(e)}")
            return False
    
    def ensure_headers(self) -> bool:
        """Ensure the campaign sheet has proper headers"""
        try:
            self._initialize_service()
            
            # Check if headers exist
            range_name = f"{self.sheet_name}!1:1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            existing_headers = result.get('values', [[]])[0] if result.get('values') else []
            
            # If no headers or headers don't match, update them
            if not existing_headers or existing_headers != self.headers:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=range_name,
                    valueInputOption='USER_ENTERED',
                    body={'values': [self.headers]}
                ).execute()
                
                logger.info("Campaign sheet headers updated")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring headers: {str(e)}")
            return False
    
    def _extract_caller_phone_number(self, payload: dict) -> Optional[str]:
        """
        Extract caller's phone number from End of Call Report payload
        
        Args:
            payload: The webhook payload from VAPI
            
        Returns:
            str: Formatted phone number or None if not found
        """
        try:
            # Try different possible locations for the phone number
            phone_number = None
            
            # Check message.call.from (most common location)
            if payload.get('message', {}).get('call', {}).get('from'):
                phone_number = payload['message']['call']['from']
            
            # Check root level call.from
            elif payload.get('call', {}).get('from'):
                phone_number = payload['call']['from']
            
            # Check message.call.customer.number
            elif payload.get('message', {}).get('call', {}).get('customer', {}).get('number'):
                phone_number = payload['message']['call']['customer']['number']
            
            # Check root level call.customer.number
            elif payload.get('call', {}).get('customer', {}).get('number'):
                phone_number = payload['call']['customer']['number']
            
            # Try to find phone number in the Messages > Artifact section
            elif payload.get('message', {}).get('artifact'):
                artifact = payload['message']['artifact']
                # If artifact is a string, try to parse it as JSON
                if isinstance(artifact, str):
                    try:
                        import json
                        artifact_data = json.loads(artifact)
                        # Look for phone number in artifact data
                        if isinstance(artifact_data, dict):
                            # Check common phone number fields in artifact
                            for field in ['from', 'customer_number', 'caller_number', 'phone', 'number']:
                                if field in artifact_data:
                                    phone_number = artifact_data[field]
                                    break
                    except json.JSONDecodeError:
                        pass
                elif isinstance(artifact, dict):
                    # If artifact is already a dict, look for phone number fields
                    for field in ['from', 'customer_number', 'caller_number', 'phone', 'number']:
                        if field in artifact:
                            phone_number = artifact[field]
                            break
            
            # If we found a phone number, clean and format it
            if phone_number:
                return self._format_caller_phone_number(str(phone_number))
            
            logger.warning("Caller phone number not found in payload")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting caller phone number: {str(e)}")
            return None
    
    def _format_caller_phone_number(self, phone: str) -> str:
        """
        Format and clean caller phone number
        
        Args:
            phone: Raw phone number from payload
            
        Returns:
            str: Cleaned phone number
        """
        import re
        
        # Remove all non-digit characters except the leading +
        if phone.startswith('+'):
            # Keep the + and remove everything except digits
            digits = re.sub(r'[^\d]', '', phone[1:])
            cleaned = f"+{digits}"
        else:
            # Remove all non-digits
            digits = re.sub(r'[^\d]', '', phone)
            # Add + if it's missing
            if len(digits) >= 10:
                cleaned = f"+{digits}"
            else:
                cleaned = phone  # Return as-is if too short
        
        return cleaned

# Background scheduler function
def run_scheduler():
    """Run the scheduled tasks"""
    while True:
        schedule.run_pending()
        time.sleep(1)