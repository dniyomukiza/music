# 1. Stop udev
sudo systemctl stop systemd-udevd

# 2. Remove all files from /run/udev/data
sudo find /run/udev/data -type f -delete

# 3. Remove all directories from /run/udev/data
sudo find /run/udev/data -mindepth 1 -type d -delete

# 4. Restart udev
sudo systemctl start systemd-udevd

# 5. Check if it worked
df -h /run