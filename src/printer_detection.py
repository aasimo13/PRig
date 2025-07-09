#!/usr/bin/env python3
"""
Printer Detection Module for PRig
Detects and configures USB photo printers (Canon SELPHY and DNP QW410).
"""

import re
import subprocess
import logging
import platform
from dataclasses import dataclass
from typing import List, Optional, Dict
from pathlib import Path


@dataclass
class PrinterInfo:
    """Information about a detected printer."""
    name: str
    model: str
    vendor: str
    device_uri: str
    cups_name: str
    ppd_file: str
    usb_device: str
    vendor_id: str
    product_id: str


class PrinterDetector:
    """Detects and configures USB photo printers."""
    
    SUPPORTED_PRINTERS = {
        # Canon SELPHY printers
        '04a9:327b': {
            'name': 'Canon SELPHY CP1300',
            'model': 'Canon SELPHY CP1300',
            'vendor': 'Canon',
            'ppd': 'raw'
        },
        '04a9:3302': {
            'name': 'Canon SELPHY CP1500',
            'model': 'Canon SELPHY CP1500', 
            'vendor': 'Canon',
            'ppd': 'raw'
        },
        '04a9:327a': {
            'name': 'Canon SELPHY CP910',
            'model': 'Canon SELPHY CP910',
            'vendor': 'Canon',
            'ppd': 'raw'
        },
        # DNP Photo Printers
        '1343:0003': {
            'name': 'DNP QW410',
            'model': 'DNP QW410',
            'vendor': 'DNP',
            'ppd': 'raw'
        },
        '1452:9201': {
            'name': 'DNP Photo Printer',
            'model': 'DNP Photo Printer',
            'vendor': 'DNP',
            'ppd': 'raw'
        }
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def get_connected_printers(self) -> List[PrinterInfo]:
        """Get all connected supported USB printers."""
        printers = []
        
        # Get USB devices
        usb_devices = self._get_usb_devices()
        
        for device in usb_devices:
            if device['vendor_product'] in self.SUPPORTED_PRINTERS:
                printer_info = self._create_printer_info(device)
                if printer_info:
                    printers.append(printer_info)
                    
        return printers
        
    def _get_usb_devices(self) -> List[Dict]:
        """Get USB device information using platform-specific commands."""
        devices = []
        
        try:
            if platform.system() == "Darwin":  # macOS
                devices = self._get_macos_usb_devices()
            else:  # Linux
                devices = self._get_linux_usb_devices()
                    
        except Exception as e:
            self.logger.error(f"Error getting USB devices: {e}")
            
        return devices
    
    def _get_linux_usb_devices(self) -> List[Dict]:
        """Get USB device information using lsusb (Linux)."""
        devices = []
        
        # First check if lsusb is available
        result = subprocess.run(['which', 'lsusb'], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            self.logger.warning("lsusb not found, installing usbutils...")
            subprocess.run(['apt-get', 'update'], capture_output=True, text=True, check=False)
            subprocess.run(['apt-get', 'install', '-y', 'usbutils'], capture_output=True, text=True, check=False)
        
        result = subprocess.run(['lsusb'], capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            self.logger.error(f"lsusb command failed: {result.stderr}")
            return devices
        
        for line in result.stdout.splitlines():
            # Parse lsusb output: Bus 001 Device 004: ID 04a9:327b Canon, Inc. 
            match = re.search(r'Bus (\d+) Device (\d+): ID ([0-9a-f]{4}):([0-9a-f]{4}) (.+)', line)
            if match:
                vendor_product = f"{match.group(3)}:{match.group(4)}"
                
                # Verify device still exists by checking /dev/bus/usb/
                device_path = f"/dev/bus/usb/{match.group(1).zfill(3)}/{match.group(2).zfill(3)}"
                if Path(device_path).exists():
                    devices.append({
                        'bus': match.group(1),
                        'device': match.group(2),
                        'vendor_id': match.group(3),
                        'product_id': match.group(4),
                        'vendor_product': vendor_product,
                        'description': match.group(5),
                        'device_path': device_path
                    })
                else:
                    self.logger.debug(f"USB device {vendor_product} no longer exists at {device_path}")
                
        return devices
    
    def _get_macos_usb_devices(self) -> List[Dict]:
        """Get USB device information using system_profiler (macOS)."""
        devices = []
        
        result = subprocess.run(['system_profiler', 'SPUSBDataType'], 
                              capture_output=True, text=True, check=False)
        
        # Parse system_profiler output
        current_device = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            
            if 'Product ID:' in line:
                match = re.search(r'Product ID: 0x([0-9a-f]{4})', line)
                if match:
                    current_device['product_id'] = match.group(1)
                    
            elif 'Vendor ID:' in line:
                match = re.search(r'Vendor ID: 0x([0-9a-f]{4})', line)
                if match:
                    current_device['vendor_id'] = match.group(1)
                    
            elif 'Manufacturer:' in line:
                match = re.search(r'Manufacturer: (.+)', line)
                if match:
                    current_device['description'] = match.group(1)
                    
            # If we have both vendor and product ID, create device entry
            if 'vendor_id' in current_device and 'product_id' in current_device:
                vendor_product = f"{current_device['vendor_id']}:{current_device['product_id']}"
                devices.append({
                    'bus': '001',  # Default bus for macOS
                    'device': '001',  # Default device for macOS
                    'vendor_id': current_device['vendor_id'],
                    'product_id': current_device['product_id'],
                    'vendor_product': vendor_product,
                    'description': current_device.get('description', 'Unknown Device')
                })
                current_device = {}  # Reset for next device
                
        return devices
        
    def _create_printer_info(self, device: Dict) -> Optional[PrinterInfo]:
        """Create PrinterInfo object from USB device information."""
        vendor_product = device['vendor_product']
        
        if vendor_product not in self.SUPPORTED_PRINTERS:
            return None
            
        printer_config = self.SUPPORTED_PRINTERS[vendor_product]
        
        # Create device URI
        device_uri = f"usb://{printer_config['vendor']}/{printer_config['name'].replace(' ', '%20')}"
        
        # Create CUPS printer name (safe for system use)
        cups_name = f"prig_{printer_config['name'].lower().replace(' ', '_')}"
        
        return PrinterInfo(
            name=printer_config['name'],
            model=printer_config['model'],
            vendor=printer_config['vendor'],
            device_uri=device_uri,
            cups_name=cups_name,
            ppd_file=printer_config['ppd'],
            usb_device=f"Bus {device['bus']} Device {device['device']}",
            vendor_id=device['vendor_id'],
            product_id=device['product_id']
        )
        
    def get_printer_capabilities(self, printer: PrinterInfo) -> Dict:
        """Get printer capabilities and supported options."""
        capabilities = {
            'paper_sizes': [],
            'media_types': [],
            'quality_levels': [],
            'color_modes': []
        }
        
        try:
            # Query printer options using lpoptions
            result = subprocess.run(['lpoptions', '-p', printer.cups_name, '-l'], 
                                  capture_output=True, text=True, check=False)
            
            if result.returncode == 0:
                capabilities = self._parse_printer_options(result.stdout)
                
        except Exception as e:
            self.logger.error(f"Error getting printer capabilities: {e}")
            
        # Set default capabilities based on printer model
        if printer.model.startswith('Canon'):
            capabilities.update({
                'paper_sizes': ['4x6', '5x7'],
                'media_types': ['PhotoPaper', 'GlossyPhoto'],
                'quality_levels': ['Draft', 'Normal', 'High'],
                'color_modes': ['RGB', 'sRGB']
            })
        elif printer.model.startswith('DNP'):
            capabilities.update({
                'paper_sizes': ['4x6', '5x7', '6x8'],
                'media_types': ['Ribbon'],
                'quality_levels': ['Standard', 'Fine'],
                'color_modes': ['RGB']
            })
            
        return capabilities
        
    def _parse_printer_options(self, options_output: str) -> Dict:
        """Parse lpoptions output to extract capabilities."""
        capabilities = {
            'paper_sizes': [],
            'media_types': [],
            'quality_levels': [],
            'color_modes': []
        }
        
        for line in options_output.splitlines():
            line = line.strip()
            
            if line.startswith('PageSize/'):
                # Extract paper sizes
                sizes = re.findall(r'(\w+x\w+)', line)
                capabilities['paper_sizes'].extend(sizes)
                
            elif line.startswith('MediaType/'):
                # Extract media types
                types = re.findall(r'(\w+)', line.split(':')[1] if ':' in line else '')
                capabilities['media_types'].extend(types)
                
            elif line.startswith('Quality/'):
                # Extract quality levels
                qualities = re.findall(r'(\w+)', line.split(':')[1] if ':' in line else '')
                capabilities['quality_levels'].extend(qualities)
                
            elif line.startswith('ColorModel/'):
                # Extract color modes
                modes = re.findall(r'(\w+)', line.split(':')[1] if ':' in line else '')
                capabilities['color_modes'].extend(modes)
                
        return capabilities
        
    def install_printer_drivers(self) -> bool:
        """Install necessary printer drivers."""
        try:
            self.logger.info("Installing printer drivers...")
            
            # Update package list
            result = subprocess.run(['apt-get', 'update'], capture_output=True, text=True, check=False)
            if result.returncode != 0:
                self.logger.warning(f"apt-get update failed: {result.stderr}")
            
            # Install essential packages
            packages = [
                'cups',
                'cups-client', 
                'cups-daemon',
                'printer-driver-gutenprint',
                'printer-driver-all',
                'usbutils',
                'libcups2-dev',
                'cups-filters',
                'cups-pdf'
            ]
            
            for package in packages:
                self.logger.info(f"Installing {package}...")
                result = subprocess.run(['apt-get', 'install', '-y', package], 
                                      capture_output=True, text=True, check=False)
                if result.returncode != 0:
                    self.logger.warning(f"Failed to install {package}: {result.stderr}")
            
            # Start CUPS service
            subprocess.run(['systemctl', 'start', 'cups'], capture_output=True, text=True, check=False)
            subprocess.run(['systemctl', 'enable', 'cups'], capture_output=True, text=True, check=False)
            
            # Install DNP QW410 specific drivers
            self._install_dnp_drivers()
            
            # Install Canon SELPHY drivers
            self._install_canon_drivers()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error installing printer drivers: {e}")
            return False
            
    def _install_dnp_drivers(self):
        """Install DNP QW410 specific drivers."""
        try:
            # Create DNP QW410 PPD file
            ppd_content = self._get_dnp_ppd_content()
            ppd_path = Path('/usr/share/cups/model/dnp-qw410.ppd')
            
            with open(ppd_path, 'w') as f:
                f.write(ppd_content)
                
            self.logger.info("DNP QW410 PPD file installed")
            
        except Exception as e:
            self.logger.error(f"Error installing DNP drivers: {e}")
    
    def _install_canon_drivers(self):
        """Install Canon SELPHY specific drivers."""
        try:
            self.logger.info("Installing Canon SELPHY drivers...")
            
            # Create Canon SELPHY PPD files
            canon_models = ['CP1300', 'CP1500', 'CP910']
            
            for model in canon_models:
                ppd_content = self._get_canon_ppd_content(model)
                ppd_path = Path(f'/usr/share/cups/model/canon-selphy-{model.lower()}.ppd')
                
                with open(ppd_path, 'w') as f:
                    f.write(ppd_content)
                    
                self.logger.info(f"Canon SELPHY {model} PPD file installed")
            
            # Update CUPS to recognize new PPDs
            subprocess.run(['systemctl', 'reload', 'cups'], capture_output=True, text=True, check=False)
            
        except Exception as e:
            self.logger.error(f"Error installing Canon drivers: {e}")
    
    def _get_canon_ppd_content(self, model: str) -> str:
        """Get Canon SELPHY PPD file content."""
        return f'''*PPD-Adobe: "4.3"
*FormatVersion: "4.3"
*FileVersion: "1.0"
*LanguageVersion: English
*LanguageEncoding: ISOLatin1
*PCFileName: "CANON-{model}.PPD"
*Manufacturer: "Canon"
*Product: "({model})"
*cupsVersion: 1.4
*cupsManualCopies: False
*cupsModelNumber: 0
*cupsFilter: "application/vnd.cups-raster 0 rastertocanon"
*ModelName: "Canon SELPHY {model}"
*ShortNickName: "Canon SELPHY {model}"
*NickName: "Canon SELPHY {model}"
*PSVersion: "(3010.000) 0"
*LanguageLevel: "3"
*ColorDevice: True
*DefaultColorSpace: RGB
*FileSystem: False
*Throughput: "1"
*LandscapeOrientation: Plus90
*VariablePaperSize: False
*TTRasterizer: Type42

*OpenUI *PageSize/Media Size: PickOne
*OrderDependency: 10 AnySetup *PageSize
*DefaultPageSize: w288h432
*PageSize w288h432/4x6": "<</PageSize[288 432]/ImagingBBox null>>setpagedevice"
*PageSize w360h504/5x7": "<</PageSize[360 504]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageSize

*OpenUI *PageRegion: PickOne
*OrderDependency: 10 AnySetup *PageRegion
*DefaultPageRegion: w288h432
*PageRegion w288h432/4x6": "<</PageSize[288 432]/ImagingBBox null>>setpagedevice"
*PageRegion w360h504/5x7": "<</PageSize[360 504]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageRegion

*DefaultImageableArea: w288h432
*ImageableArea w288h432/4x6": "0.0 0.0 288.0 432.0"
*ImageableArea w360h504/5x7": "0.0 0.0 360.0 504.0"

*DefaultPaperDimension: w288h432
*PaperDimension w288h432/4x6": "288 432"
*PaperDimension w360h504/5x7": "360 504"

*OpenUI *Quality/Print Quality: PickOne
*OrderDependency: 10 AnySetup *Quality
*DefaultQuality: Standard
*Quality Standard/Standard: ""
*Quality High/High: ""
*CloseUI: *Quality

*% End of PPD file
'''
            
    def _get_dnp_ppd_content(self) -> str:
        """Get DNP QW410 PPD file content."""
        return '''*PPD-Adobe: "4.3"
*FormatVersion: "4.3"
*FileVersion: "1.0"
*LanguageVersion: English
*LanguageEncoding: ISOLatin1
*PCFileName: "DNP-QW410.PPD"
*Manufacturer: "DNP"
*Product: "(QW410)"
*cupsVersion: 1.4
*cupsManualCopies: False
*cupsModelNumber: 0
*cupsFilter: "application/vnd.cups-raster 0 rastertoqw410"
*ModelName: "DNP QW410"
*ShortNickName: "DNP QW410"
*NickName: "DNP QW410"
*PSVersion: "(3010.000) 0"
*LanguageLevel: "3"
*ColorDevice: True
*DefaultColorSpace: RGB
*FileSystem: False
*Throughput: "1"
*LandscapeOrientation: Plus90
*VariablePaperSize: False
*TTRasterizer: Type42

*OpenUI *PageSize/Media Size: PickOne
*OrderDependency: 10 AnySetup *PageSize
*DefaultPageSize: w288h432
*PageSize w288h432/4x6": "<</PageSize[288 432]/ImagingBBox null>>setpagedevice"
*PageSize w360h504/5x7": "<</PageSize[360 504]/ImagingBBox null>>setpagedevice"
*PageSize w432h576/6x8": "<</PageSize[432 576]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageSize

*OpenUI *PageRegion: PickOne
*OrderDependency: 10 AnySetup *PageRegion
*DefaultPageRegion: w288h432
*PageRegion w288h432/4x6": "<</PageSize[288 432]/ImagingBBox null>>setpagedevice"
*PageRegion w360h504/5x7": "<</PageSize[360 504]/ImagingBBox null>>setpagedevice"
*PageRegion w432h576/6x8": "<</PageSize[432 576]/ImagingBBox null>>setpagedevice"
*CloseUI: *PageRegion

*DefaultImageableArea: w288h432
*ImageableArea w288h432/4x6": "0.0 0.0 288.0 432.0"
*ImageableArea w360h504/5x7": "0.0 0.0 360.0 504.0"
*ImageableArea w432h576/6x8": "0.0 0.0 432.0 576.0"

*DefaultPaperDimension: w288h432
*PaperDimension w288h432/4x6": "288 432"
*PaperDimension w360h504/5x7": "360 504"
*PaperDimension w432h576/6x8": "432 576"

*OpenUI *Quality/Print Quality: PickOne
*OrderDependency: 10 AnySetup *Quality
*DefaultQuality: Standard
*Quality Standard/Standard: ""
*Quality Fine/Fine: ""
*CloseUI: *Quality

*% End of PPD file
'''

    def test_printer_communication(self, printer: PrinterInfo) -> bool:
        """Test if printer is responding to commands."""
        try:
            # Send a simple query to the printer
            result = subprocess.run(['lpstat', '-p', printer.cups_name], 
                                  capture_output=True, text=True, check=False)
            
            return result.returncode == 0 and 'idle' in result.stdout.lower()
            
        except Exception as e:
            self.logger.error(f"Error testing printer communication: {e}")
            return False