#!/bin/bash

# Cachenet CDN Platform Build Script
# This script provides a simple interface to build and manage the CDN platform

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    if ! command_exists node; then
        log_error "Node.js is required but not installed"
        exit 1
    fi
    
    if ! command_exists npm; then
        log_error "npm is required but not installed"
        exit 1
    fi
    
    if ! command_exists python3; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    if ! command_exists docker; then
        log_error "Docker is required but not installed"
        exit 1
    fi
    
    if ! (command_exists "docker" && docker compose version >/dev/null 2>&1); then
        log_error "Docker Compose is required but not installed"
        exit 1
    fi
    
    log_success "All system requirements are met"
}

# Install dependencies
install_dependencies() {
    log_info "Installing dependencies..."
    
    # Check if .env exists
    if [ ! -f .env ]; then
        log_warning ".env file not found, copying from .env.example"
        cp .env.example .env
    fi
    
    # Install admin dependencies
    log_info "Installing admin dashboard dependencies..."
    cd admin
    npm install
    cd ..
    
    # Install client dependencies
    log_info "Installing client dashboard dependencies..."
    cd client
    npm install
    cd ..
    
    # Install API dependencies (optional, might require network)
    log_info "Checking API dependencies..."
    cd api
    if python3 -m pip install -r requirements.txt --dry-run > /dev/null 2>&1; then
        log_info "Installing API dependencies..."
        python3 -m pip install -r requirements.txt
    else
        log_warning "Skipping API dependencies due to network issues"
    fi
    cd ..
    
    log_success "Dependencies installation completed"
}

# Build components
build_components() {
    log_info "Building all components..."
    
    # Build admin dashboard
    log_info "Building admin dashboard..."
    cd admin
    npm run build
    cd ..
    
    # Build client dashboard
    log_info "Building client dashboard..."
    cd client
    npm run build
    cd ..
    
    log_success "All components built successfully"
}

# Run linting
run_linting() {
    log_info "Running linting and syntax checks..."
    
    # Lint admin dashboard
    log_info "Linting admin dashboard..."
    cd admin
    npm run lint || log_warning "Admin linting completed with warnings"
    cd ..
    
    # Check Python syntax
    log_info "Checking Python syntax..."
    cd api
    python3 -m py_compile app.py
    python3 -m py_compile models.py
    python3 -m py_compile celery_config.py
    cd ..
    
    # Validate Docker Compose
    log_info "Validating Docker Compose configuration..."
    docker compose config > /dev/null
    
    log_success "Linting completed"
}

# Run tests
run_tests() {
    log_info "Running tests..."
    
    # Test builds exist
    if [ ! -d "admin/dist" ]; then
        log_error "Admin build directory not found"
        exit 1
    fi
    
    if [ ! -d "client/dist" ]; then
        log_error "Client build directory not found"
        exit 1
    fi
    
    # Test Docker Compose syntax
    docker compose config > /dev/null
    
    log_success "All tests passed"
}

# Clean build artifacts
clean_build() {
    log_info "Cleaning build artifacts..."
    
    rm -rf admin/dist/
    rm -rf admin/node_modules/
    rm -rf client/dist/
    rm -rf client/node_modules/
    rm -rf api/__pycache__/
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "*.pyo" -delete 2>/dev/null || true
    
    log_success "Clean completed"
}

# Start Docker services
start_services() {
    log_info "Starting Docker services..."
    
    docker compose up -d
    
    log_success "Docker services started"
    echo ""
    log_info "Services available at:"
    log_info "  Admin Dashboard: http://localhost:3000"
    log_info "  Client Dashboard: http://localhost:3002"
    log_info "  API: http://localhost:5000"
    log_info "  Grafana: http://localhost:3001"
    log_info "  Prometheus: http://localhost:9090"
}

# Stop Docker services
stop_services() {
    log_info "Stopping Docker services..."
    docker compose down
    log_success "Docker services stopped"
}

# Full build process
full_build() {
    check_requirements
    install_dependencies
    build_components
    run_linting
    run_tests
    log_success "Full build completed successfully!"
}

# Show help
show_help() {
    echo "Cachenet CDN Platform Build Script"
    echo "=================================="
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  help          Show this help message"
    echo "  check         Check system requirements"
    echo "  install       Install dependencies"
    echo "  build         Build all components"
    echo "  lint          Run linting"
    echo "  test          Run tests"
    echo "  clean         Clean build artifacts"
    echo "  start         Start Docker services"
    echo "  stop          Stop Docker services"
    echo "  full          Run full build process"
    echo "  setup         Clean + Install + Build + Test"
    echo ""
}

# Main script logic
case "${1:-help}" in
    check)
        check_requirements
        ;;
    install)
        check_requirements
        install_dependencies
        ;;
    build)
        check_requirements
        install_dependencies
        build_components
        ;;
    lint)
        run_linting
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_build
        ;;
    start)
        check_requirements
        start_services
        ;;
    stop)
        stop_services
        ;;
    full)
        full_build
        ;;
    setup)
        clean_build
        check_requirements
        install_dependencies
        build_components
        run_tests
        ;;
    help)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac