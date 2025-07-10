#!/usr/bin/env python3
"""
PRig Web Application
Web interface for controlling the automatic printer test rig.
"""

import os
import sys
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_socketio import SocketIO, emit
import subprocess

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from printer_detection import PrinterDetector, PrinterInfo
from printer_test import PrinterTestRig
from utils import setup_logging, load_config, get_system_info


app = Flask(__name__)
app.config['SECRET_KEY'] = 'prig-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
printer_status = {
    'connected_printers': [],
    'active_tests': {},
    'system_status': 'idle',
    'last_updated': datetime.now().isoformat()
}

test_threads = {}
stop_flags = {}
logger = setup_logging()


class WebControlledPrinterRig:
    """Web-controlled version of the printer test rig."""
    
    def __init__(self):
        self.detector = PrinterDetector()
        self.config = load_config()
        self.logger = logger
        
    def start_continuous_test(self, printer_info: dict, test_id: str):
        """Start continuous testing for a printer."""
        from test_image_data import save_embedded_test_image
        import tempfile
        
        printer = PrinterInfo(**printer_info)
        
        # Setup printer in CUPS
        self.setup_printer_in_cups(printer)
        
        # Use only embedded PNG test image
        temp_dir = Path(tempfile.mkdtemp())
        test_image_path = temp_dir / "embedded_test_image.png"
        save_embedded_test_image(test_image_path)
        test_images = [(test_image_path, "4x6 PNG Test Image")]
        
        cycle_count = 0
        stop_flag = stop_flags.get(test_id, {'stop': False})
        
        socketio.emit('test_started', {
            'test_id': test_id,
            'printer': printer_info,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            while not stop_flag['stop'] and self.is_printer_connected(printer):
                cycle_count += 1
                
                socketio.emit('cycle_started', {
                    'test_id': test_id,
                    'cycle': cycle_count,
                    'timestamp': datetime.now().isoformat()
                })
                
                for i, (image_path, description) in enumerate(test_images):
                    if stop_flag['stop']:
                        break
                        
                    socketio.emit('print_started', {
                        'test_id': test_id,
                        'cycle': cycle_count,
                        'image': i + 1,
                        'description': description,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    success = self.print_image(printer, image_path)
                    
                    socketio.emit('print_completed', {
                        'test_id': test_id,
                        'cycle': cycle_count,
                        'image': i + 1,
                        'description': description,
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    if not success:
                        time.sleep(10)
                        continue
                        
                    time.sleep(5)
                
                if not stop_flag['stop']:
                    socketio.emit('cycle_completed', {
                        'test_id': test_id,
                        'cycle': cycle_count,
                        'timestamp': datetime.now().isoformat()
                    })
                    time.sleep(30)
                    
        except Exception as e:
            socketio.emit('test_error', {
                'test_id': test_id,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        finally:
            socketio.emit('test_stopped', {
                'test_id': test_id,
                'cycles_completed': cycle_count,
                'timestamp': datetime.now().isoformat()
            })
            
            # Cleanup
            generator.cleanup()
            if test_id in test_threads:
                del test_threads[test_id]
            if test_id in stop_flags:
                del stop_flags[test_id]
                
    def setup_printer_in_cups(self, printer: PrinterInfo):
        """Setup printer in CUPS."""
        try:
            # Remove existing printer
            subprocess.run(['lpadmin', '-x', printer.cups_name], 
                          capture_output=True, text=True)
            
            # Add printer
            cmd = [
                'lpadmin', '-p', printer.cups_name, '-E',
                '-v', printer.device_uri, '-m', printer.ppd_file,
                '-L', f"PRig Web - {printer.model}",
                '-D', f"Web-controlled {printer.model}"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Failed to setup printer: {result.stderr}")
                
            subprocess.run(['lpoptions', '-d', printer.cups_name], 
                          capture_output=True, text=True)
                          
        except Exception as e:
            self.logger.error(f"Error setting up printer: {e}")
            raise
            
    def print_image(self, printer: PrinterInfo, image_path: Path) -> bool:
        """Print an image."""
        try:
            # Get printer-specific print options
            options = self.get_print_options(printer)
            
            cmd = [
                'lp', '-d', printer.cups_name,
                '-o', 'fit-to-page'
            ]
            
            # Add printer-specific options
            for option in options:
                cmd.extend(['-o', option])
                
            cmd.append(str(image_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                job_id = result.stdout.strip().split()[-1]
                return self.wait_for_print_completion(job_id)
            else:
                self.logger.error(f"Print failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error printing: {e}")
            return False
            
    def wait_for_print_completion(self, job_id: str, timeout: int = 120) -> bool:
        """Wait for print job completion."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = subprocess.run(['lpstat', '-W', 'completed', '-o', job_id], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and job_id in result.stdout:
                return True
                
            result = subprocess.run(['lpstat', '-o', job_id], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return False
                
            time.sleep(2)
            
        return False
        
    def get_print_options(self, printer: PrinterInfo) -> List[str]:
        """Get printer-specific print options."""
        options = []
        
        # Use minimal options for DNP printers with raw driver
        if printer.model.startswith('DNP'):
            # DNP printers with raw driver need minimal options
            options.extend([
                'media=w288h432',  # 4x6 size in points
                'fit-to-page'
            ])
        else:
            # Canon and other printers
            options.extend([
                'media=4x6',
                'ColorModel=RGB',
                'quality=5'
            ])
            
        return options
        
    def is_printer_connected(self, printer: PrinterInfo) -> bool:
        """Check if printer is connected."""
        try:
            usb_devices = self.detector.get_connected_printers()
            
            for device in usb_devices:
                if (device.vendor_id == printer.vendor_id and 
                    device.product_id == printer.product_id):
                    return True
                    
            return False
            
        except Exception:
            return False


# Initialize the rig
rig = WebControlledPrinterRig()


def update_printer_status():
    """Background task to update printer status."""
    while True:
        try:
            connected_printers = rig.detector.get_connected_printers()
            
            printer_status['connected_printers'] = [
                {
                    'name': p.name,
                    'model': p.model,
                    'vendor': p.vendor,
                    'device_uri': p.device_uri,
                    'cups_name': p.cups_name,
                    'ppd_file': p.ppd_file,
                    'usb_device': p.usb_device,
                    'vendor_id': p.vendor_id,
                    'product_id': p.product_id
                } for p in connected_printers
            ]
            
            printer_status['active_tests'] = {
                tid: {
                    'active': tid in test_threads and test_threads[tid].is_alive(),
                    'stopped': stop_flags.get(tid, {}).get('stop', False)
                } for tid in test_threads.keys()
            }
            
            printer_status['system_status'] = 'active' if test_threads else 'idle'
            printer_status['last_updated'] = datetime.now().isoformat()
            
            socketio.emit('status_update', printer_status)
            
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            
        time.sleep(5)


# Start background status updater
status_thread = threading.Thread(target=update_printer_status, daemon=True)
status_thread.start()


@app.route('/')
def index():
    """Main dashboard."""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get current system status."""
    return jsonify(printer_status)


@app.route('/api/printers')
def api_printers():
    """Get connected printers."""
    return jsonify(printer_status['connected_printers'])


@app.route('/api/start_test', methods=['POST'])
def api_start_test():
    """Start a test for a specific printer."""
    data = request.json or {}
    printer_info = data.get('printer')
    
    if not printer_info:
        return jsonify({'error': 'No printer specified'}), 400
    
    test_id = f"test_{printer_info['cups_name']}_{int(time.time())}"
    
    if test_id in test_threads:
        return jsonify({'error': 'Test already running for this printer'}), 400
    
    stop_flags[test_id] = {'stop': False}
    
    thread = threading.Thread(
        target=rig.start_continuous_test,
        args=(printer_info, test_id),
        daemon=True
    )
    
    test_threads[test_id] = thread
    thread.start()
    
    return jsonify({
        'success': True,
        'test_id': test_id,
        'message': f'Test started for {printer_info["name"]}'
    })


@app.route('/api/stop_test', methods=['POST'])
def api_stop_test():
    """Stop a running test."""
    data = request.json or {}
    test_id = data.get('test_id')
    
    if not test_id or test_id not in stop_flags:
        return jsonify({'error': 'Invalid test ID'}), 400
    
    stop_flags[test_id]['stop'] = True
    
    return jsonify({
        'success': True,
        'message': 'Test stop requested'
    })


@app.route('/api/system_info')
def api_system_info():
    """Get system information."""
    return jsonify(get_system_info())


@app.route('/api/logs')
def api_logs():
    """Get recent log entries."""
    try:
        log_file = Path('/var/log/prig/prig.log')
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Return last 100 lines
                return jsonify({'logs': lines[-100:]})
        else:
            return jsonify({'logs': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration."""
    if request.method == 'GET':
        return jsonify(rig.config)
    
    elif request.method == 'POST':
        try:
            new_config = request.json
            if not new_config:
                return jsonify({'error': 'No configuration data provided'}), 400
                
            # Save configuration
            from utils import save_config
            
            if save_config(new_config):
                rig.config = new_config
                return jsonify({'success': True, 'message': 'Configuration updated'})
            else:
                return jsonify({'error': 'Failed to save configuration'}), 500
                
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('status_update', printer_status)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    pass


if __name__ == '__main__':
    # Run the web app
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)