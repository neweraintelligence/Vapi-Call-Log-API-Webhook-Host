#!/usr/bin/env python3
"""
Google Sheet Setup Script for Central Call-Log

This script initializes a Google Sheet with proper headers, formatting,
and basic data validation rules for the Vapi call log system.
"""

import os
import json
import sys
from typing import Dict, Any
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.errors import HttpError

def load_credentials():
    """Load Google Service Account credentials"""
    credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')
    
    if os.path.exists(credentials_path):
        return service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
    
    # Try environment variable
    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json:
        creds_info = json.loads(creds_json)
        return service_account.Credentials.from_service_account_info(
            creds_info,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
    
    raise ValueError("No Google credentials found. Set GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON")

def create_new_sheet() -> str:
    """Create a new Google Sheet and return its ID"""
    credentials = load_credentials()
    service = build('sheets', 'v4', credentials=credentials)
    
    spreadsheet = {
        'properties': {
            'title': 'Central Call Log - Vapi Integration'
        },
        'sheets': [
            {
                'properties': {
                    'title': 'Raw',
                    'gridProperties': {
                        'rowCount': 1000,
                        'columnCount': 15
                    }
                }
            },
            {
                'properties': {
                    'title': 'Views',
                    'gridProperties': {
                        'rowCount': 100,
                        'columnCount': 10
                    }
                }
            }
        ]
    }
    
    result = service.spreadsheets().create(body=spreadsheet).execute()
    sheet_id = result['spreadsheetId']
    
    print(f"✅ Created new sheet with ID: {sheet_id}")
    print(f"📊 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
    
    return sheet_id

def setup_raw_sheet(service, sheet_id: str):
    """Set up the Raw data sheet with headers and formatting"""
    
    # Headers matching parser output
    headers = [
        'timestamp', 'vapi_call_id', 'CallSummary', 'Name', 'Email', 'PhoneNumber',
        'CallerIntent', 'VehicleMake', 'VehicleModel', 'VehicleKM', 'escalation_status',
        'follow_up_due', 'call_duration', 'call_status', 'raw_payload'
    ]
    
    # Insert headers
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='Raw!1:1',
        valueInputOption='USER_ENTERED',
        body={'values': [headers]}
    ).execute()
    
    print("✅ Added headers to Raw sheet")
    
    # Format headers (bold, freeze)
    requests = [
        # Freeze first row
        {
            'updateSheetProperties': {
                'properties': {
                    'sheetId': 0,  # Raw sheet ID
                    'gridProperties': {
                        'frozenRowCount': 1
                    }
                },
                'fields': 'gridProperties.frozenRowCount'
            }
        },
        # Bold headers
        {
            'repeatCell': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        },
                        'backgroundColor': {
                            'red': 0.9,
                            'green': 0.9,
                            'blue': 0.9
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat.bold,userEnteredFormat.backgroundColor'
            }
        },
        # Auto-resize columns
        {
            'autoResizeDimensions': {
                'dimensions': {
                    'sheetId': 0,
                    'dimension': 'COLUMNS',
                    'startIndex': 0,
                    'endIndex': 15
                }
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    
    print("✅ Applied formatting to Raw sheet")

def setup_data_validation(service, sheet_id: str):
    """Set up data validation rules"""
    
    requests = [
        # Email validation (column E)
        {
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 1,
                    'endRowIndex': 1000,
                    'startColumnIndex': 4,  # Email column (E)
                    'endColumnIndex': 5
                },
                'rule': {
                    'condition': {
                        'type': 'TEXT_IS_EMAIL'
                    },
                    'showCustomUi': True,
                    'strict': False
                }
            }
        },
        # Phone number validation (column F)
        {
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 1,
                    'endRowIndex': 1000,
                    'startColumnIndex': 5,  # Phone column (F)
                    'endColumnIndex': 6
                },
                'rule': {
                    'condition': {
                        'type': 'TEXT_CONTAINS',
                        'values': [{'userEnteredValue': '('}]
                    },
                    'showCustomUi': True,
                    'strict': False
                }
            }
        },
        # Caller Intent validation (column G)
        {
            'setDataValidation': {
                'range': {
                    'sheetId': 0,
                    'startRowIndex': 1,
                    'endRowIndex': 1000,
                    'startColumnIndex': 6,  # CallerIntent column (G)
                    'endColumnIndex': 7
                },
                'rule': {
                    'condition': {
                        'type': 'ONE_OF_LIST',
                        'values': [
                            {'userEnteredValue': 'Oil Change'},
                            {'userEnteredValue': 'Tire Service'},
                            {'userEnteredValue': 'Brake Service'},
                            {'userEnteredValue': 'Engine Repair'},
                            {'userEnteredValue': 'Transmission'},
                            {'userEnteredValue': 'Battery'},
                            {'userEnteredValue': 'Inspection'},
                            {'userEnteredValue': 'General Inquiry'},
                            {'userEnteredValue': 'Appointment Booking'},
                            {'userEnteredValue': 'Price Quote'},
                            {'userEnteredValue': 'Emergency'}
                        ]
                    },
                    'showCustomUi': True,
                    'strict': False
                }
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    
    print("✅ Added data validation rules")

def setup_conditional_formatting(service, sheet_id: str):
    """Set up conditional formatting for priority highlighting"""
    
    requests = [
        # Highlight Emergency escalation status
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': 0,
                        'startRowIndex': 1,
                        'endRowIndex': 1000,
                        'startColumnIndex': 10,  # escalation_status column (K)
                        'endColumnIndex': 11
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'Emergency'}]
                        },
                        'format': {
                            'backgroundColor': {
                                'red': 1.0,
                                'green': 0.4,
                                'blue': 0.4
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    }
                },
                'index': 0
            }
        },
        # Highlight High Priority escalation status
        {
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': 0,
                        'startRowIndex': 1,
                        'endRowIndex': 1000,
                        'startColumnIndex': 10,  # escalation_status column (K)
                        'endColumnIndex': 11
                    }],
                    'booleanRule': {
                        'condition': {
                            'type': 'TEXT_EQ',
                            'values': [{'userEnteredValue': 'High Priority'}]
                        },
                        'format': {
                            'backgroundColor': {
                                'red': 1.0,
                                'green': 0.8,
                                'blue': 0.4
                            }
                        }
                    }
                },
                'index': 1
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    
    print("✅ Added conditional formatting")

