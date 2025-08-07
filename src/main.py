import os
import json
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import time
import threading
import requests

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

# In-memory cache for caller phone numbers by call ID
# Structure: { call_id: {"phone": str, "cached_at": epoch_seconds} }
_CALL_CACHE = {}
_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
_CACHE_LOCK = threading.Lock()


def _cleanup_call_cache() -> None:
    """Remove expired cache entries to bound memory usage."""
    now = time.time()
    with _CACHE_LOCK:
        expired_keys = [cid for cid, data in _CALL_CACHE.items() if now - data.get("cached_at", 0) > _CACHE_TTL_SECONDS]
        for cid in expired_keys:
            _CALL_CACHE.pop(cid, None)


def _cache_phone_number(call_id: str, phone: str) -> None:
    if not call_id or not phone:
        return
    with _CACHE_LOCK:
        _CALL_CACHE[call_id] = {"phone": phone, "cached_at": time.time()}
    logger.info(f"Cached phone for call {call_id}: {phone}")
    _cleanup_call_cache()


def _get_cached_phone_number(call_id: str) -> str:
    if not call_id:
        return ""
    with _CACHE_LOCK:
        entry = _CALL_CACHE.get(call_id)
    if not entry:
        return ""
    if time.time() - entry.get("cached_at", 0) > _CACHE_TTL_SECONDS:
        with _CACHE_LOCK:
            _CALL_CACHE.pop(call_id, None)
        return ""
    return entry.get("phone", "")


def _extract_phone_from_call_obj(call_obj: dict, payload: dict) -> str:
    """Try several likely paths to find a caller phone number and normalize/validate it."""
    call_obj = call_obj or {}
    # Candidate sources (ordered)
    candidates = [
        call_obj.get("customer", {}).get("number"),
        call_obj.get("from"),
        call_obj.get("caller"),
        call_obj.get("sourceNumber"),
        call_obj.get("destination", {}).get("callerId"),  # outbound
        payload.get("from"),
        payload.get("phone"),
    ]
    for candidate in candidates:
        if candidate and str(candidate).strip():
            formatted = parser._validate_phone(candidate)  # reuse parser validation/formatting
            if formatted and not formatted.startswith("INVALID:"):
                return formatted
    return ""


def _fetch_phone_from_vapi(call_id: str) -> str:
    """Optional REST fallback to retrieve phone from Vapi if API key is configured."""
    api_key = os.getenv("VAPI_PRIVATE_API_KEY")
    if not api_key or not call_id:
        return ""
    try:
        url = f"https://api.vapi.ai/call/{call_id}"
        resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=10)
        if resp.status_code != 200:
            logger.warning(f"Vapi GET /call failed ({resp.status_code}) for {call_id}")
            return ""
        data = resp.json() if resp.content else {}
        phone = (
            (data.get("customer") or {}).get("number")
            or (data.get("destination") or {}).get("callerId")
            or data.get("from")
        )
        if phone:
            formatted = parser._validate_phone(phone)
            return formatted if formatted and not formatted.startswith("INVALID:") else ""
        return ""
    except Exception as e:
        logger.warning(f"Vapi GET /call error for {call_id}: {e}")
        return ""

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
            # Proactively capture caller phone on status updates
            if message_type == 'status-update':
                call_obj = payload.get('call', payload.get('message', {}).get('call', {}))
                call_id_tmp = call_obj.get('id')
                phone = _extract_phone_from_call_obj(call_obj, payload)
                if phone:
                    _cache_phone_number(call_id_tmp, phone)
                    logger.info(f"Status update cached phone for call {call_id_tmp}")
                else:
                    logger.info(f"Status update had no phone fields for call {call_id_tmp}")
                return jsonify({
                    "status": "status-update-processed",
                    "message_type": message_type,
                }), 200

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

        # If phone not present from EoCR, try cache then REST fallback
        if not parsed_data.get('caller_phone_number'):
            cached_phone = _get_cached_phone_number(call_id)
            if cached_phone:
                parsed_data['caller_phone_number'] = cached_phone
                logger.info(f"Filled caller_phone_number from cache for call {call_id}: {cached_phone}")
            else:
                api_phone = _fetch_phone_from_vapi(call_id)
                if api_phone:
                    parsed_data['caller_phone_number'] = api_phone
                    _cache_phone_number(call_id, api_phone)
                    logger.info(f"Filled caller_phone_number from Vapi API for call {call_id}: {api_phone}")
        
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

@app.route('/debug', methods=['POST'])
def debug_webhook():
    """
    Debug endpoint to log raw VAPI payload
    """
    try:
        # Get raw payload
        payload = request.get_json()
        
        # Log the complete payload for debugging
        logger.info("=== DEBUG WEBHOOK PAYLOAD ===")
        logger.info(f"Raw payload: {json.dumps(payload, indent=2)}")
        
        # Extract call data for analysis
        call_data = payload.get('call', {})
        analysis_data = payload.get('analysis', {})
        
        logger.info("=== CALL DATA ANALYSIS ===")
        logger.info(f"Call fields: {list(call_data.keys())}")
        logger.info(f"Analysis fields: {list(analysis_data.keys())}")
        
        # Check for phone number fields
        phone_fields = []
        for key, value in call_data.items():
            if 'phone' in key.lower() or 'from' in key.lower() or 'caller' in key.lower():
                phone_fields.append(f"{key}: {value}")
        
        if phone_fields:
            logger.info(f"Phone-related fields found: {phone_fields}")
        else:
            logger.info("No phone-related fields found in call data")
        
        # Check structured data for phone
        structured_data = analysis_data.get('structuredData', {})
        if 'PhoneNumber' in structured_data:
            logger.info(f"PhoneNumber in structured data: {structured_data['PhoneNumber']}")
        else:
            logger.info("No PhoneNumber in structured data")
        
        logger.info("=== END DEBUG ===")
        
        return jsonify({
            "status": "debug_complete",
            "call_fields": list(call_data.keys()),
            "analysis_fields": list(analysis_data.keys()),
            "phone_fields_found": phone_fields
        }), 200
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}")
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
        "service": "vapi-call-log",
        "configuration": "single-sheet" if os.environ.get('GOOGLE_SHEET_ID') else "multi-agent"
    }
    
    # Add agent configuration info only for multi-agent setups
    if not os.environ.get('GOOGLE_SHEET_ID'):
        health_status["agents_configured"] = {
            "agent1_id": os.environ.get('AGENT1_ID', 'Not configured'),
            "agent2_id": os.environ.get('AGENT2_ID', 'Not configured')
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