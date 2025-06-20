#!/bin/bash

# Sodalite Server Service Uninstallation Script
# This script removes the sodalite server systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root (use sudo)"
    exit 1
fi

print_status "Starting Sodalite service uninstallation..."

# Default installation directory
INSTALL_DIR="/opt/sodalite"
SERVICE_USER="sodalite"
SERVICE_GROUP="sodalite"
LOG_DIR="/var/log/sodalite"

# Ask for confirmation
echo ""
print_warning "This will remove:"
echo "  - Systemd service: sodalite"
echo "  - Installation directory: $INSTALL_DIR"
echo "  - Service user: $SERVICE_USER"
echo "  - Log directory: $LOG_DIR"
echo ""
read -p "Are you sure you want to continue? [y/N]: " confirm

if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    print_status "Uninstallation cancelled."
    exit 0
fi

# Stop and disable service
if systemctl is-active --quiet sodalite.service; then
    print_status "Stopping sodalite service..."
    systemctl stop sodalite.service
fi

if systemctl is-enabled --quiet sodalite.service; then
    print_status "Disabling sodalite service..."
    systemctl disable sodalite.service
fi

# Remove service file
if [ -f "/etc/systemd/system/sodalite.service" ]; then
    print_status "Removing systemd service file..."
    rm -f /etc/systemd/system/sodalite.service
    systemctl daemon-reload
fi

# Remove installation directory
if [ -d "$INSTALL_DIR" ]; then
    print_status "Removing installation directory..."
    rm -rf "$INSTALL_DIR"
fi

# Remove log directory
if [ -d "$LOG_DIR" ]; then
    print_status "Removing log directory..."
    rm -rf "$LOG_DIR"
fi

# Remove service user
if id "$SERVICE_USER" &>/dev/null; then
    print_status "Removing service user: $SERVICE_USER"
    userdel "$SERVICE_USER" 2>/dev/null || true
fi

# Clean up any remaining systemd files
systemctl reset-failed sodalite.service 2>/dev/null || true

print_success "Sodalite service has been completely uninstalled!"
echo ""
print_status "The following may still be installed on your system:"
echo "  - ffmpeg (if installed by the installation script)"
echo "  - Python 3 and pip (system packages)"
echo ""
print_status "To remove these manually if desired:"
echo "  - ffmpeg: sudo apt remove ffmpeg (or equivalent for your distro)"
echo ""
print_success "Uninstallation complete! 🗑️"
