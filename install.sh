#!/bin/bash

# PRig Installation Script
# Installs the automated printer test rig system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/printer-test"
SERVICE_DIR="/etc/systemd/system"
CONFIG_DIR="/etc/prig"
LOG_DIR="/var/log/prig"
UDEV_RULES_DIR="/etc/udev/rules.d"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

check_system() {
    log_info "Checking system requirements..."
    
    # Check if running on Raspberry Pi OS or Debian/Ubuntu
    if ! command -v apt-get &> /dev/null; then
        log_error "This installer requires apt package manager (Debian/Ubuntu/Raspberry Pi OS)"
        exit 1
    fi
    
    # Check Python version
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)" 2>/dev/null; then
        log_error "Python 3.7 or higher is required"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    # Update package lists
    apt-get update -qq
    
    # Install required packages
    apt-get install -y \
        cups \
        cups-client \
        printer-driver-gutenprint \
        python3-pip \
        python3-dev \
        usbutils \
        systemd \
        git
    
    # Install Python packages
    pip3 install \
        Pillow \
        numpy \
        Flask \
        Flask-SocketIO
    
    log_success "Dependencies installed successfully"
}

create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    
    # Set permissions
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$CONFIG_DIR"
    chmod 755 "$LOG_DIR"
    
    log_success "Directories created"
}

install_files() {
    log_info "Installing PRig files..."
    
    # Copy Python modules
    cp src/*.py "$INSTALL_DIR/"
    
    # Copy templates directory
    cp -r src/templates "$INSTALL_DIR/"
    
    # Make scripts executable
    chmod +x "$INSTALL_DIR/printer_test.py"
    chmod +x "$INSTALL_DIR/web_app.py"
    
    # Copy configuration files
    cp config/cupsd.conf "$CONFIG_DIR/"
    cp config/printers.conf "$CONFIG_DIR/"
    
    # Install systemd service files
    cp config/printer-test@.service "$SERVICE_DIR/"
    cp config/printer-test-startup.service "$SERVICE_DIR/"
    cp config/prig-webapp.service "$SERVICE_DIR/"
    
    # Install udev rules
    cp config/99-printer-test.rules "$UDEV_RULES_DIR/"
    
    log_success "Files installed successfully"
}

configure_cups() {
    log_info "Configuring CUPS..."
    
    # Backup original CUPS configuration
    if [[ -f /etc/cups/cupsd.conf ]]; then
        cp /etc/cups/cupsd.conf /etc/cups/cupsd.conf.backup
    fi
    
    # Install our CUPS configuration
    cp "$CONFIG_DIR/cupsd.conf" /etc/cups/cupsd.conf
    
    # Add pi user to lpadmin group
    if id "pi" &>/dev/null; then
        usermod -a -G lpadmin pi
        log_info "Added pi user to lpadmin group"
    fi
    
    # Start and enable CUPS
    systemctl enable cups
    systemctl start cups || true
    
    log_success "CUPS configured successfully"
}

setup_services() {
    log_info "Setting up systemd services..."
    
    # Reload systemd daemon
    systemctl daemon-reload
    
    # Enable services
    systemctl enable printer-test-startup.service
    systemctl enable prig-webapp.service
    
    # Start web app
    systemctl start prig-webapp.service
    
    # Reload udev rules
    udevadm control --reload-rules
    udevadm trigger
    
    log_success "Services configured successfully"
}

create_default_config() {
    log_info "Creating default configuration..."
    
    cat > "$CONFIG_DIR/config.json" << EOF
{
  "log_level": "INFO",
  "test_images": {
    "formats": ["JPEG"],
    "quality": 95,
    "resolution": [1800, 1200]
  },
  "printer_settings": {
    "timeout": 120,
    "retry_attempts": 3,
    "print_delay": 5
  },
  "supported_printers": {
    "canon_selphy": {
      "vendor_id": "04a9",
      "models": ["CP1300", "CP1500", "CP910"]
    },
    "dnp_qw410": {
      "vendor_id": "1343",
      "product_id": "0003"
    }
  }
}
EOF
    
    log_success "Default configuration created"
}

test_installation() {
    log_info "Testing installation..."
    
    # Test Python imports
    if ! python3 -c "import sys; sys.path.insert(0, '$INSTALL_DIR'); import printer_test, printer_detection, test_image_generator, utils" 2>/dev/null; then
        log_error "Python module import test failed"
        exit 1
    fi
    
    # Test CUPS
    if ! systemctl is-active --quiet cups; then
        log_warning "CUPS service is not running"
    fi
    
    # Test udev rules
    if [[ ! -f "$UDEV_RULES_DIR/99-printer-test.rules" ]]; then
        log_error "udev rules not installed"
        exit 1
    fi
    
    log_success "Installation test passed"
}

show_status() {
    log_info "Installation completed successfully!"
    echo
    echo "PRig has been installed and configured. Here's what was set up:"
    echo
    echo "  • Installation directory: $INSTALL_DIR"
    echo "  • Configuration directory: $CONFIG_DIR"
    echo "  • Log directory: $LOG_DIR"
    echo "  • CUPS configured for headless operation"
    echo "  • udev rules installed for automatic printer detection"
    echo "  • systemd services configured"
    echo
    echo "The system will now automatically:"
    echo "  • Detect when USB printers are connected"
    echo "  • Run comprehensive test prints"
    echo "  • Log all activities to $LOG_DIR/prig.log"
    echo
    echo "Supported printers:"
    echo "  • Canon SELPHY (CP1300, CP1500, CP910)"
    echo "  • DNP QW410"
    echo
    echo "Web Interface:"
    echo "  Open http://$(hostname -I | awk '{print $1}'):5000 in your browser"
    echo "  Or use http://localhost:5000 if accessing locally"
    echo
    echo "To test manually, run:"
    echo "  sudo python3 $INSTALL_DIR/printer_test.py"
    echo
    echo "To view logs:"
    echo "  sudo tail -f $LOG_DIR/prig.log"
    echo "  sudo journalctl -u printer-test-startup.service -f"
    echo "  sudo journalctl -u prig-webapp.service -f"
    echo
    echo "To check system status:"
    echo "  sudo systemctl status printer-test-startup.service"
    echo "  sudo systemctl status prig-webapp.service"
    echo "  sudo systemctl status cups"
    echo
    log_success "PRig is ready to use!"
}

main() {
    echo "======================================"
    echo "PRig - Printer Test Rig Installation"
    echo "======================================"
    echo
    
    check_root
    check_system
    install_dependencies
    create_directories
    install_files
    configure_cups
    setup_services
    create_default_config
    test_installation
    show_status
}

# Run main function
main "$@"