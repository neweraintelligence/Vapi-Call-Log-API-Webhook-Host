import os
import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename
import csv
from datetime import datetime
from threading import Thread
import pandas as pd

# Import our call manager
try:
    from .call_manager import CallManager, run_scheduler
except ImportError:
    from call_manager import CallManager, run_scheduler

logger = logging.getLogger(__name__)

class WebInterface:
    """
    Web interface for New Era AI cold outreach campaign management
    """
    
    def __init__(self, app: Flask):
        self.app = app
        self.call_manager = CallManager()
        self.upload_folder = os.path.join(os.getcwd(), 'uploads')
        
        # Ensure upload folder exists
        os.makedirs(self.upload_folder, exist_ok=True)
        
        # Configure Flask
        app.config['UPLOAD_FOLDER'] = self.upload_folder
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
        app.secret_key = os.getenv('FLASK_SECRET_KEY', 'new-era-ai-secret-key')
        
        # Start background scheduler
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register all Flask routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard"""
            try:
                status = self.call_manager.get_campaign_status()
                return render_template('dashboard.html', status=status)
            except Exception as e:
                logger.error(f"Dashboard error: {str(e)}")
                return render_template('dashboard.html', status={'error': str(e)})
        
        @self.app.route('/upload', methods=['GET', 'POST'])
        def upload_prospects():
            """Upload prospect list"""
            if request.method == 'GET':
                return render_template('upload.html')
            
            try:
                if 'file' not in request.files:
                    flash('No file selected', 'error')
                    return redirect(request.url)
                
                file = request.files['file']
                if file.filename == '':
                    flash('No file selected', 'error')
                    return redirect(request.url)
                
                if file and self._allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)
                    
                    # Process the uploaded file
                    result = self._process_uploaded_file(filepath)
                    
                    if result['success']:
                        flash(f"Successfully uploaded {result['count']} prospects", 'success')
                        return redirect(url_for('dashboard'))
                    else:
                        flash(f"Upload error: {result['error']}", 'error')
                        return redirect(request.url)
                
                else:
                    flash('Invalid file type. Please upload CSV or Excel files.', 'error')
                    return redirect(request.url)
                    
            except Exception as e:
                logger.error(f"Upload error: {str(e)}")
                flash(f'Upload failed: {str(e)}', 'error')
                return redirect(request.url)
        
        @self.app.route('/campaign/start', methods=['POST'])
        def start_campaign():
            """Start calling campaign"""
            try:
                data = request.get_json() or {}
                target_calls = data.get('target_calls')
                
                if target_calls:
                    target_calls = int(target_calls)
                
                result = self.call_manager.start_campaign(target_calls)
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Start campaign error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/campaign/stop', methods=['POST'])
        def stop_campaign():
            """Stop calling campaign"""
            try:
                result = self.call_manager.stop_campaign()
                return jsonify(result)
                
            except Exception as e:
                logger.error(f"Stop campaign error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/campaign/status')
        def campaign_status():
            """Get campaign status (API endpoint)"""
            try:
                status = self.call_manager.get_campaign_status()
                return jsonify(status)
                
            except Exception as e:
                logger.error(f"Campaign status error: {str(e)}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/prospects')
        def view_prospects():
            """View current prospect list"""
            try:
                prospects = self._get_prospects_from_sheet()
                return render_template('prospects.html', prospects=prospects)
                
            except Exception as e:
                logger.error(f"View prospects error: {str(e)}")
                return render_template('prospects.html', prospects=[], error=str(e))
        
        @self.app.route('/results')
        def view_results():
            """View call results and summaries"""
            try:
                results = self._get_call_results()
                return render_template('results.html', results=results)
                
            except Exception as e:
                logger.error(f"View results error: {str(e)}")
                return render_template('results.html', results=[], error=str(e))
        
        @self.app.route('/settings', methods=['GET', 'POST'])
        def settings():
            """Campaign settings"""
            if request.method == 'GET':
                current_settings = {
                    'calls_per_batch': self.call_manager.calls_per_batch,
                    'batch_interval_minutes': self.call_manager.batch_interval_minutes,
                    'vapi_phone_id': self.call_manager.vapi_phone_id,
                    'vapi_assistant_id': self.call_manager.vapi_assistant_id
                }
                return render_template('settings.html', settings=current_settings)
            else:
                try:
                    # Update settings
                    self.call_manager.calls_per_batch = int(request.form.get('calls_per_batch', 5))
                    self.call_manager.batch_interval_minutes = int(request.form.get('batch_interval_minutes', 5))
                    
                    flash('Settings updated successfully', 'success')
                    return redirect(url_for('settings'))
                    
                except Exception as e:
                    flash(f'Settings update failed: {str(e)}', 'error')
                    return redirect(url_for('settings'))
        
        # API endpoint to receive call summaries (from existing webhook)
        @self.app.route('/webhook/call-summary', methods=['POST'])
        def receive_call_summary():
            """Receive call summary and update campaign sheet"""
            try:
                payload = request.get_json()
                
                # Extract call ID and summary
                call_id = payload.get('call', {}).get('id') or payload.get('message', {}).get('call', {}).get('id')
                analysis = payload.get('analysis', {}) or payload.get('message', {}).get('analysis', {})
                call_summary = analysis.get('summary', '')
                
                # Extract caller phone number using the new method
                caller_phone_number = self.call_manager._extract_caller_phone_number(payload)
                
                if call_id and call_summary:
                    # Update the campaign sheet with summary and caller phone number
                    success = self.call_manager.update_call_summary(call_id, call_summary, caller_phone_number)
                    
                    response_data = {'status': 'success', 'call_id': call_id}
                    if caller_phone_number:
                        response_data['caller_phone_number'] = caller_phone_number
                    else:
                        response_data['caller_phone_number'] = 'not_found'
                    
                    if success:
                        return jsonify(response_data)
                    else:
                        return jsonify({'status': 'call_not_found', 'call_id': call_id})
                else:
                    return jsonify({'status': 'invalid_payload'}), 400
                    
            except Exception as e:
                logger.error(f"Webhook error: {str(e)}")
                return jsonify({'error': str(e)}), 500
    
    def _allowed_file(self, filename):
        """Check if file type is allowed"""
        allowed_extensions = {'csv', 'xlsx', 'xls'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
    
    def _process_uploaded_file(self, filepath: str) -> dict:
        """Process uploaded prospect file and add to Google Sheets"""
        try:
            # Read the file
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            # Validate required columns
            required_columns = ['name', 'phone_number']
            if not all(col in df.columns for col in required_columns):
                return {
                    'success': False,
                    'error': f'Missing required columns. Need: {required_columns}'
                }
            
            # Prepare data for sheets
            prospects = []
            for _, row in df.iterrows():
                prospect = {
                    'name': str(row['name']).strip(),
                    'phone_number': self._format_phone_number(str(row['phone_number'])),
                    'caller_phone_number': '',  # Will be filled when calls are received
                    'attempt_count': '0',
                    'status': 'QUEUED',
                    'last_called': '',
                    'next_call_time': '',
                    'call_summary': '',
                    'vapi_call_id': '',
                    'notes': str(row.get('notes', '')).strip()
                }
                prospects.append(prospect)
            
            # Add to Google Sheets
            self._add_prospects_to_sheet(prospects)
            
            # Clean up uploaded file
            os.remove(filepath)
            
            return {
                'success': True,
                'count': len(prospects)
            }
            
        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for calling"""
        import re
        
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Format as needed for VAPI (ensure proper format)
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        else:
            return f"+1{digits}"  # Best effort
    
    def _add_prospects_to_sheet(self, prospects: list):
        """Add prospects to Google Sheets"""
        try:
            self.call_manager._initialize_service()
            self.call_manager.ensure_headers()
            
            # Convert to row format
            rows = []
            for prospect in prospects:
                row = [prospect[header] for header in self.call_manager.headers]
                rows.append(row)
            
            # Append to sheet
            range_name = f"{self.call_manager.sheet_name}!A:J"
            body = {'values': rows}
            
            self.call_manager.service.spreadsheets().values().append(
                spreadsheetId=self.call_manager.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Added {len(prospects)} prospects to sheet")
            
        except Exception as e:
            logger.error(f"Failed to add prospects: {str(e)}")
            raise
    
    def _get_prospects_from_sheet(self) -> list:
        """Get current prospects from Google Sheets"""
        try:
            self.call_manager._initialize_service()
            
            range_name = f"{self.call_manager.sheet_name}!A:J"
            result = self.call_manager.service.spreadsheets().values().get(
                spreadsheetId=self.call_manager.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if len(values) <= 1:
                return []
            
            prospects = []
            for row in values[1:]:  # Skip header
                while len(row) < len(self.call_manager.headers):
                    row.append('')
                
                prospect = dict(zip(self.call_manager.headers, row))
                prospects.append(prospect)
            
            return prospects
            
        except Exception as e:
            logger.error(f"Failed to get prospects: {str(e)}")
            return []
    
    def _get_call_results(self) -> list:
        """Get call results with summaries"""
        try:
            prospects = self._get_prospects_from_sheet()
            
            # Filter for completed calls with summaries
            results = [
                p for p in prospects 
                if p.get('status') in ['COMPLETED', 'SUMMARY_RECEIVED'] 
                and p.get('call_summary')
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get results: {str(e)}")
            return []