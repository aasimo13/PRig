#!/usr/bin/env python3
"""
Simple printer detection and test for PRig
Detect when printer is plugged in and print a test image
"""

import subprocess
import time
import sys
import os
from pathlib import Path

# Supported printer USB IDs
SUPPORTED_PRINTERS = {
    '04a9:327b': 'Canon SELPHY CP1300',
    '04a9:3302': 'Canon SELPHY CP1500', 
    '04a9:327a': 'Canon SELPHY CP910',
    '1343:0003': 'DNP QW410',
    '1452:9201': 'DNP Photo Printer'
}

def get_usb_printers():
    """Get connected supported USB printers"""
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        printers = []
        for line in result.stdout.splitlines():
            for usb_id, name in SUPPORTED_PRINTERS.items():
                if usb_id in line:
                    printers.append((usb_id, name))
                    print(f"✅ Found: {name} ({usb_id})")
        return printers
    except Exception as e:
        print(f"❌ Error checking USB: {e}")
        return []

def get_cups_printers():
    """Get available CUPS printers"""
    try:
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        printers = []
        for line in result.stdout.splitlines():
            if 'printer' in line and 'idle' in line:
                parts = line.split()
                if len(parts) >= 2:
                    printer_name = parts[1]
                    # Look for photo printers
                    if any(keyword in printer_name.lower() for keyword in ['qw410', 'canon', 'cp1500', 'selphy']):
                        printers.append(printer_name)
                        print(f"🖨️  Available: {printer_name}")
        return printers
    except Exception as e:
        print(f"❌ Error checking CUPS: {e}")
        return []

def create_test_image():
    """Create a simple test image"""
    test_image_path = Path('/tmp/prig_test.png')
    
    # Try to copy existing test image first
    existing_paths = [
        Path('/Users/aaronsimo/Documents/GitHub/PRig/test_images/test_image.jpg'),
        Path('/home/pi/PRig/test_images/test_image.jpg'),
        Path('./test_images/test_image.jpg')
    ]
    
    for path in existing_paths:
        if path.exists():
            subprocess.run(['cp', str(path), str(test_image_path)], check=False)
            if test_image_path.exists():
                print(f"✅ Using existing test image: {path}")
                return test_image_path
    
    # Create simple colored rectangle as fallback
    try:
        subprocess.run([
            'convert', '-size', '288x432', 'xc:red',
            '-pointsize', '24', '-fill', 'white',
            '-gravity', 'center', '-annotate', '0', 'PRig Test Image',
            str(test_image_path)
        ], check=False)
        
        if test_image_path.exists():
            print(f"✅ Created test image: {test_image_path}")
            return test_image_path
    except:
        pass
    
    print("❌ Cannot create test image")
    return None

def print_to_printer(printer_name, image_path):
    """Print image to specified printer"""
    try:
        print(f"🖨️  Printing to {printer_name}...")
        
        # Simple print command
        cmd = ['lp', '-d', printer_name, str(image_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Print job submitted to {printer_name}")
            return True
        else:
            print(f"❌ Print failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Print error: {e}")
        return False

def main():
    """Main loop - detect printers and print"""
    if os.geteuid() != 0:
        print("❌ Must run as root: sudo python3 simple_printer_test.py")
        return
    
    print("🔍 PRig Simple Printer Test")
    print("Waiting for printers...")
    
    known_printers = set()
    
    while True:
        try:
            # Check for USB printers
            usb_printers = get_usb_printers()
            
            # Check for CUPS printers
            cups_printers = get_cups_printers()
            
            # Look for new printers
            current_printers = set(cups_printers)
            new_printers = current_printers - known_printers
            
            if new_printers:
                print(f"\n🆕 New printer(s) detected: {new_printers}")
                
                # Create test image
                test_image = create_test_image()
                if test_image:
                    # Print to each new printer
                    for printer in new_printers:
                        print_to_printer(printer, test_image)
                        time.sleep(2)  # Wait between prints
                
                known_printers.update(new_printers)
            
            # Remove disconnected printers
            disconnected = known_printers - current_printers
            if disconnected:
                print(f"📤 Printer(s) disconnected: {disconnected}")
                known_printers -= disconnected
            
            time.sleep(3)  # Check every 3 seconds
            
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()