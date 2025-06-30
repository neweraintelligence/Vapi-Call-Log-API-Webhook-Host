# Central Call-Log System (Multi-Agent)

A robust webhook endpoint that captures Vapi voice agent call data and automatically logs it to Google Sheets for OK Tire's operational needs. **Now supports multiple agents with automatic routing to separate sheets.**

## 🎯 Project Overview

This system serves as a bridge between Vapi's AI voice agents and centralized Google Sheets call logs, providing:

- **Multi-agent support** with automatic routing to separate sheets
- **Real-time call ingestion** from Vapi webhooks
- **Structured data parsing** with validation and formatting
- **Phone number redundancy** - captures caller number from both AI analysis and call metadata
- **Google Sheets integration** with retry logic and error handling
- **Operational views** for follow-ups and reporting
- **Future CRM extensibility** with dual-write capability

## 📁 Project Structure

```
call-log/
├── src/
│   ├── main.py          # Flask app & Cloud Function entrypoint
│   ├── parser.py        # JSON payload parser with validation
│   └── sheet_writer.py  # Google Sheets API wrapper (multi-agent)
├── tests/
│   └── test_parser.py   # Comprehensive test suite (95% coverage)
├── test_multi_agent.py  # Multi-agent testing script
├── .env.example         # Environment variables template
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8+
- Google Cloud account (for deployment)
- Google Sheets API access
- Vapi account with multiple agents configured

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

### 3. Configure Environment (Multi-Agent)

Edit `.env` with your actual values:

```bash
# Required - Agent 1
GOOGLE_SHEET_ID_AGENT1=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
AGENT1_ID=your_first_agent_id_from_vapi

# Required - Agent 2  
GOOGLE_SHEET_ID_AGENT2=1CxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
AGENT2_ID=your_second_agent_id_from_vapi

# Required - Google Credentials
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}

# Optional
SHEET_NAME=Raw
PORT=8080
```

### 4. Google Sheets Setup (Multi-Agent)

1. **Create two separate Google Sheets:**
   - Sheet 1 for Agent 1 (e.g., "OK Tire - Sales Agent Calls")
   - Sheet 2 for Agent 2 (e.g., "OK Tire - Support Agent Calls")

2. **Each sheet should have these tabs:**
   - `Raw` (for data dump)
   - `Views` (for filtered views)

3. **Set up Google Service Account:**
   ```bash
   # Go to Google Cloud Console
   # Create new project or select existing
   # Enable Google Sheets API
   # Create Service Account
   # Download credentials.json
   ```

4. **Share both sheets** with the service account email (found in credentials.json)

### 5. Get Your VAPI Agent IDs

1. Go to your VAPI dashboard
2. Click on your first agent → copy the Agent ID from the URL or settings
3. Click on your second agent → copy the Agent ID
4. Add these IDs to your environment variables

### 6. Run Locally

```bash
# Start development server
python src/main.py

# Test health endpoint
curl -X GET http://localhost:8080/health

# Test multi-agent setup
python test_multi_agent.py
```

## 📡 API Endpoints

### Webhook Endpoint (Multi-Agent)
```bash
POST /webhook
Content-Type: application/json

# The system automatically routes to the correct sheet based on agent ID
# Example payload
{
  "type": "end-of-call-report",
  "call": {
    "id": "call_12345",
    "assistant": {
      "id": "agent1_id"  # This determines which sheet to use
    },
    "created_at": "2024-01-15T10:30:00Z",
    "duration": 180,
    "status": "completed"
  },
  "analysis": {
    "summary": "Customer called about oil change...",
    "structured_data": {
      "Name": "John Doe",
      "Email": "john@email.com",
      "PhoneNumber": "5551234567"
    },
    "success": true
  }
}
```

### Health Check (Multi-Agent)
```bash
GET /health
# Returns service status, agent configuration, and sheet health for both agents
```

### Test Endpoint
```bash
POST /test
# Same payload format as webhook, returns parsed data without writing to sheet
```

## 🔧 Multi-Agent Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_SHEET_ID_AGENT1` | Google Sheet ID for Agent 1 | Yes |
| `GOOGLE_SHEET_ID_AGENT2` | Google Sheet ID for Agent 2 | Yes |
| `AGENT1_ID` | VAPI Agent ID for Agent 1 | Yes |
| `AGENT2_ID` | VAPI Agent ID for Agent 2 | Yes |
| `GOOGLE_CREDENTIALS_JSON` | Minified service account JSON | Yes |
| `SHEET_NAME` | Sheet tab name (default: "Raw") | No |

### Agent Routing Logic

The system automatically routes calls to the correct Google Sheet based on the `assistant.id` field in the VAPI payload:

