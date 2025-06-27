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
        
        # Validate webhook secret (if configured)
        webhook_secret = os.getenv('VAPI_WEBHOOK_SECRET')
        if webhook_secret:
            provided_secret = request.headers.get('X-Vapi-Secret')
            if provided_secret != webhook_secret:
                logger.error("Invalid webhook secret")
                return jsonify({"error": "Unauthorized"}), 401
        
        logger.info(f"Received webhook payload for call: {payload.get('call', {}).get('id', 'unknown')}")
        
        # Parse the payload into flat dict
        parsed_data = parser.parse_call_data(payload)
        
        # Write to Google Sheets
        sheet_writer.append_call_data(parsed_data)
        
        logger.info(f"Successfully processed call: {parsed_data.get('vapi_call_id')}")
        
        return jsonify({
            "status": "success",
            "call_id": parsed_data.get('vapi_call_id'),
            "timestamp": parsed_data.get('timestamp')
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        
        # Send alert for critical failures
        # TODO: Implement Slack/email alerting
        
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "vapi-call-log"
    }), 200

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