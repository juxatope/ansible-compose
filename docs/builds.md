# Build System Documentation

This document explains how to build standalone executables of the Ansible Runner microservice using the integrated build system.

## Overview

The Ansible Runner includes a comprehensive build system that creates self-contained executables using PyInstaller. All build-related files and artifacts are organized in the `build_system/` directory to keep the project root clean.

## Directory Structure

```
ansible_python/
├── build_system/              # Build system directory
│   ├── build.py              # Main build script
│   ├── build.spec            # PyInstaller specification
│   ├── build/                # Temporary build artifacts (created during build)
│   └── dist/                 # Final distribution (created during build)
│       ├── ansible-runner    # Main executable (~7.4 MB)
│       ├── examples/         # Configuration examples
│       ├── docs/            # Complete documentation
│       └── README.md        # Project README
└── ...
```

## Build Methods

### Method 1: Using Make (Recommended)

The easiest way to build is using the provided Makefile:

```bash
# Install dependencies in virtual environment
make install

# Build the executable
make build

# Clean build artifacts
make clean

# Show all available targets
make help
```

### Method 2: Direct Build Script

You can also run the build script directly:

```bash
# Build executable
python3 build_system/build.py

# The script will:
# 1. Check and install dependencies
# 2. Clean previous builds
# 3. Build executable with PyInstaller
# 4. Test the executable
# 5. Create distribution package
```

## Build Process Details

### 1. Dependency Checking
The build system automatically checks for and installs required dependencies:
- **PyInstaller** (≥5.13.0) - For creating executables
- **PyYAML** (≥6.0) - For YAML configuration support

### 2. Clean Build
Before building, the system removes:
- Previous build artifacts (`build_system/build/`, `build_system/dist/`)
- Python cache files (`__pycache__`, `*.pyc`)
- Legacy build directories in project root

### 3. PyInstaller Build
The build uses a custom PyInstaller specification (`build.spec`) that:
- Packages the main application (`main.py`)
- Includes all source modules from `src/`
- Bundles configuration examples (`schemas/` → `examples/`)
- Includes documentation (`docs/`)
- Excludes unnecessary packages to reduce size

### 4. Testing
After building, the system automatically:
- Tests the executable with `--help` command
- Validates example configurations
- Verifies all components work correctly

### 5. Distribution Package
Creates a complete distribution with:
- Self-contained executable
- Configuration examples
- Full documentation
- Project README

## Build Configuration

### PyInstaller Specification (build.spec)

Key configuration options in `build_system/build.spec`:

```python
# Main application entry point
['main.py']

# Include data files
datas=[
    ('schemas', 'schemas'),    # Configuration examples
    ('docs', 'docs'),         # Documentation
]

# Hidden imports (ensures all modules are included)
hiddenimports=[
    'src.ansible_service',
    'src.config.loader',
    # ... all microservice modules
    'yaml',                   # YAML support
]

# Excluded packages (reduces executable size)
excludes=[
    'tkinter', 'matplotlib', 'numpy', 'pandas',
    'jupyter', 'IPython',
]

# Executable options
name='ansible-runner'          # Output name
console=True                   # Console application
upx=True                      # Compress with UPX
```

### Build Script Features

The `build.py` script includes:

- **Automatic dependency detection and installation**
- **Cross-platform path handling**
- **Comprehensive error reporting**
- **Build verification and testing**
- **File size reporting**
- **Usage instructions**

## Using the Built Executable

### Basic Usage

```bash
# Show help
./build_system/dist/ansible-runner --help

# Validate configuration
./build_system/dist/ansible-runner validate examples/timer_example.yaml

# Run playbook (dry-run)
./build_system/dist/ansible-runner run examples/timer_example.yaml --dry-run

# Generate systemd service
./build_system/dist/ansible-runner systemd generate examples/timer_example.yaml
```

### Deployment

The executable is completely self-contained and includes:
- Python interpreter
- All required libraries
- Application source code
- Configuration examples
- Documentation

Simply copy `build_system/dist/ansible-runner` to your target system.

## Troubleshooting

### Build Fails - Missing Dependencies

```bash
# Install missing dependencies manually
pip install pyinstaller>=5.13.0 pyyaml>=6.0

# Or use the virtual environment approach
make install
make build
```

### Build Fails - Permission Issues

```bash
# Ensure build script is executable
chmod +x build_system/build.py

# Check file permissions
ls -la build_system/
```

### Large Executable Size

The executable (~7.4 MB) includes:
- Python interpreter
- All dependencies
- Application code
- Bundled data files

To reduce size:
1. Add more packages to `excludes` in `build.spec`
2. Remove unnecessary data files
3. Disable UPX compression if it causes issues

### Import Errors in Built Executable

If the executable fails with import errors:
1. Add missing modules to `hiddenimports` in `build.spec`
2. Ensure all source files are properly structured
3. Check that relative imports work correctly

## Advanced Configuration

### Custom Build Paths

You can modify paths in `build.py`:

```python
# Change output directories
build_dir = Path('custom_build')
dist_dir = Path('custom_dist')
```

### Additional Data Files

Add more data to the executable in `build.spec`:

```python
datas=[
    ('schemas', 'schemas'),
    ('docs', 'docs'),
    ('custom_dir', 'custom_dir'),  # Add custom directory
]
```

### Build Hooks

You can add custom build steps in `build.py`:

```python
def custom_post_build():
    """Custom actions after successful build."""
    # Add your custom logic here
    pass

# Call in main()
custom_post_build()
```

## Performance

### Build Times
- Clean build: ~30-60 seconds
- Incremental build: ~15-30 seconds
- Dependencies check: ~2-5 seconds

### Runtime Performance
- Startup time: ~1-2 seconds
- Memory usage: ~50-100 MB
- Execution speed: Similar to Python script

## Distribution

### Portable Package

The build system creates a portable distribution in `build_system/dist/` containing:
- `ansible-runner` - Main executable
- `examples/` - Configuration examples
- `docs/` - Complete documentation
- `README.md` - Project overview

### Archive Creation

You can create a distributable archive:

```bash
cd build_system/dist
tar -czf ansible-runner-portable.tar.gz *
```

Or add to the Makefile:

```bash
make dist  # Creates portable tarball
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build Executable
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Build executable
        run: |
          make install
          make build
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: ansible-runner-executable
          path: build_system/dist/ansible-runner
```

### Build Verification

The build system includes automatic testing:
- Help command functionality
- Configuration validation
- Core feature verification

## Security Considerations

### Executable Security
- The executable contains all source code (not obfuscated)
- Sensitive information should not be embedded
- Use external configuration files for secrets

### Build Environment
- Build on trusted systems
- Verify dependencies before building
- Use virtual environments for isolation

## Maintenance

### Updating Dependencies
- Update `requirements.txt` for new dependencies
- Add new modules to `hiddenimports` in `build.spec`
- Test builds after dependency changes

### Version Management
- Update version strings in source code
- Tag releases in git
- Document build requirements for each version

## Support

For build-related issues:
1. Check this documentation
2. Review error messages carefully
3. Ensure all dependencies are installed
4. Try a clean build (`make clean && make build`)
5. Check the project issues on GitHub

The build system is designed to be robust and user-friendly. Most common issues are resolved by ensuring proper dependencies and using the recommended Make targets.