#!/bin/bash

# Generate SSH keys for Cachenet edge server management

set -e

KEY_DIR="ansible/keys"
KEY_NAME="cachenet-ed25519"

echo "Generating SSH keys for Cachenet edge servers..."

# Create keys directory if it doesn't exist
mkdir -p "$KEY_DIR"

# Generate ED25519 key pair
ssh-keygen -t ed25519 -f "$KEY_DIR/$KEY_NAME" -N "" -C "cachenet-automation@$(hostname)"

# Set proper permissions
chmod 600 "$KEY_DIR/$KEY_NAME"
chmod 644 "$KEY_DIR/$KEY_NAME.pub"
chmod 700 "$KEY_DIR"

echo "SSH keys generated successfully:"
echo "  Private key: $KEY_DIR/$KEY_NAME"
echo "  Public key:  $KEY_DIR/$KEY_NAME.pub"
echo ""
echo "Public key content (add this to your edge servers):"
echo "======================================================"
cat "$KEY_DIR/$KEY_NAME.pub"
echo "======================================================"
echo ""
echo "To add this key to an edge server, run:"
echo "  ssh-copy-id -i $KEY_DIR/$KEY_NAME.pub root@[server-ip]"
echo ""
echo "Or manually add the public key to /root/.ssh/authorized_keys on each edge server."