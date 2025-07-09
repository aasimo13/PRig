#!/usr/bin/env python3
"""
PRig - Automatic Printer Test Program
Automatically prints test photos when USB photo printers are connected.
"""

import sys
import os
import time
import logging
import subprocess
import urllib.request
import urllib.parse
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from printer_detection import PrinterDetector, PrinterInfo
from test_image_generator import TestImageGenerator
from utils import setup_logging, get_printer_capabilities


class PrinterTestRig:
    """Main class for the automatic printer test rig."""
    
    def __init__(self, test_image_url: Optional[str] = None):
        self.logger = setup_logging()
        self.detector = PrinterDetector()
        self.image_generator = TestImageGenerator()
        self.test_results = []
        self.test_image_url = test_image_url
        self.temp_dir = Path("/tmp/prig_test_images")
        self.temp_dir.mkdir(exist_ok=True)
        
    def run(self) -> None:
        """Main execution method."""
        self.logger.info("PRig starting - scanning for USB printers...")
        
        try:
            printers = self.detector.get_connected_printers()
            
            if not printers:
                self.logger.info("No supported printers found")
                return
                
            for printer in printers:
                self.logger.info(f"Found printer: {printer.name} ({printer.model})")
                self.test_printer(printer)
                
        except Exception as e:
            self.logger.error(f"Error during printer testing: {e}")
            sys.exit(1)
            
    def test_printer(self, printer: PrinterInfo) -> None:
        """Test a specific printer with comprehensive test images - continuous printing."""
        self.logger.info(f"Starting continuous test sequence for {printer.name}")
        
        try:
            # Setup printer in CUPS
            self.setup_printer_in_cups(printer)
            
            # Get test images (from URL or generated)
            test_images = self.get_test_images(printer)
            
            cycle_count = 0
            
            # Continuous printing until printer is disconnected
            while self.is_printer_connected(printer):
                cycle_count += 1
                self.logger.info(f"Starting print cycle {cycle_count} for {printer.name}")
                
                for image_path, description in test_images:
                    # Check if printer is still connected before each print
                    if not self.is_printer_connected(printer):
                        self.logger.info(f"Printer {printer.name} disconnected, stopping test sequence")
                        return
                    
                    self.logger.info(f"Printing test: {description} (cycle {cycle_count})")
                    success = self.print_image(printer, image_path)
                    
                    if success:
                        self.logger.info(f"Successfully printed: {description}")
                    else:
                        self.logger.error(f"Failed to print: {description}")
                        # If print fails, wait a bit and check connection
                        time.sleep(10)
                        continue
                    
                    # Wait between prints to avoid printer overload
                    time.sleep(5)
                    
                # Wait between complete cycles
                self.logger.info(f"Completed print cycle {cycle_count}, waiting before next cycle...")
                time.sleep(30)
                
            self.logger.info(f"Printer {printer.name} disconnected after {cycle_count} cycles")
            
        except Exception as e:
            self.logger.error(f"Error testing printer {printer.name}: {e}")
            
    def is_printer_connected(self, printer: PrinterInfo) -> bool:
        """Check if printer is still connected via USB."""
        try:
            # Check if USB device is still present
            usb_devices = self.detector.get_connected_printers()
            
            for device in usb_devices:
                if (device.vendor_id == printer.vendor_id and 
                    device.product_id == printer.product_id):
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking printer connection: {e}")
            return False
            
    def setup_printer_in_cups(self, printer: PrinterInfo) -> None:
        """Configure printer in CUPS for testing."""
        self.logger.info(f"Setting up printer {printer.name} in CUPS")
        
        # Remove existing printer if it exists
        subprocess.run(['lpadmin', '-x', printer.cups_name], 
                      capture_output=True, text=True)
        
        # Add printer to CUPS
        cmd = [
            'lpadmin',
            '-p', printer.cups_name,
            '-E',
            '-v', printer.device_uri,
            '-m', printer.ppd_file,
            '-L', f"PRig Test Rig - {printer.model}",
            '-D', f"Auto-detected {printer.model}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to setup printer in CUPS: {result.stderr}")
            
        # Set printer as default temporarily
        subprocess.run(['lpoptions', '-d', printer.cups_name], 
                      capture_output=True, text=True)
        
        # Verify printer is ready
        self._verify_printer_status(printer)
        
        self.logger.info(f"Printer {printer.name} configured successfully")
    
    def _verify_printer_status(self, printer: PrinterInfo) -> None:
        """Verify printer status and readiness."""
        try:
            # Check printer status
            result = subprocess.run(['lpstat', '-p', printer.cups_name], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                status = result.stdout.strip()
                self.logger.info(f"Printer status: {status}")
                
                if 'disabled' in status.lower():
                    self.logger.warning(f"Printer {printer.cups_name} is disabled")
                    # Try to enable it
                    subprocess.run(['cupsenable', printer.cups_name], 
                                 capture_output=True, text=True)
                    
            # Check if printer accepts jobs
            result = subprocess.run(['lpstat', '-a', printer.cups_name], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                accept_status = result.stdout.strip()
                self.logger.info(f"Job acceptance status: {accept_status}")
                
                if 'not accepting' in accept_status.lower():
                    self.logger.warning(f"Printer {printer.cups_name} not accepting jobs")
                    # Try to make it accept jobs
                    subprocess.run(['cupsaccept', printer.cups_name], 
                                 capture_output=True, text=True)
                    
        except Exception as e:
            self.logger.warning(f"Could not verify printer status: {e}")
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format and scheme."""
        try:
            parsed = urllib.parse.urlparse(url)
            return parsed.scheme in ['http', 'https'] and parsed.netloc
        except Exception:
            return False
    
    def _convert_google_drive_url(self, url: str) -> str:
        """Convert Google Drive sharing URL to direct download URL."""
        # Handle both old and new Google Drive URL formats
        if "drive.google.com" not in url:
            raise ValueError("Not a Google Drive URL")
        
        # Extract file ID using regex to handle various URL formats
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',  # Standard sharing link
            r'id=([a-zA-Z0-9_-]+)',       # Direct link format
            r'/d/([a-zA-Z0-9_-]+)',       # Short format
        ]
        
        file_id = None
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                file_id = match.group(1)
                break
        
        if not file_id:
            raise ValueError("Could not extract file ID from Google Drive URL")
        
        # Validate file ID format
        if not re.match(r'^[a-zA-Z0-9_-]+$', file_id):
            raise ValueError("Invalid file ID format")
        
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    def download_test_image(self, url: str) -> Path:
        """Download test image from URL."""
        try:
            # Validate URL format
            if not self._validate_url(url):
                raise ValueError(f"Invalid URL format: {url}")
            
            # Convert Google Drive sharing link to direct download link
            if "drive.google.com" in url:
                url = self._convert_google_drive_url(url)
                self.logger.info(f"Converted Google Drive link to direct download URL")
            
            self.logger.info(f"Downloading test image from {url}")
            
            # Determine file extension from URL or default to JPG
            if url.lower().endswith(('.jpg', '.jpeg')):
                filename = "test_image.jpg"
            elif url.lower().endswith('.png'):
                filename = "test_image.png"
            else:
                filename = "test_image.jpg"  # Default to JPG
                
            image_path = self.temp_dir / filename
            
            # Download the image
            urllib.request.urlretrieve(url, image_path)
            
            # Verify the downloaded file exists and has content
            if not image_path.exists() or image_path.stat().st_size == 0:
                raise Exception("Downloaded file is empty or does not exist")
            
            self.logger.info(f"Test image downloaded to {image_path}")
            return image_path
            
        except Exception as e:
            self.logger.error(f"Failed to download test image from {url}: {e}")
            raise
    
    def get_test_images(self, printer: PrinterInfo) -> List[Tuple[Path, str]]:
        """Get test images - use local test image."""
        # Use local test image
        local_image_path = Path(__file__).parent.parent / "test_images" / "test_image.jpg"
        
        if local_image_path.exists():
            self.logger.info(f"Using local test image: {local_image_path}")
            return [(local_image_path, "Local Test Image")]
        
        # Fallback to URL download if local image doesn't exist
        if self.test_image_url:
            try:
                image_path = self.download_test_image(self.test_image_url)
                return [(image_path, "Test Image from URL")]
            except Exception as e:
                self.logger.error(f"Failed to get test image from URL: {e}")
                raise Exception("Could not download test image from URL")
        
        raise Exception("No test image available (neither local nor URL)")
        
    def print_image(self, printer: PrinterInfo, image_path: Path) -> bool:
        """Print a test image to the specified printer."""
        try:
            # Check if image file exists
            if not image_path.exists():
                self.logger.error(f"Image file not found: {image_path}")
                return False
            
            # Get printer-specific print options
            options = self.get_print_options(printer)
            
            # Build print command with basic options
            cmd = [
                'lp',
                '-d', printer.cups_name,
                '-o', 'fit-to-page'
            ]
            
            # Add printer-specific options
            for option in options:
                cmd.extend(['-o', option])
                
            cmd.append(str(image_path))
            
            # Log the full command for debugging
            self.logger.info(f"Print command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Extract job ID from output
                output_lines = result.stdout.strip().split('\n')
                job_id = None
                for line in output_lines:
                    if 'request id is' in line:
                        job_id = line.split('request id is')[1].strip()
                        break
                
                if job_id:
                    self.logger.info(f"Print job {job_id} queued successfully")
                    return self.wait_for_print_completion(job_id)
                else:
                    self.logger.warning(f"Print job queued but no job ID found. Output: {result.stdout}")
                    return True  # Assume success if no job ID but command succeeded
            else:
                self.logger.error(f"Print command failed with return code {result.returncode}")
                self.logger.error(f"STDOUT: {result.stdout}")
                self.logger.error(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error printing image: {e}")
            return False
            
    def get_print_options(self, printer: PrinterInfo) -> List[str]:
        """Get printer-specific print options."""
        options = []
        
        # Use basic options that should work with raw driver
        options.extend([
            'media=4x6',
            'ColorModel=RGB'
        ])
        
        # Add printer-specific options if needed
        if printer.model.startswith('Canon'):
            options.extend([
                'quality=5'
            ])
        elif printer.model.startswith('DNP'):
            options.extend([
                'quality=5'
            ])
            
        return options
        
    def wait_for_print_completion(self, job_id: str, timeout: int = 120) -> bool:
        """Wait for print job to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check job status
            result = subprocess.run(['lpstat', '-o', job_id], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Print job {job_id} failed or not found")
                # Check CUPS error log for more details
                self._check_cups_error_log(job_id)
                return False
            
            # Parse job status
            job_status = result.stdout.strip()
            self.logger.info(f"Job {job_id} status: {job_status}")
            
            # Check if job is completed
            if 'completed' in job_status.lower():
                self.logger.info(f"Print job {job_id} completed successfully")
                return True
            
            # Check if job failed
            if any(status in job_status.lower() for status in ['aborted', 'canceled', 'stopped']):
                self.logger.error(f"Print job {job_id} failed with status: {job_status}")
                self._check_cups_error_log(job_id)
                return False
                
            time.sleep(2)
            
        self.logger.error(f"Print job {job_id} timed out")
        return False
    
    def _check_cups_error_log(self, job_id: str) -> None:
        """Check CUPS error log for job-specific errors."""
        try:
            result = subprocess.run(['grep', job_id, '/var/log/cups/error_log'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                self.logger.error(f"CUPS error log for job {job_id}:")
                for line in result.stdout.splitlines()[-5:]:  # Last 5 lines
                    self.logger.error(f"  {line}")
        except Exception as e:
            self.logger.warning(f"Could not check CUPS error log: {e}")


def main():
    """Main entry point."""
    if os.geteuid() != 0:
        print("This program must be run as root for proper USB device access")
        sys.exit(1)
    
    # Use your specific test image URL
    test_image_url = "https://drive.google.com/file/d/1rkatDCicnLhBlmG08WBGQgF-sbzEKxXK/view?usp=sharing"
    print(f"Using test image from URL: {test_image_url}")
    
    rig = PrinterTestRig(test_image_url=test_image_url)
    rig.run()


if __name__ == "__main__":
    main()