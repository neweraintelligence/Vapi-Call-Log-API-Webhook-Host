# Central Call-Log System

A robust webhook endpoint that captures Vapi voice agent call data and automatically logs it to Google Sheets for OK Tire's operational needs.

## 🎯 Project Overview

This system serves as a bridge between Vapi's AI voice agent and a centralized Google Sheets call log, providing:

- **Real-time call ingestion** from Vapi webhooks
- **Structured data parsing** with validation and formatting
- **Google Sheets integration** with retry logic and error handling
- **Operational views** for follow-ups and reporting
- **Future CRM extensibility** with dual-write capability

## 📁 Project Structure

```
call-log/
├── src/
│   ├── main.py          # Flask app & Cloud Function entrypoint
│   ├── parser.py        # JSON payload parser with validation
│   └── sheet_writer.py  # Google Sheets API wrapper
├── tests/
│   └── test_parser.py   # Comprehensive test suite (95% coverage)
├── .env.example         # Environment variables template
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Google Cloud account (for deployment)
- Google Sheets API access
- Vapi account with webhook configuration

### 2. Local Development Setup

```bash
# Clone and setup
git clone <repository-url>
cd call-log

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 3. Configure Environment

Edit `.env` with your actual values:

```bash
# Required
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
GOOGLE_CREDENTIALS_PATH=./credentials.json
VAPI_WEBHOOK_SECRET=your_secret_from_vapi_dashboard

# Optional
SHEET_NAME=Raw
PORT=8080
```

### 4. Google Sheets Setup

1. **Create a new Google Sheet** with these tabs:
   - `Raw` (for data dump)
   - `Views` (for filtered views)

2. **Set up Google Service Account:**
   ```bash
   # Go to Google Cloud Console
   # Create new project or select existing
   # Enable Google Sheets API
   # Create Service Account
   # Download credentials.json
   ```

3. **Share your sheet** with the service account email (found in credentials.json)

### 5. Run Locally

```bash
# Start development server
python src/main.py

# Test endpoint
curl -X GET http://localhost:8080/health
```

## 📡 API Endpoints

### Webhook Endpoint
```bash
POST /webhook
Content-Type: application/json
X-Vapi-Secret: your_webhook_secret

# Example payload
{
  "call": {
    "id": "call_12345",
    "created_at": "2024-01-15T10:30:00Z",
    "duration": 180,
    "status": "completed"
  },
  "summary": {
    "text": "Customer called about oil change..."
  },
  "structured": {
    "Name": "John Doe",
    "Email": "john@email.com",
    "PhoneNumber": "5551234567",
    "CallerIntent": "Oil Change",
    "VehicleMake": "Honda",
    "VehicleModel": "Civic",
    "VehicleKM": "45000"
  }
}
```

### Health Check
```bash
GET /health
# Returns service status and timestamp
```

### Test Endpoint
```bash
POST /test
# Same payload format as webhook, returns parsed data without writing to sheet
```

## 📊 Data Schema

| Column | Description | Validation |
|--------|-------------|------------|
| `timestamp` | Call start time | ISO 8601 → local time |
| `vapi_call_id` | Unique call identifier | Required |
| `CallSummary` | AI-generated summary | Max 1000 chars |
| `Name` | Customer name | Title case formatting |
| `Email` | Customer email | Regex validation |
| `PhoneNumber` | Customer phone | US format: (555) 123-4567 |
| `CallerIntent` | Purpose of call | Predefined enum values |
| `VehicleMake` | Vehicle manufacturer | Text cleanup |
| `VehicleModel` | Vehicle model | Text cleanup |
| `VehicleKM` | Vehicle mileage | Numeric validation, comma formatting |
| `escalation_status` | Priority level | Auto-determined from content |
| `follow_up_due` | Follow-up date | Auto-calculated by intent |
| `call_duration` | Call length (seconds) | Numeric |
| `call_status` | Call completion status | From Vapi |
| `raw_payload` | Original JSON (truncated) | Debugging aid |

## 🚀 Deployment

### Google Cloud Functions

1. **Prepare deployment:**
   ```bash
   # Create main.py entrypoint (already done)
   # Ensure requirements.txt is complete
   # Set environment variables in Cloud Console
   ```

2. **Deploy:**
   ```bash
   gcloud functions deploy vapi-call-log \
     --runtime python39 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point main \
     --set-env-vars GOOGLE_SHEET_ID=your_sheet_id,VAPI_WEBHOOK_SECRET=your_secret
   ```

