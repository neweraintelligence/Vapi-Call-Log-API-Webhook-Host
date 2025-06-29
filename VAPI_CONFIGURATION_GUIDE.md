# VAPI Configuration Guide for Call Analysis Integration

## 🎯 Overview

This guide explains how to configure your VAPI assistant to automatically generate call summaries and structured data, then send them to your webhook endpoint as `end-of-call-report` messages.

## 📋 Step 1: Configure Assistant Analysis Plan

When creating or updating your VAPI assistant, include the following `analysisPlan` configuration:

```json
{
  "name": "OK Tire Call Assistant",
  "model": {
    "provider": "openai",
    "model": "gpt-4",
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant for OK Tire, helping customers with tire and automotive service needs..."
      }
    ]
  },
  "analysisPlan": {
    "summaryPrompt": "Provide a comprehensive summary of this call, including the customer's main concern, services discussed, vehicle information, and any follow-up actions needed. Focus on actionable details for the service team.",
    "structuredDataPrompt": "Extract the following information from the call: customer name, email, phone number, caller intent/service needed, vehicle make, vehicle model, vehicle kilometers/mileage, and any special notes or requests.",
    "structuredDataSchema": {
      "type": "object",
      "properties": {
        "customer_name": { 
          "type": "string",
          "description": "Full name of the customer"
        },
        "customer_email": { 
          "type": "string", 
          "format": "email",
          "description": "Customer's email address if provided"
        },
        "customer_phone": { 
          "type": "string",
          "description": "Customer's phone number"
        },
        "caller_intent": { 
          "type": "string",
          "enum": ["Oil Change", "Tire Service", "Brake Service", "Engine Repair", "Transmission", "Battery", "Inspection", "General Inquiry", "Appointment Booking", "Price Quote", "Emergency"],
          "description": "Primary reason for the call"
        },
        "vehicle_make": { 
          "type": "string",
          "description": "Make of the vehicle (e.g., Toyota, Honda, Ford)"
        },
        "vehicle_model": { 
          "type": "string",
          "description": "Model of the vehicle (e.g., Camry, Civic, F-150)"
        },
        "vehicle_km": { 
          "type": "string",
          "description": "Vehicle mileage or kilometers"
        },
        "service_requested": { 
          "type": "string",
          "description": "Specific services requested or discussed"
        },
        "customer_notes": { 
          "type": "string",
          "description": "Any additional notes, special requests, or important details"
        }
      },
      "required": ["customer_name", "caller_intent"]
    },
    "successEvaluationPrompt": "Evaluate if this call was successful based on: 1) Did we identify the customer's needs? 2) Did we provide helpful information or schedule appropriate service? 3) Was the customer satisfied with the interaction? Return 'true' for successful calls, 'false' for unsuccessful ones.",
    "successEvaluationRubric": "PassFail"
  },
  "serverMessages": ["end-of-call-report"],
  "serverUrl": "https://your-webhook-url.render.com/webhook"
}
```

## 🔗 Step 2: Set Up Server Messages

Ensure your assistant configuration includes:

```json
{
  "serverMessages": ["end-of-call-report"],
  "serverUrl": "https://your-actual-render-url.render.com/webhook"
}
```

**Important**: Replace `your-actual-render-url` with your actual Render deployment URL.

## 📡 Step 3: Webhook Payload Format

Your webhook will receive POST requests with this structure:

```json
{
  "type": "end-of-call-report",
  "call": {
    "id": "call_abc123",
    "created_at": "2024-01-15T14:30:00Z",
    "duration": 185,
    "status": "completed",
    "type": "inbound",
    "from": "+14165550123",
    "to": "+18885551234"
  },
  "analysis": {
    "summary": "Customer Sarah Wilson called to schedule an oil change...",
    "structuredData": {
      "customer_name": "Sarah Wilson",
      "customer_email": "sarah.wilson@email.com",
      "customer_phone": "416-555-0123",
      "caller_intent": "Oil Change",
      "vehicle_make": "Toyota",
      "vehicle_model": "Camry",
      "vehicle_km": "45000",
      "service_requested": "Oil Change + Brake Inspection",
      "customer_notes": "Slight squeaking noise during braking"
    },
    "successEvaluation": "true"
  },
  "timestamp": "2024-01-15T14:30:15Z"
}
```

