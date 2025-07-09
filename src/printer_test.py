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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from printer_detection import PrinterDetector, PrinterInfo
from test_image_generator import TestImageGenerator
from utils import setup_logging, get_printer_capabilities


class PrinterTestRig:
    """Main class for the automatic printer test rig."""
    
    def __init__(self):
        self.logger = setup_logging()
        self.detector = PrinterDetector()
        self.image_generator = TestImageGenerator()
        self.test_results = []
        
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
            
            # Generate test images once
            test_images = self.image_generator.generate_test_suite(printer)
            
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
        
        self.logger.info(f"Printer {printer.name} configured successfully")
        
    def print_image(self, printer: PrinterInfo, image_path: Path) -> bool:
        """Print a test image to the specified printer."""
        try:
            # Get printer-specific print options
            options = self.get_print_options(printer)
            
            cmd = [
                'lp',
                '-d', printer.cups_name,
                '-o', 'fit-to-page',
                '-o', 'media=4x6',
                '-o', 'ColorModel=RGB',
                '-o', 'quality=5'
            ]
            
            # Add printer-specific options
            for option in options:
                cmd.extend(['-o', option])
                
            cmd.append(str(image_path))
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                job_id = result.stdout.strip().split()[-1]
                self.logger.info(f"Print job {job_id} queued successfully")
                return self.wait_for_print_completion(job_id)
            else:
                self.logger.error(f"Print command failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error printing image: {e}")
            return False
            
    def get_print_options(self, printer: PrinterInfo) -> List[str]:
        """Get printer-specific print options."""
        options = []
        
        if printer.model.startswith('Canon'):
            options.extend([
                'PageSize=4x6',
                'MediaType=PhotoPaper',
                'Quality=High'
            ])
        elif printer.model.startswith('DNP'):
            options.extend([
                'PageSize=4x6',
                'MediaType=Ribbon',
                'Quality=Fine'
            ])
            
        return options
        
    def wait_for_print_completion(self, job_id: str, timeout: int = 120) -> bool:
        """Wait for print job to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = subprocess.run(['lpstat', '-W', 'completed', '-o', job_id], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0 and job_id in result.stdout:
                self.logger.info(f"Print job {job_id} completed successfully")
                return True
                
            # Check if job failed
            result = subprocess.run(['lpstat', '-o', job_id], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"Print job {job_id} failed or not found")
                return False
                
            time.sleep(2)
            
        self.logger.error(f"Print job {job_id} timed out")
        return False


def main():
    """Main entry point."""
    if os.geteuid() != 0:
        print("This program must be run as root for proper USB device access")
        sys.exit(1)
        
    rig = PrinterTestRig()
    rig.run()


if __name__ == "__main__":
    main()