# Makefile for Ansible Runner

.PHONY: help install build clean test validate

# Default target
help:
	@echo "Ansible Runner - Build System"
	@echo "============================="
	@echo ""
	@echo "Available targets:"
	@echo "  install    - Install dependencies in virtual environment"
	@echo "  build      - Build standalone executable with PyInstaller"
	@echo "  test       - Run tests and validation"
	@echo "  clean      - Clean build artifacts"
	@echo "  validate   - Validate configuration files"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Building executable:"
	@echo "  make install  # Setup environment"
	@echo "  make build    # Create executable"

# Install dependencies in virtual environment
install:
	@echo "🔧 Setting up virtual environment and dependencies..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed in venv/"

# Build executable using PyInstaller
build:
	@echo "🏗️ Building executable..."
	@if [ ! -d "venv" ]; then \
		echo "❌ Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	./venv/bin/python build_system/build.py
	@echo "🎉 Build completed! Check build_system/dist/ansible-runner"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build_system/build/ build_system/dist/ build/ dist/ *.spec
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "✅ Clean completed"

# Run validation tests
validate:
	@echo "🧪 Validating configurations..."
	python3 main.py validate schemas/test_with_logging.yaml
	python3 main.py validate schemas/timer_example.yaml
	@echo "✅ All configurations valid"

# Test the application
test: validate
	@echo "🧪 Running application tests..."
	python3 main.py --help
	python3 main.py systemd generate schemas/timer_example.yaml
	@echo "✅ All tests passed"

# Create portable distribution
dist: build
	@echo "📦 Creating portable distribution..."
	mkdir -p dist/portable
	cp dist/ansible-runner dist/portable/
	cp -r schemas dist/portable/examples
	cp -r docs dist/portable/
	cp README.md dist/portable/
	cd dist && tar -czf ansible-runner-portable.tar.gz portable/
	@echo "✅ Portable distribution created: dist/ansible-runner-portable.tar.gz"