def setup_views_sheet(service, sheet_id: str):
    """Set up the Views sheet with sample filter formulas"""
    
    # Get the sheet ID for Views tab
    sheet_metadata = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    views_sheet_id = None
    for sheet in sheet_metadata['sheets']:
        if sheet['properties']['title'] == 'Views':
            views_sheet_id = sheet['properties']['sheetId']
            break
    
    if not views_sheet_id:
        print("❌ Views sheet not found")
        return
    
    # Add sample view headers and formulas
    view_data = [
        ['📋 OPERATIONAL VIEWS', '', '', '', ''],
        ['', '', '', '', ''],
        ['🔥 Open Follow-Ups (Next 7 Days)', '', '', '', ''],
        ['=FILTER(Raw!A:O, (Raw!L:L<>"")*((Raw!L:L-TODAY())<=7)*(Raw!L:L>=TODAY()))', '', '', '', ''],
        ['', '', '', '', ''],
        ['🚨 Emergency & High Priority Calls', '', '', '', ''],
        ['=FILTER(Raw!A:O, (Raw!K:K="Emergency")+(Raw!K:K="High Priority"))', '', '', '', ''],
        ['', '', '', '', ''],
        ['📈 Daily Call Summary', '', '', '', ''],
        ['Date', 'Total Calls', 'Emergencies', 'Follow-ups Due', 'Avg Duration'],
        ['=UNIQUE(Raw!A2:A)', '=COUNTIF(Raw!A:A,A11)', '=COUNTIFS(Raw!A:A,A11,Raw!K:K,"Emergency")', '=COUNTIFS(Raw!A:A,A11,Raw!L:L,"<>"&"")', '=AVERAGEIF(Raw!A:A,A11,Raw!M:M)']
    ]
    
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range='Views!A1:E11',
        valueInputOption='USER_ENTERED',
        body={'values': view_data}
    ).execute()
    
    # Format the Views sheet
    requests = [
        # Bold section headers
        {
            'repeatCell': {
                'range': {
                    'sheetId': views_sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True,
                            'fontSize': 14
                        }
                    }
                },
                'fields': 'userEnteredFormat.textFormat'
            }
        }
    ]
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={'requests': requests}
    ).execute()
    
    print("✅ Set up Views sheet with operational formulas")

def main():
    """Main setup function"""
    print("🔧 Central Call-Log Sheet Setup")
    print("=" * 40)
    
    # Check for existing sheet ID
    sheet_id = os.getenv('GOOGLE_SHEET_ID')
    
    if not sheet_id:
        print("No GOOGLE_SHEET_ID found. Creating new sheet...")
        sheet_id = create_new_sheet()
        print(f"\n💡 Add this to your .env file:")
        print(f"GOOGLE_SHEET_ID={sheet_id}")
    else:
        print(f"📊 Using existing sheet: {sheet_id}")
    
    try:
        credentials = load_credentials()
        service = build('sheets', 'v4', credentials=credentials)
        
        # Set up the sheets
        setup_raw_sheet(service, sheet_id)
        setup_data_validation(service, sheet_id)
        setup_conditional_formatting(service, sheet_id)
        setup_views_sheet(service, sheet_id)
        
        print("\n🎉 Sheet setup complete!")
        print(f"📊 Access your sheet: https://docs.google.com/spreadsheets/d/{sheet_id}")
        print("\n📋 Next steps:")
        print("1. Share the sheet with your team")
        print("2. Deploy the webhook endpoint")
        print("3. Configure Vapi to use your webhook URL")
        
    except HttpError as e:
        print(f"❌ Google Sheets API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 