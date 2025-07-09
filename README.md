# PRig - Raspberry Pi Printer Test Rig

Automated test rig for DNP QW410 and Canon SELPHY photo printers. Automatically detects when printers are connected via USB and prints comprehensive test images for quality control.

## Features

- **Automatic Detection**: Triggers when USB printers are plugged in
- **Comprehensive Test Images**: Tests color accuracy, clarity, and smudging
- **Headless Operation**: All logging, no GUI required
- **Multi-Printer Support**: Handles both DNP QW410 and Canon Selphy models
- **Smart Print Settings**: Optimized settings for each printer type

## Supported Printers

- **DNP QW410** (all size variants)
- **Canon SELPHY** (CP1300, CP1500, CP910, and other models)

## Quick Install

```bash
git clone https://github.com/aasimo13/PRig.git
cd PRig
chmod +x install.sh
./install.sh