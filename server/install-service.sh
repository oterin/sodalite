#!/bin/bash

# Sodalite Server Service Installation Script
# This script sets up the sodalite server as a systemd service

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

print_status "Starting Sodalite service installation..."

# Get the current directory (should be the server directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

print_status "Script directory: $SCRIPT_DIR"
print_status "Project directory: $PROJECT_DIR"

# Default installation directory
INSTALL_DIR="/opt/sodalite"
SERVICE_USER="sodalite"
SERVICE_GROUP="sodalite"

# Ask for custom installation directory
read -p "Installation directory [$INSTALL_DIR]: " custom_dir
if [ ! -z "$custom_dir" ]; then
    INSTALL_DIR="$custom_dir"
fi

print_status "Installing to: $INSTALL_DIR"

# Create installation directory
if [ ! -d "$INSTALL_DIR" ]; then
    print_status "Creating installation directory..."
    mkdir -p "$INSTALL_DIR"
fi

# Create service user if it doesn't exist
if ! id "$SERVICE_USER" &>/dev/null; then
    print_status "Creating service user: $SERVICE_USER"
    useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
else
    print_status "Service user $SERVICE_USER already exists"
fi

# Copy project files
print_status "Copying project files..."
cp -r "$PROJECT_DIR"/* "$INSTALL_DIR/"

# Create virtual environment
print_status "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"

# Install dependencies
print_status "Installing Python dependencies..."
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/server/requirements.txt"

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    print_warning "ffmpeg is not installed. Installing it..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y ffmpeg
    elif command -v yum &> /dev/null; then
        yum install -y ffmpeg
    elif command -v dnf &> /dev/null; then
        dnf install -y ffmpeg
    elif command -v pacman &> /dev/null; then
        pacman -S --noconfirm ffmpeg
    else
        print_error "Could not install ffmpeg automatically. Please install it manually."
        exit 1
    fi
    print_success "ffmpeg installed successfully"
else
    print_success "ffmpeg is already installed"
fi

# Set ownership
print_status "Setting file ownership..."
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"

# Create log directory
LOG_DIR="/var/log/sodalite"
if [ ! -d "$LOG_DIR" ]; then
    print_status "Creating log directory..."
    mkdir -p "$LOG_DIR"
    chown "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"
fi

# Update service file with correct paths
print_status "Configuring systemd service..."
SERVICE_FILE="$INSTALL_DIR/server/sodalite.service"
sed -i "s|/opt/sodalite|$INSTALL_DIR|g" "$SERVICE_FILE"
sed -i "s|User=sodalite|User=$SERVICE_USER|g" "$SERVICE_FILE"
sed -i "s|Group=sodalite|Group=$SERVICE_GROUP|g" "$SERVICE_FILE"

# Copy service file to systemd
cp "$SERVICE_FILE" /etc/systemd/system/

# Reload systemd and enable service
print_status "Enabling systemd service..."
systemctl daemon-reload
systemctl enable sodalite.service

# Start the service
print_status "Starting sodalite service..."
if systemctl start sodalite.service; then
    print_success "Sodalite service started successfully!"
else
    print_error "Failed to start sodalite service. Check logs with: journalctl -u sodalite -f"
    exit 1
fi

# Show status
print_status "Service status:"
systemctl status sodalite.service --no-pager

echo ""
print_success "Sodalite server has been installed and configured as a systemd service!"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo "  Start service:    sudo systemctl start sodalite"
echo "  Stop service:     sudo systemctl stop sodalite"
echo "  Restart service:  sudo systemctl restart sodalite"
echo "  Check status:     sudo systemctl status sodalite"
echo "  View logs:        sudo journalctl -u sodalite -f"
echo "  Disable service:  sudo systemctl disable sodalite"
echo ""
echo -e "${BLUE}Files installed to:${NC} $INSTALL_DIR"
echo -e "${BLUE}Service user:${NC} $SERVICE_USER"
echo -e "${BLUE}Log files:${NC} $LOG_DIR (also check: journalctl -u sodalite)"
echo ""
print_success "Installation complete! 🚀"
