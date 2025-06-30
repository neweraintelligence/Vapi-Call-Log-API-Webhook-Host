import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Import after app creation to avoid circular imports
try:
    from .parser import VapiCallParser
    from .sheet_writer import SheetWriter
except ImportError:
    # For Render deployment
    from parser import VapiCallParser
    from sheet_writer import SheetWriter

# Initialize components
parser = VapiCallParser()
sheet_writer = SheetWriter()

@app.route('/webhook', methods=['POST'])
def handle_vapi_webhook():
    """
    Main webhook endpoint for Vapi end-of-call reports
    """
    try:
        # Validate request
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        payload = request.get_json()
        
        # Log the raw payload for debugging
        logger.info(f"Received webhook payload: {json.dumps(payload, indent=2)}")
        
        # Check if this is an end-of-call-report message
        message_type = payload.get('type', payload.get('message', {}).get('type', ''))
        
        if message_type != 'end-of-call-report':
            logger.info(f"Ignoring non-end-of-call-report message: {message_type}")
            return jsonify({
                "status": "ignored",
                "message_type": message_type,
                "info": "Only processing end-of-call-report messages"
            }), 200
        
        # Extract call ID and agent ID for logging
        call_id = payload.get('call', {}).get('id') or payload.get('message', {}).get('call', {}).get('id', 'unknown')
        agent_id = payload.get('call', {}).get('assistant', {}).get('id') or payload.get('message', {}).get('call', {}).get('assistant', {}).get('id', 'unknown')
        
        logger.info(f"Processing end-of-call-report for call: {call_id}, agent: {agent_id}")
        
        # Parse the payload into flat dict
        parsed_data = parser.parse_call_data(payload)
        
        # Write to appropriate Google Sheet based on agent
        sheet_writer.append_call_data(parsed_data, agent_id)
        
        logger.info(f"Successfully processed call: {parsed_data.get('vapi_call_id')} for agent: {agent_id}")
        
        return jsonify({
            "status": "success",
            "call_id": parsed_data.get('vapi_call_id'),
            "agent_id": agent_id,
            "timestamp": parsed_data.get('timestamp'),
            "message_type": message_type
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        logger.error(f"Payload causing error: {json.dumps(payload, indent=2) if 'payload' in locals() else 'N/A'}")
        
        # Send alert for critical failures
        # TODO: Implement Slack/email alerting
        
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    # Basic app health
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "vapi-call-log-multi-agent",
        "agents_configured": {
            "agent1_id": os.environ.get('AGENT1_ID', 'Not configured'),
            "agent2_id": os.environ.get('AGENT2_ID', 'Not configured')
        }
    }
    
    # Check Google Sheets connectivity
    try:
        sheets_health = sheet_writer.health_check()
        health_status["google_sheets"] = sheets_health
        
        # Overall status depends on all components
        if sheets_health.get("status") == "error":
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["google_sheets"] = {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Return appropriate HTTP status code
    status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
    
    return jsonify(health_status), status_code

@app.route('/test', methods=['POST'])
def test_endpoint():
    """Test endpoint for manual payload testing"""
    try:
        payload = request.get_json()
        parsed_data = parser.parse_call_data(payload)
        
        return jsonify({
            "status": "test_success",
            "parsed_data": parsed_data
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "test_error",
            "message": str(e)
        }), 400

# Cloud Function entrypoint
def main(request):
    """Google Cloud Function entrypoint"""
    with app.app_context():
        return app.full_dispatch_request()

if __name__ == '__main__':
    # For local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 