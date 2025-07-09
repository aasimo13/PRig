#!/usr/bin/env python3
"""
Test version of PRig Web App for local development
"""

import os
import sys
import tempfile
from pathlib import Path

# Create temp directories for testing
temp_dir = Path(tempfile.mkdtemp(prefix="prig_test_"))
log_dir = temp_dir / "logs"
config_dir = temp_dir / "config"

log_dir.mkdir(exist_ok=True)
config_dir.mkdir(exist_ok=True)

print(f"Using temp directories:")
print(f"  Logs: {log_dir}")
print(f"  Config: {config_dir}")

# Mock the paths in utils
sys.path.insert(0, 'src')
import utils

# Patch the logging setup to use temp directory
original_setup_logging = utils.setup_logging

def mock_setup_logging(log_level='INFO'):
    import logging
    logger = logging.getLogger('PRig')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler only for testing
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger

utils.setup_logging = mock_setup_logging

# Mock config paths
utils.load_config = lambda path=None: {
    'log_level': 'INFO',
    'test_images': {'formats': ['JPEG'], 'quality': 95, 'resolution': [1800, 1200]},
    'printer_settings': {'timeout': 120, 'retry_attempts': 3, 'print_delay': 5}
}

# Now import and test the web app
try:
    from web_app import app, socketio
    print("✅ Web app imported successfully")
    
    # Test basic functionality
    with app.test_client() as client:
        response = client.get('/')
        print(f"✅ Home page status: {response.status_code}")
        
        response = client.get('/api/status')
        print(f"✅ API status: {response.status_code}")
        
        response = client.get('/api/printers')
        print(f"✅ API printers: {response.status_code}")
        
    print("✅ All web app tests passed!")
    print(f"\nTo test the web interface:")
    print(f"1. Run: cd src && python3 ../test_web_app.py")
    print(f"2. Open: http://localhost:5000")
    print(f"3. Note: Printer detection won't work on macOS (requires Linux USB tools)")
    
except Exception as e:
    print(f"❌ Web app test failed: {e}")
    import traceback
    traceback.print_exc()

if __name__ == "__main__":
    print("\nStarting test web server...")
    print("Open http://localhost:5000 in your browser")
    print("Press Ctrl+C to stop")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)