#!/usr/bin/env python3
"""
Hardware and dependency verification for PRig
"""

import subprocess
import sys
import os
from pathlib import Path

def check_root():
    """Check if running as root"""
    if os.geteuid() != 0:
        print("❌ ERROR: Must run as root (use sudo)")
        return False
    print("✅ Running as root")
    return True

def check_usb_tools():
    """Check if USB detection tools are available"""
    tools = ['lsusb', 'usbutils']
    for tool in tools:
        result = subprocess.run(['which', tool], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {tool} available")
        else:
            print(f"❌ {tool} not found")
            return False
    return True

def check_cups():
    """Check if CUPS is installed and running"""
    # Check if CUPS is installed
    result = subprocess.run(['which', 'lp'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ CUPS not installed")
        return False
    print("✅ CUPS installed")
    
    # Check if CUPS service is running
    result = subprocess.run(['systemctl', 'is-active', 'cups'], capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ CUPS service not running")
        return False
    print("✅ CUPS service running")
    return True

def check_usb_devices():
    """Check what USB devices are connected"""
    print("\n🔍 USB Devices:")
    result = subprocess.run(['lsusb'], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if any(vendor in line.lower() for vendor in ['canon', 'dnp', '04a9', '1343']):
                print(f"📱 PRINTER: {line}")
            else:
                print(f"   {line}")
    else:
        print("❌ Cannot list USB devices")
        return False
    return True

def check_existing_printers():
    """Check what printers are already configured in CUPS"""
    print("\n🖨️  Existing CUPS Printers:")
    result = subprocess.run(['lpstat', '-p'], capture_output=True, text=True)
    if result.returncode == 0:
        if result.stdout.strip():
            for line in result.stdout.splitlines():
                print(f"   {line}")
        else:
            print("   No printers configured")
    else:
        print("❌ Cannot list CUPS printers")
        return False
    return True

def main():
    """Main hardware check"""
    print("🔧 PRig Hardware & Dependency Check")
    print("=" * 40)
    
    checks = [
        check_root,
        check_usb_tools,
        check_cups,
        check_usb_devices,
        check_existing_printers
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"❌ Error in {check.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    if all(results):
        print("✅ ALL CHECKS PASSED - System ready for PRig")
    else:
        print("❌ Some checks failed - System needs setup")
        
    return all(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)