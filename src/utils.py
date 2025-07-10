#!/usr/bin/env python3
"""
Utilities for PRig - Logging, configuration, and helper functions.
"""

import logging
import logging.handlers
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def setup_logging(log_level: str = 'INFO') -> logging.Logger:
    """Set up logging configuration for PRig."""
    
    # Create logs directory if it doesn't exist
    log_dir = Path('/var/log/prig')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure logging
    logger = logging.getLogger('PRig')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    
    # File handler for detailed logging
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'prig.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Console handler for important messages
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # System log handler for systemd integration
    try:
        syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
        syslog_handler.setLevel(logging.INFO)
        syslog_handler.setFormatter(logging.Formatter('PRig: %(message)s'))
        logger.addHandler(syslog_handler)
    except Exception:
        # Syslog not available, continue without it
        pass
    
    return logger


def get_printer_capabilities(printer_name: str) -> Dict[str, Any]:
    """Get printer capabilities from CUPS."""
    import subprocess
    
    capabilities = {
        'paper_sizes': [],
        'media_types': [],
        'quality_levels': [],
        'color_modes': []
    }
    
    try:
        result = subprocess.run(['lpoptions', '-p', printer_name, '-l'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            capabilities = _parse_printer_capabilities(result.stdout)
            
    except Exception as e:
        logging.getLogger('PRig').error(f"Error getting printer capabilities: {e}")
        
    return capabilities


def _parse_printer_capabilities(options_output: str) -> Dict[str, Any]:
    """Parse lpoptions output to extract printer capabilities."""
    import re
    
    capabilities = {
        'paper_sizes': [],
        'media_types': [],
        'quality_levels': [],
        'color_modes': []
    }
    
    for line in options_output.splitlines():
        line = line.strip()
        
        if line.startswith('PageSize/'):
            # Extract available paper sizes
            matches = re.findall(r'(\w+x\w+|\w+)', line)
            capabilities['paper_sizes'].extend(matches)
            
        elif line.startswith('MediaType/'):
            # Extract media types
            if ':' in line:
                options_part = line.split(':', 1)[1]
                matches = re.findall(r'(\w+)', options_part)
                capabilities['media_types'].extend(matches)
                
        elif line.startswith('Quality/') or line.startswith('PrintQuality/'):
            # Extract quality levels
            if ':' in line:
                options_part = line.split(':', 1)[1]
                matches = re.findall(r'(\w+)', options_part)
                capabilities['quality_levels'].extend(matches)
                
        elif line.startswith('ColorModel/'):
            # Extract color modes
            if ':' in line:
                options_part = line.split(':', 1)[1]
                matches = re.findall(r'(\w+)', options_part)
                capabilities['color_modes'].extend(matches)
    
    return capabilities


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    if config_path is None:
        config_path = '/etc/prig/config.json'
    
    default_config = {
        'log_level': 'INFO',
        'test_images': {
            'formats': ['PNG'],
            'resolution': [1800, 1200]
        },
        'printer_settings': {
            'timeout': 120,
            'retry_attempts': 3,
            'print_delay': 5
        },
        'supported_printers': {
            'canon_selphy': {
                'vendor_id': '04a9',
                'models': ['CP1300', 'CP1500', 'CP910']
            },
            'dnp_qw410': {
                'vendor_id': '1343',
                'product_id': '0003'
            }
        }
    }
    
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge with default config
                config = {**default_config, **user_config}
        else:
            config = default_config
            
    except Exception as e:
        logging.getLogger('PRig').error(f"Error loading config: {e}")
        config = default_config
    
    return config


def save_config(config: Dict[str, Any], config_path: Optional[str] = None) -> bool:
    """Save configuration to JSON file."""
    if config_path is None:
        config_path = '/etc/prig/config.json'
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        return True
        
    except Exception as e:
        logging.getLogger('PRig').error(f"Error saving config: {e}")
        return False


def create_test_report(test_results: list, output_path: Optional[str] = None) -> str:
    """Create a test report from test results."""
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'/var/log/prig/test_report_{timestamp}.json'
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_results': test_results,
        'summary': {
            'total_tests': len(test_results),
            'passed': sum(1 for r in test_results if r.get('status') == 'success'),
            'failed': sum(1 for r in test_results if r.get('status') == 'failed')
        }
    }
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return output_path
        
    except Exception as e:
        logging.getLogger('PRig').error(f"Error creating test report: {e}")
        return ""


def check_system_requirements() -> Dict[str, bool]:
    """Check if system has required dependencies."""
    requirements = {
        'cups': False,
        'lp': False,
        'lpadmin': False,
        'lpstat': False,
        'lsusb': False,
        'python3': False,
        'pillow': False
    }
    
    import subprocess
    import importlib.util
    
    # Check command line tools
    commands = ['cups', 'lp', 'lpadmin', 'lpstat', 'lsusb', 'python3']
    
    for cmd in commands:
        try:
            result = subprocess.run(['which', cmd], 
                                  capture_output=True, text=True)
            requirements[cmd] = result.returncode == 0
        except Exception:
            requirements[cmd] = False
    
    # Check Python packages
    try:
        spec = importlib.util.find_spec('PIL')
        requirements['pillow'] = spec is not None
    except Exception:
        requirements['pillow'] = False
    
    return requirements


def install_dependencies() -> bool:
    """Install required system dependencies."""
    import subprocess
    
    logger = logging.getLogger('PRig')
    
    try:
        # Update package list
        logger.info("Updating package lists...")
        subprocess.run(['apt-get', 'update'], check=True)
        
        # Install required packages
        packages = [
            'cups',
            'cups-client',
            'printer-driver-gutenprint',
            'python3-pip',
            'python3-dev',
            'usbutils'
        ]
        
        logger.info(f"Installing packages: {', '.join(packages)}")
        subprocess.run(['apt-get', 'install', '-y'] + packages, check=True)
        
        # Install Python packages
        python_packages = ['Pillow', 'numpy']
        
        logger.info(f"Installing Python packages: {', '.join(python_packages)}")
        subprocess.run(['pip3', 'install'] + python_packages, check=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Error installing dependencies: {e}")
        return False


def get_system_info() -> Dict[str, Any]:
    """Get system information for debugging."""
    import subprocess
    import platform
    
    info = {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'cups_version': '',
        'usb_devices': [],
        'printer_queues': []
    }
    
    try:
        # Get CUPS version
        result = subprocess.run(['cups-config', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            info['cups_version'] = result.stdout.strip()
            
        # Get USB devices
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode == 0:
            info['usb_devices'] = result.stdout.splitlines()
            
        # Get printer queues
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode == 0:
            info['printer_queues'] = result.stdout.splitlines()
            
    except Exception as e:
        logging.getLogger('PRig').error(f"Error getting system info: {e}")
    
    return info


def cleanup_temp_files(temp_dir: Optional[str] = None) -> None:
    """Clean up temporary files created during testing."""
    import shutil
    
    if temp_dir is None:
        temp_dir = '/tmp/prig_*'
    
    try:
        import glob
        for path in glob.glob(temp_dir):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
                
    except Exception as e:
        logging.getLogger('PRig').error(f"Error cleaning up temp files: {e}")


def validate_image_file(image_path: str) -> bool:
    """Validate that an image file is valid and readable."""
    try:
        from PIL import Image
        
        if not os.path.exists(image_path):
            return False
            
        with Image.open(image_path) as img:
            img.verify()
            
        return True
        
    except Exception:
        return False


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{int(minutes)}m {int(secs)}s"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)}h {int(minutes)}m"