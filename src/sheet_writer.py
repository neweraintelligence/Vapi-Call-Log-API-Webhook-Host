import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class SheetWriter:
    """
    Wrapper around Google Sheets API for appending call data
    """
    
    def __init__(self):
        self.spreadsheet_id = os.getenv('GOOGLE_SHEET_ID')
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
        self.sheet_name = os.getenv('SHEET_NAME', 'Raw')
        
        # Column headers (must match parser output)
        self.headers = [
            'timestamp', 'vapi_call_id', 'CallSummary', 'Name', 'Email', 'PhoneNumber',
            'CallerIntent', 'VehicleMake', 'VehicleModel', 'VehicleKM', 'escalation_status',
            'follow_up_due', 'call_duration', 'call_status', 'raw_payload'
        ]
        
        self.service: Optional[Any] = None
        self._initialized = False
    
    def _initialize_service(self):
        """Initialize Google Sheets API service (lazy initialization)"""
        if self._initialized:
            return
            
        try:
            if os.path.exists(self.credentials_path):
                # Use service account credentials file
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                # Try to use credentials from environment variable
                creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
                if creds_json:
                    creds_info = json.loads(creds_json)
                    credentials = service_account.Credentials.from_service_account_info(
                        creds_info,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                else:
                    raise ValueError("No Google credentials found. Set GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON")
            
            self.service = build('sheets', 'v4', credentials=credentials)
            self._initialized = True
            logger.info("Google Sheets API service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {str(e)}")
            raise
    
    def append_call_data(self, call_data: Dict[str, Any]) -> bool:
        """
        Append call data to the Google Sheet with retry logic
        
        Args:
            call_data: Parsed call data dictionary
            
        Returns:
            bool: Success status
        """
        # Initialize service if not already done
        self._initialize_service()
        
        if not self.service:
            raise RuntimeError("Google Sheets service not initialized")
        
        # Convert call data to row format
        row_data = self._format_row_data(call_data)
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._append_row(row_data)
                logger.info(f"Successfully appended call {call_data.get('vapi_call_id')} to sheet")
                return True
                
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    wait_time = (2 ** attempt) + 1  # Exponential backoff
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"HTTP error appending to sheet: {e}")
                    raise
                    
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def _format_row_data(self, call_data: Dict[str, Any]) -> List[str]:
        """
        Format call data dictionary into row array matching header order
        
        Args:
            call_data: Parsed call data dictionary
            
        Returns:
            List of values in header order
        """
        row = []
        for header in self.headers:
            value = call_data.get(header, '')
            
            # Convert to string and handle None values
            if value is None:
                row.append('')
            else:
                row.append(str(value))
        
        return row
    
    def _append_row(self, row_data: List[str]):
        """
        Append a single row to the sheet
        
        Args:
            row_data: List of cell values
        """
        range_name = f"{self.sheet_name}!A:A"  # Dynamic range
        
        body = {
            'values': [row_data]
        }
        
        result = self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        logger.debug(f"Appended {result.get('updates', {}).get('updatedRows', 0)} rows")
    
    def ensure_headers(self) -> bool:
        """
        Ensure the sheet has proper headers in row 1
        
        Returns:
            bool: Success status
        """
        try:
            # Initialize service if not already done
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
                self._update_headers()
                logger.info("Headers updated in sheet")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ensuring headers: {str(e)}")
            return False
    
    def _update_headers(self):
        """Update the header row"""
        range_name = f"{self.sheet_name}!1:1"
        
        body = {
            'values': [self.headers]
        }
        
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
    
    def check_for_duplicates(self, vapi_call_id: str) -> bool:
        """
        Check if a call ID already exists in the sheet
        
        Args:
            vapi_call_id: Call ID to check
            
        Returns:
            bool: True if duplicate exists
        """
        try:
            # Initialize service if not already done
            self._initialize_service()
            
            # Search for the call ID in column B (vapi_call_id)
            range_name = f"{self.sheet_name}!B:B"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            # Check if call ID exists in any row
            for row in values:
                if row and row[0] == vapi_call_id:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False
    
    def get_sheet_stats(self) -> Dict[str, Any]:
        """
        Get basic statistics about the sheet
        
        Returns:
            Dict with row count and other stats
        """
        try:
            # Initialize service if not already done
            self._initialize_service()
            
            # Get all data to count rows
            range_name = f"{self.sheet_name}!A:A"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            row_count = len(values)
            
            return {
                "total_rows": row_count,
                "data_rows": max(0, row_count - 1),  # Excluding header
                "sheet_name": self.sheet_name,
                "spreadsheet_id": self.spreadsheet_id
            }
            
        except Exception as e:
            logger.error(f"Error getting sheet stats: {str(e)}")
            return {"error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check if Google Sheets connection is working
        
        Returns:
            Dict with health status
        """
        try:
            # Check if required environment variables are set
            if not self.spreadsheet_id:
                return {
                    "status": "error",
                    "message": "GOOGLE_SHEET_ID environment variable not set"
                }
            
            # Try to initialize service
            self._initialize_service()
            
            # Test basic connectivity by getting sheet metadata
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            return {
                "status": "healthy",
                "message": "Google Sheets connection successful",
                "sheet_title": result.get('properties', {}).get('title', 'Unknown'),
                "sheet_id": self.spreadsheet_id
            }
            
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Google Sheets connection failed: {str(e)}"
            }

def create_sheet_writer() -> SheetWriter:
    """Factory function to create SheetWriter instance"""
    return SheetWriter() 