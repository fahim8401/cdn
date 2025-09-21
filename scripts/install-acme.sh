#!/bin/bash

# Install ACME.sh for SSL certificate management

set -e

echo "Installing ACME.sh for SSL certificate management..."

# Download and install acme.sh
curl https://get.acme.sh | sh -s email=admin@cachenet.local

# Source the acme.sh environment
source ~/.bashrc

# Set default CA to Let's Encrypt
~/.acme.sh/acme.sh --set-default-ca --server letsencrypt

# Create acme.sh configuration directory
mkdir -p ~/.acme.sh/conf.d

echo "ACME.sh installed successfully!"
echo ""
echo "Configuration:"
echo "  Installation directory: ~/.acme.sh/"
echo "  Default CA: Let's Encrypt"
echo "  Email: admin@cachenet.local"
echo ""
echo "To issue a certificate manually:"
echo "  ~/.acme.sh/acme.sh --issue --dns dns_pdns --dnssleep 60 -d example.com -d *.example.com"
echo ""
echo "Make sure to configure PowerDNS API settings in your .env file:"
echo "  PDNS_API_URL=https://your-powerdns-server:8081"
echo "  PDNS_API_KEY=your-api-key"