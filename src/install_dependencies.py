#!/usr/bin/env python3
"""
Install all required dependencies for PRig
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command with error handling"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Success")
            return True
        else:
            print(f"❌ {description} - Failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Error: {e}")
        return False

def main():
    """Install all dependencies"""
    if os.geteuid() != 0:
        print("❌ Must run as root: sudo python3 install_dependencies.py")
        return False
    
    print("🚀 Installing PRig Dependencies")
    print("=" * 40)
    
    commands = [
        # Fix any broken packages
        ("dpkg --configure -a", "Fixing broken packages"),
        ("apt-get -f install -y", "Fixing broken dependencies"),
        
        # Update package list
        ("apt-get update", "Updating package list"),
        
        # Install essential packages
        ("apt-get install -y usbutils", "Installing USB utilities"),
        ("apt-get install -y cups cups-client cups-daemon", "Installing CUPS"),
        ("apt-get install -y printer-driver-all", "Installing printer drivers"),
        ("apt-get install -y imagemagick", "Installing ImageMagick"),
        ("apt-get install -y python3 python3-pip", "Installing Python3"),
        
        # Start services
        ("systemctl start cups", "Starting CUPS service"),
        ("systemctl enable cups", "Enabling CUPS service"),
        
        # Set permissions
        ("usermod -a -G lpadmin pi", "Adding pi user to lpadmin group"),
    ]
    
    success_count = 0
    for cmd, desc in commands:
        if run_command(cmd, desc):
            success_count += 1
    
    print("\n" + "=" * 40)
    print(f"✅ {success_count}/{len(commands)} commands successful")
    
    if success_count == len(commands):
        print("🎉 All dependencies installed successfully!")
        return True
    else:
        print("⚠️  Some dependencies failed to install")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)