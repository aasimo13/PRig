# PRig Setup Guide

## Step-by-Step Setup Instructions

### 1. Install Dependencies
```bash
cd ~/PRig/src
sudo python3 install_dependencies.py
```

### 2. Verify Hardware
```bash
sudo python3 hardware_check.py
```

### 3. Test Basic Functionality
```bash
sudo python3 simple_printer_test.py
```

## Hardware Requirements

### Supported Printers
- **Canon SELPHY CP1300** (USB ID: 04a9:327b)
- **Canon SELPHY CP1500** (USB ID: 04a9:3302) 
- **Canon SELPHY CP910** (USB ID: 04a9:327a)
- **DNP QW410** (USB ID: 1343:0003)
- **DNP Photo Printer** (USB ID: 1452:9201)

### System Requirements
- Raspberry Pi (or Linux system) with USB ports
- Root access (sudo privileges)
- Internet connection for initial setup

## Software Dependencies

### Required Packages
- `usbutils` - USB device detection
- `cups` - Print system
- `cups-client` - CUPS client tools
- `cups-daemon` - CUPS service
- `printer-driver-all` - Printer drivers
- `imagemagick` - Image processing (optional)
- `python3` - Runtime

### Required Services
- `cups` service must be running
- USB devices must be accessible

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Always run with `sudo`
   - Check if user is in `lpadmin` group

2. **No Printers Found**
   - Check USB connection: `lsusb`
   - Verify CUPS is running: `systemctl status cups`

3. **Print Jobs Stuck**
   - Check printer status: `lpstat -p`
   - Cancel stuck jobs: `cancel -a`

4. **Dependencies Missing**
   - Run: `sudo python3 install_dependencies.py`
   - Fix broken packages: `sudo dpkg --configure -a`

### Debug Commands
```bash
# Check USB devices
lsusb

# Check CUPS printers
lpstat -p

# Check CUPS jobs
lpstat -o

# Check system logs
journalctl -u cups -f
```

## File Structure

```
PRig/
├── src/
│   ├── hardware_check.py      # Hardware verification
│   ├── install_dependencies.py # Dependency installer
│   ├── simple_printer_test.py  # Basic printer test
│   ├── printer_test.py        # Full test suite
│   └── printer_detection.py   # Printer detection logic
├── test_images/               # Test images
└── SETUP_GUIDE.md            # This file
```

## Usage

1. **Install and verify setup:**
   ```bash
   sudo python3 install_dependencies.py
   sudo python3 hardware_check.py
   ```

2. **Run simple test:**
   ```bash
   sudo python3 simple_printer_test.py
   ```

3. **Full continuous printing:**
   ```bash
   sudo python3 printer_test.py
   ```

## Expected Behavior

- System monitors USB for supported printers
- When printer is connected, automatically prints test image
- Continues printing until printer is disconnected
- Handles multiple printers simultaneously