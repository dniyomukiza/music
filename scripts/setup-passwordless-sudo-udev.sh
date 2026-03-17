#!/usr/bin/env bash
# One-time setup on the server: allow the deploy user to run udev cleanup without a password.
# Run on the server (SSH in), with sudo:  sudo bash scripts/setup-passwordless-sudo-udev.sh
# Or copy the commands from the "Manual setup" section below and run them yourself.

set -e

DEPLOY_USER="${1:-nididier}"
SUDOERS_FILE="/etc/sudoers.d/${DEPLOY_USER}-deploy-udev"

if [[ $EUID -ne 0 ]]; then
  echo "Run this script with sudo: sudo bash $0 [$DEPLOY_USER]"
  echo "Example: sudo bash scripts/setup-passwordless-sudo-udev.sh nididier"
  exit 1
fi

echo "Creating $SUDOERS_FILE for user: $DEPLOY_USER"

# Use full paths for find and systemctl (required in sudoers)
cat > "$SUDOERS_FILE" << EOF
# Allow $DEPLOY_USER to run udev cleanup without password (for CI/CD deploy).
# Created by scripts/setup-passwordless-sudo-udev.sh
$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/find /run/udev/data -type f -delete
$DEPLOY_USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl start systemd-udevd
EOF

chmod 440 "$SUDOERS_FILE"

# Validate sudoers syntax (optional but safe)
if visudo -c -f "$SUDOERS_FILE" 2>/dev/null; then
  echo "Done. $DEPLOY_USER can now run the udev commands without a password."
  echo "Test with: sudo find /run/udev/data -type f -delete && sudo systemctl start systemd-udevd"
else
  echo "WARNING: visudo check failed. Removing $SUDOERS_FILE."
  rm -f "$SUDOERS_FILE"
  exit 1
fi
