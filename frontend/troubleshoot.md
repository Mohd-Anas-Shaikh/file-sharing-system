# EC2 Deployment Troubleshooting Guide

## Check Detailed Logs

Run the following command on your EC2 instance to see detailed logs:

```bash
sudo journalctl -u file-sharing.service -n 50 --no-pager
```

This will show the last 50 log entries for the service, which should help identify the specific error.

## Common Issues and Solutions

### 1. Python Module Not Found

If you see errors like `ModuleNotFoundError: No module named 'some_module'`:

```bash
# Activate the virtual environment
cd /home/ec2-user/file-sharing-system-aws/frontend
source venv/bin/activate

# Install the missing module
pip install some_module

# Restart the service
sudo systemctl restart file-sharing
```

### 2. Permission Issues

If there are permission problems:

```bash
# Fix permissions for the application directory
sudo chown -R ec2-user:ec2-user /home/ec2-user/file-sharing-system-aws

# Make sure Python files are executable
chmod +x /home/ec2-user/file-sharing-system-aws/frontend/app.py
chmod +x /home/ec2-user/file-sharing-system-aws/frontend/wsgi.py

# Restart the service
sudo systemctl restart file-sharing
```

### 3. Environment Variables Missing

If environment variables are not set:

```bash
# Check if .env file exists
ls -la /home/ec2-user/file-sharing-system-aws/frontend/.env

# Create or update .env file if needed
nano /home/ec2-user/file-sharing-system-aws/frontend/.env
```

Add the required environment variables:
```
API_ENDPOINT=https://s8yefd1acg.execute-api.ap-south-1.amazonaws.com
SECRET_KEY=your-secret-key-here
PORT=5002
```

### 4. Port Already In Use

If port 5002 is already in use:

```bash
# Check what's using the port
sudo lsof -i :5002

# Either stop the conflicting service or change the port in your .env file
```

### 5. Systemd Service Configuration Issues

If the service configuration is incorrect:

```bash
# Edit the service file
sudo nano /etc/systemd/system/file-sharing.service
```

Make sure paths and commands are correct, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart file-sharing
```

## Manual Testing

If the service still won't start, try running the application manually to see the errors:

```bash
cd /home/ec2-user/file-sharing-system-aws/frontend
source venv/bin/activate
gunicorn --workers 3 --bind 0.0.0.0:5002 wsgi:app
```

This will show any errors directly in the console.

## Check System Resources

Make sure the EC2 instance has enough resources:

```bash
# Check memory usage
free -m

# Check disk space
df -h
```

## Verify File Structure

Ensure all required files are in the correct locations:

```bash
# List all files in the application directory
find /home/ec2-user/file-sharing-system-aws/frontend -type f | sort
```
