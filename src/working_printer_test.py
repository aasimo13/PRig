#!/usr/bin/env python3
"""
Working printer test - uses idle printers and proper image format
"""

import subprocess
import time
import sys
import os
from pathlib import Path

def get_idle_printers():
    """Get only idle printers that can actually print"""
    try:
        result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        
        idle_printers = []
        for line in result.stdout.splitlines():
            if 'printer' in line and 'idle' in line and 'enabled' in line:
                parts = line.split()
                if len(parts) >= 2:
                    printer_name = parts[1]
                    # Focus on working printers only
                    if any(keyword in printer_name.lower() for keyword in ['qw410_4x6', 'qw410_4x4']):
                        idle_printers.append(printer_name)
                        print(f"✅ Found idle printer: {printer_name}")
        return idle_printers
    except Exception as e:
        print(f"❌ Error getting printers: {e}")
        return []

def create_simple_image():
    """Create a simple 4x6 image that should work"""
    image_path = Path('/tmp/simple_test.png')
    
    # Create a simple solid color image in 4x6 format
    try:
        # 4x6 inches at 72 DPI = 288x432 pixels
        subprocess.run([
            'convert', 
            '-size', '288x432', 
            'xc:blue',  # Blue background
            '-fill', 'white',
            '-pointsize', '36',
            '-gravity', 'center',
            '-annotate', '0', 'TEST\n4x6\nPRINT',
            str(image_path)
        ], check=True)
        
        if image_path.exists():
            print(f"✅ Created test image: {image_path}")
            return image_path
    except Exception as e:
        print(f"❌ ImageMagick failed: {e}")
    
    # Fallback: try to use existing image
    existing_paths = [
        '/Users/aaronsimo/Documents/GitHub/PRig/test_images/test_image.jpg',
        '/home/pi/PRig/test_images/test_image.jpg',
        './test_images/test_image.jpg'
    ]
    
    for path in existing_paths:
        if Path(path).exists():
            subprocess.run(['cp', path, str(image_path)], check=False)
            if image_path.exists():
                print(f"✅ Using existing image: {path}")
                return image_path
    
    print("❌ Cannot create test image")
    return None

def test_print(printer_name, image_path):
    """Test print with minimal options"""
    try:
        print(f"\n🖨️  Testing print to {printer_name}")
        
        # Clear any existing jobs for this printer
        subprocess.run(['cancel', '-a', printer_name], capture_output=True)
        time.sleep(1)
        
        # Simple print command - let printer handle sizing
        cmd = ['lp', '-d', printer_name, str(image_path)]
        print(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Print job submitted successfully")
            print(f"Output: {result.stdout}")
            
            # Wait a moment and check if job completed
            time.sleep(3)
            
            # Check job status
            job_result = subprocess.run(['lpstat', '-o'], capture_output=True, text=True)
            if printer_name in job_result.stdout:
                print(f"⏳ Job still processing...")
            else:
                print(f"✅ Job completed or printed")
            
            return True
        else:
            print(f"❌ Print failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error printing: {e}")
        return False

def main():
    """Main test function"""
    if os.geteuid() != 0:
        print("❌ Must run as root: sudo python3 working_printer_test.py")
        return
    
    print("🔍 Testing Working Printers")
    print("=" * 40)
    
    # Get idle printers
    printers = get_idle_printers()
    if not printers:
        print("❌ No idle printers found")
        return
    
    # Create test image
    image = create_simple_image()
    if not image:
        print("❌ Cannot create test image")
        return
    
    # Test each printer
    for printer in printers:
        success = test_print(printer, image)
        if success:
            print(f"✅ {printer} - SUCCESS")
        else:
            print(f"❌ {printer} - FAILED")
        
        time.sleep(2)  # Wait between tests
    
    print("\n" + "=" * 40)
    print("🏁 Test completed")

if __name__ == "__main__":
    main()