3. **Get the deployment URL:**
   ```bash
   gcloud functions describe vapi-call-log --format="value(httpsTrigger.url)"
   ```

### Alternative: AWS Lambda

1. **Package the deployment:**
   ```bash
   # Install dependencies locally
   pip install -r requirements.txt -t .
   
   # Create deployment package
   zip -r deployment-package.zip .
   ```

2. **Deploy via AWS CLI or Console**

### Alternative: Supabase Edge Functions

1. **Create edge function:**
   ```bash
   supabase functions new vapi-call-log
   # Copy src/main.py content to the function
   supabase functions deploy vapi-call-log
   ```

## 🔧 Configuration & Governance

### Data Validation Rules

The system includes built-in validation:

- **Phone numbers:** US format validation with auto-formatting
- **Email addresses:** RFC-compliant regex validation
- **Vehicle KM:** Range validation (0-999,999) with comma formatting
- **Caller Intent:** Enum validation against predefined values
- **Escalation detection:** Keyword-based priority assignment

### Duplicate Prevention

- Unique constraint checking on `vapi_call_id`
- Configurable retry logic with exponential backoff
- Error logging and alerting for failed operations

### Backup & Export

Add to Google Apps Script (Extensions → Apps Script in your sheet):

```javascript
function dailyBackup() {
  const sheet = SpreadsheetApp.getActiveSheet();
  const data = sheet.getDataRange().getValues();
  
  // Create CSV
  const csv = data.map(row => row.join(',')).join('\n');
  
  // Save to Drive
  const blob = Utilities.newBlob(csv, 'text/csv', 'call-log-backup-' + new Date().toISOString().split('T')[0] + '.csv');
  DriveApp.createFile(blob);
}

// Set up time-driven trigger for 2 AM daily
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_parser.py -v

# Test with realistic payloads
pytest tests/test_parser.py::TestRealisticPayloads -v
```

### Test Coverage Goals

- **95% code coverage** across all modules
- **Unit tests** for all parsing and validation logic
- **Integration tests** with realistic Vapi payloads
- **Error handling tests** for malformed data

## 🚨 Monitoring & Alerts

### Health Monitoring

- `/health` endpoint for uptime monitoring
- Google Sheets API quota monitoring
- Error rate tracking and alerting

### Slack Integration (Optional)

Add to your `.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

Then errors and daily summaries will be posted to Slack.

## 🔮 Future Extensibility

### CRM Integration Ready

The architecture supports dual-write to future CRM systems:

```python
# In sheet_writer.py, extend append_call_data():
def append_call_data(self, call_data):
    # Write to Google Sheets
    self._append_to_sheet(call_data)
    
    # Also write to CRM (when ready)
    if os.getenv('CRM_API_URL'):
        self._post_to_crm(call_data)
```

### Schema Evolution

Field mappings are centralized in `parser.py` - easy to extend:

```python
# Add new fields to structured data parsing
'CustomerType': structured_data.get('CustomerType', 'Walk-in'),
'ServiceLocation': structured_data.get('ServiceLocation', 'Main Shop'),
```

## 📞 Support & Troubleshooting

### Common Issues

1. **"Google Sheets service not initialized"**
   - Check `GOOGLE_CREDENTIALS_PATH` or `GOOGLE_CREDENTIALS_JSON`
   - Verify service account has Sheets API access
   - Ensure sheet is shared with service account email

2. **"Rate limited" errors**
   - Built-in exponential backoff handles temporary limits
   - For persistent issues, check Google API quotas

3. **"Invalid phone format" in logs**
   - Update `phone_pattern` regex in `parser.py` for international numbers
   - Or adjust validation logic for your region

### Debug Mode

Set `FLASK_ENV=development` for detailed logging:

```bash
export FLASK_ENV=development
python src/main.py
```

### Getting Help

- Check logs in Google Cloud Console (for Cloud Functions)
- Use `/test` endpoint to validate payload parsing
- Run unit tests to verify core functionality

## 📈 Usage Analytics

The sheet automatically tracks:
- Call volume trends
- Intent distribution
- Follow-up completion rates
- Escalation patterns

Create pivot tables in the "Views" tab for operational insights.

---

**Ready to get started?** Follow the Quick Start guide above, then configure your Vapi webhook to point to your deployed endpoint! 