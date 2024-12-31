# Set up autostart service
# 1. Copy service file to systemd directory
sudo cp people-monitor.service /etc/systemd/system/

# 2. Reload systemd to recognize the new service
sudo systemctl daemon-reload

# 3. Enable the service to run on boot
sudo systemctl enable people-monitor.service

# 4. Start the service immediately
sudo systemctl start people-monitor.service

# Useful commands:
# Check service status:
# sudo systemctl status people-monitor.service

# View logs:
# sudo journalctl -u people-monitor.service -f

# Stop service:
# sudo systemctl stop people-monitor.service

# Restart service:
# sudo systemctl restart people-monitor.service

# Disable autostart:
# sudo systemctl disable people-monitor.service

# Note: Make sure the paths in people-monitor.service match your actual file locations!
