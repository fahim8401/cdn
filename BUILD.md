# Build System Documentation

This document describes the build system for the Cachenet CDN Platform.

## Quick Start

### Using the Build Script (Recommended)

```bash
# Make the build script executable (if not already)
chmod +x build.sh

# Quick setup (clean, install, build, test)
./build.sh setup

# Start the services
./build.sh start
```

### Using Make

```bash
# Full build process
make ci

# Start Docker services
make docker-up
```

## Available Commands

### Build Script (`./build.sh`)

- `./build.sh help` - Show help message
- `./build.sh check` - Check system requirements
- `./build.sh install` - Install dependencies
- `./build.sh build` - Build all components
- `./build.sh lint` - Run linting
- `./build.sh test` - Run tests
- `./build.sh clean` - Clean build artifacts
- `./build.sh start` - Start Docker services
- `./build.sh stop` - Stop Docker services
- `./build.sh full` - Run full build process
- `./build.sh setup` - Clean + Install + Build + Test

### Makefile

- `make help` - Show help message
- `make check` - Check system requirements and configuration
- `make install` - Install all dependencies
- `make build` - Build all components
- `make lint` - Run linting on all components
- `make test` - Run all tests
- `make clean` - Clean build artifacts
- `make dev` - Start development environment
- `make docker-build` - Build Docker images
- `make docker-up` - Start Docker services
- `make docker-down` - Stop Docker services
- `make ci` - Full CI/CD pipeline
- `make setup` - Quick setup for new environments

## System Requirements

- Node.js (version 18+)
- npm
- Python 3.11+
- Docker
- Docker Compose

## Build Process

### 1. Frontend Components

#### Admin Dashboard (`admin/`)
- Built with React + Vite
- TypeScript support
- Tailwind CSS for styling
- Build output: `admin/dist/`

#### Client Dashboard (`client/`)
- Built with React + Vite
- Minimal dependencies
- Build output: `client/dist/`

### 2. Backend Components

#### API (`api/`)
- Flask-based Python API
- Requirements defined in `requirements.txt`
- Dependency validation through syntax checking

### 3. Infrastructure

#### Docker Configuration
- Multi-service setup with `docker-compose.yml`
- Includes database, cache, monitoring, and application services
- Configuration validation before startup

## Development Workflow

1. **Initial Setup**:
   ```bash
   ./build.sh setup
   ```

2. **Development**:
   ```bash
   # Start only core services for development
   make dev
   
   # Or start all services
   ./build.sh start
   ```

3. **Testing Changes**:
   ```bash
   # Build and test
   ./build.sh build
   ./build.sh test
   ```

4. **Production Deployment**:
   ```bash
   # Full CI/CD pipeline
   make ci
   
   # Deploy (placeholder for actual deployment)
   make deploy
   ```

## Configuration

### Environment Variables
- Copy `.env.example` to `.env`
- Update configuration values as needed
- Required for Docker services

### Docker Compose
- Services defined in `docker-compose.yml`
- Volumes for persistent data
- Health checks for critical services

## Troubleshooting

### Common Issues

1. **Build Failures**:
   ```bash
   # Clean and retry
   ./build.sh clean
   ./build.sh setup
   ```

2. **Docker Issues**:
   ```bash
   # Reset Docker environment
   docker compose down -v
   docker system prune -f
   ./build.sh start
   ```

3. **Dependency Issues**:
   ```bash
   # Reinstall dependencies
   ./build.sh clean
   ./build.sh install
   ```

### Logs and Debugging

- Check build logs for specific error messages
- Use `docker compose logs [service]` for service-specific logs
- Enable verbose output with `-v` flag where supported

## CI/CD Integration

The build system integrates with GitHub Actions through:

- `.github/workflows/build-and-test.yml` - Main build pipeline
- `.github/workflows/deploy-configs.yml` - Deployment pipeline

### Build Pipeline Steps:
1. Check system requirements
2. Install dependencies
3. Build all components
4. Run linting
5. Run tests
6. Build Docker images
7. Security scanning
8. Configuration validation

## File Structure

```
cdn/
├── admin/                 # Admin dashboard
│   ├── dist/             # Build output (gitignored)
│   ├── src/              # Source code
│   └── package.json      # Dependencies
├── client/               # Client dashboard
│   ├── dist/             # Build output (gitignored)
│   ├── src/              # Source code
│   └── package.json      # Dependencies
├── api/                  # Backend API
│   ├── requirements.txt  # Python dependencies
│   └── *.py             # Python source files
├── docker-compose.yml    # Docker services
├── Makefile             # Make build targets
├── build.sh             # Build script
├── .env.example         # Environment template
└── .gitignore           # Git ignore rules
```

## Performance Notes

- Frontend builds include code splitting recommendations
- Docker images use multi-stage builds for optimization
- Build artifacts are cached in CI/CD pipeline
- Dependencies are cached between builds

## Security

- Security scanning integrated in CI/CD
- Secrets management through environment variables
- Container vulnerability scanning with Trivy
- Dependency audit in npm builds