## 🚀 Step 4: Deploy Updated Code

1. **Update Environment Variables** in Render Dashboard:
   ```
   GOOGLE_SHEET_ID=your_google_sheet_id_here
   GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
   SHEET_NAME=Raw
   ```

2. **Deploy the updated code** to Render (it should auto-deploy from GitHub)

3. **Test the webhook** using the `/test` endpoint with new format payloads

## 🧪 Step 5: Testing

### Local Testing

Use the provided test payloads:

```bash
# Test normal call
curl -X POST http://localhost:8080/test \
  -H "Content-Type: application/json" \
  -d @test_payload_vapi_format.json

# Test emergency call  
curl -X POST http://localhost:8080/test \
  -H "Content-Type: application/json" \
  -d @test_emergency_payload_vapi.json
```

### Production Testing

1. **Make a test call** to your VAPI phone number
2. **Check Render logs** to see if webhook is received
3. **Verify Google Sheet** is populated with call data
4. **Check health endpoint**: `https://your-app.render.com/health`

## 📊 Step 6: Google Sheets Column Mapping

The webhook will populate these columns in your Google Sheet:

| Column | Source | Description |
|--------|--------|-------------|
| vapi_call_id | call.id | Unique call identifier |
| timestamp | call.created_at | When call was made |
| CallSummary | analysis.summary | AI-generated call summary |
| Name | analysis.structuredData.customer_name | Customer name |
| Email | analysis.structuredData.customer_email | Customer email |
| PhoneNumber | analysis.structuredData.customer_phone | Customer phone (formatted) |
| CallerIntent | analysis.structuredData.caller_intent | Service requested |
| VehicleMake | analysis.structuredData.vehicle_make | Vehicle make |
| VehicleModel | analysis.structuredData.vehicle_model | Vehicle model |
| VehicleKM | analysis.structuredData.vehicle_km | Vehicle mileage |
| escalation_status | Calculated | Auto-detected priority level |
| follow_up_due | Calculated | Auto-calculated follow-up date |
| call_duration | call.duration | Call length in seconds |
| call_status | call.status | Call completion status |
| success_evaluation | analysis.successEvaluation | AI success assessment |

## 🔧 Troubleshooting

### Common Issues

1. **No webhook received**: Check VAPI assistant serverUrl and serverMessages configuration
2. **Analysis missing**: Ensure analysisPlan is properly configured in assistant
3. **Google Sheets error**: Verify environment variables and service account permissions
4. **Wrong message type**: Webhook only processes "end-of-call-report" messages

### Debug Steps

1. **Check Render logs**: Look for webhook payload details
2. **Test health endpoint**: Verify Google Sheets connectivity
3. **Use test endpoint**: Validate parsing with sample payloads
4. **Check VAPI logs**: Verify assistant is sending webhooks

## 🎉 Success Indicators

When properly configured, you should see:

- ✅ **Webhook receives** `end-of-call-report` messages after each call
- ✅ **Call summaries** are automatically generated by AI
- ✅ **Structured data** is extracted and validated
- ✅ **Google Sheets** is populated with formatted call data
- ✅ **Escalations** are automatically detected and flagged
- ✅ **Follow-up dates** are calculated based on call intent

## 📞 Support

If you encounter issues:

1. Check the Render deployment logs
2. Verify the VAPI assistant configuration
3. Test with the provided sample payloads
4. Ensure Google Sheets service account has proper permissions

The system is now ready to automatically capture and log all VAPI call summaries! 