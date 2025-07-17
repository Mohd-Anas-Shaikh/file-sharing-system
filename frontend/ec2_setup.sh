#!/bin/bash
# EC2 setup script for File Sharing System

# Exit on error
set -e

echo "=== File Sharing System - EC2 Setup ==="

# Update system packages
echo "Updating system packages..."
sudo yum update -y

# Install Python and development tools
echo "Installing Python and development tools..."
sudo yum install -y python3 python3-pip python3-devel gcc

# Assuming the zip file has been uploaded and extracted to ~/file-sharing-system-aws.zip
# If you're using a different location, adjust the paths below

# Create application directory
echo "Setting up application directory..."
APP_DIR="/home/ec2-user/file-sharing-system-aws"

# If the directory doesn't exist from unzipping, create it
if [ ! -d "$APP_DIR" ]; then
    mkdir -p "$APP_DIR"
    echo "Created application directory"
fi

# Navigate to the frontend directory
cd "$APP_DIR/frontend"
echo "Working in directory: $(pwd)"

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies including Gunicorn
echo "Installing dependencies..."
pip install -r requirements.txt
pip install gunicorn

# Make sure the application files are executable
chmod +x wsgi.py
chmod +x app.py

# Set up systemd service
echo "Setting up systemd service..."
sudo cp file-sharing.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable file-sharing
sudo systemctl start file-sharing

# Verify service is running
echo "Verifying service status..."
sudo systemctl status file-sharing --no-pager

# Get the public IP address for easy access
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

echo "=== Setup Complete ==="
echo "File Sharing System is now running on port 5002"
echo "You can access it at: http://$PUBLIC_IP:5002"
echo "Health check endpoint: http://$PUBLIC_IP:5002/health"
echo "To check the service status, run: sudo systemctl status file-sharing"