- If `assistant.id` matches `AGENT1_ID` → writes to Agent 1's sheet
- If `assistant.id` matches `AGENT2_ID` → writes to Agent 2's sheet
- If `assistant.id` doesn't match either → defaults to Agent 1's sheet with warning

## 🧪 Testing Multi-Agent Setup

### 1. Update Test Script

Edit `test_multi_agent.py` and update the agent IDs:

```python
AGENT1_TEST_PAYLOAD = {
    "call": {
        "assistant": {
            "id": "your_actual_agent1_id"  # Replace with real ID
        }
    }
}

AGENT2_TEST_PAYLOAD = {
    "call": {
        "assistant": {
            "id": "your_actual_agent2_id"  # Replace with real ID
        }
    }
}
```

### 2. Run Tests

```bash
# Test the multi-agent system
python test_multi_agent.py

# Check health endpoint
curl https://vapi-call-log.onrender.com/health
```

### 3. Verify Results

1. Check both Google Sheets for test data
2. Verify data went to the correct sheets
3. Check Render logs for any errors

## 🚀 Deployment (Render)

### 1. Update Environment Variables in Render

In your Render dashboard, add these environment variables:

- `GOOGLE_SHEET_ID_AGENT1`: Your first agent's sheet ID
- `GOOGLE_SHEET_ID_AGENT2`: Your second agent's sheet ID  
- `AGENT1_ID`: Your first agent's VAPI ID
- `AGENT2_ID`: Your second agent's VAPI ID
- `GOOGLE_CREDENTIALS_JSON`: Your minified service account JSON
- `SHEET_NAME`: Raw (or your preferred tab name)

### 2. Deploy

```bash
# Push your changes
git add .
git commit -m "Add multi-agent support"
git push origin main

# Render will automatically deploy
```

### 3. Configure VAPI

Both agents use the same webhook URL: `https://vapi-call-log.onrender.com/webhook`

The system automatically routes based on the agent ID in the payload.

## 📊 Data Schema

Same schema as before, but now data is automatically separated by agent:

| Column | Description | Validation |
|--------|-------------|------------|
| `timestamp` | Call start time | ISO 8601 → local time |
| `vapi_call_id` | Unique call identifier | Required |
| `CallSummary` | AI-generated summary | Max 1000 chars |
| `Name` | Customer name | Title case formatting |
| `Email` | Customer email | Regex validation |
| `PhoneNumber` | Customer phone (from structured data) | US format: (555) 123-4567 |
| `CallerPhoneNumber` | Caller phone (from call metadata) | US format: (555) 123-4567 |
| `CallerIntent` | Purpose of call | Predefined enum values |
| `VehicleMake` | Vehicle manufacturer | Text cleanup |
| `VehicleModel` | Vehicle model | Text cleanup |
| `VehicleKM` | Vehicle mileage | Numeric validation, comma formatting |
| `escalation_status` | Priority level | Auto-determined from content |
| `follow_up_due` | Follow-up date | Auto-calculated by intent |
| `call_duration` | Call length (seconds) | Numeric |
| `call_status` | Call completion status | From Vapi |
| `raw_payload` | Original JSON (truncated) | Debugging aid |

## 🔍 Troubleshooting

### Common Issues

1. **Data not appearing in sheets:**
   - Check that both sheets are shared with your service account email
   - Verify environment variables are set correctly in Render
   - Check Render logs for errors

2. **Wrong agent routing:**
   - Verify `AGENT1_ID` and `AGENT2_ID` match your actual VAPI agent IDs
   - Check the webhook payload to ensure `assistant.id` is present

3. **Health check shows errors:**
   - Run `curl https://vapi-call-log.onrender.com/health` to see detailed status
   - Check that both sheet IDs are valid and accessible

### Debug Commands

```bash
# Check health status
curl https://vapi-call-log.onrender.com/health

# Test with specific agent payload
curl -X POST https://vapi-call-log.onrender.com/webhook \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# Run local tests
python test_multi_agent.py
```

## 🔄 Adding More Agents

To add a third agent:

1. Create a new Google Sheet
2. Add environment variables: `GOOGLE_SHEET_ID_AGENT3`, `AGENT3_ID`
3. Update `sheet_writer.py` to handle the third agent
4. Deploy and test

## 📈 Monitoring

- **Health endpoint**: Monitor overall system health
- **Render logs**: Check for errors and performance
- **Google Sheets**: Verify data is being written correctly
- **VAPI dashboard**: Monitor webhook delivery status

---

**Ready to get started?** Follow the Quick Start guide above, then configure your Vapi webhook to point to your deployed endpoint! 