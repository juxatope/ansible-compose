#!/usr/bin/env python3
"""
Build script for creating Ansible Runner executable using PyInstaller.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔨 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Command: {cmd}")
        print(f"   Error: {e.stderr}")
        sys.exit(1)

def check_dependencies():
    """Check if required dependencies are installed."""
    print("🔍 Checking dependencies...")

    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        run_command("pip install pyinstaller>=5.13.0", "Installing PyInstaller")

    try:
        import yaml
        print("✅ PyYAML found")
    except ImportError:
        print("❌ PyYAML not found. Installing...")
        run_command("pip install pyyaml>=6.0", "Installing PyYAML")

def clean_build():
    """Clean previous build artifacts."""
    print("🧹 Cleaning previous builds...")

    # Clean build artifacts in build_system directory
    build_system_dir = Path('build_system')
    directories_to_clean = [build_system_dir / 'build', build_system_dir / 'dist']

    for dir_path in directories_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   Removed {dir_path}/")

    # Also clean any old build/dist in project root
    root_dirs_to_clean = ['build', 'dist']
    for dir_name in root_dirs_to_clean:
        if Path(dir_name).exists():
            shutil.rmtree(dir_name)
            print(f"   Removed {dir_name}/ (legacy location)")

    # Clean __pycache__ directories recursively
    for pycache in Path('.').rglob('__pycache__'):
        shutil.rmtree(pycache)

    # Clean .pyc files
    for pyc_file in Path('.').rglob('*.pyc'):
        pyc_file.unlink()

    print("✅ Cleanup completed")

def build_executable():
    """Build the executable using PyInstaller."""
    spec_file = Path('build_system/build.spec')

    if not spec_file.exists():
        print("❌ build.spec file not found!")
        sys.exit(1)

    # Build using the spec file with custom paths
    build_dir = Path('build_system/build')
    dist_dir = Path('build_system/dist')
    cmd = f"pyinstaller {spec_file} --clean --noconfirm --distpath {dist_dir} --workpath {build_dir}"
    run_command(cmd, "Building executable with PyInstaller")

    # Check if the executable was created
    executable_path = Path('build_system/dist/ansible-runner')
    if executable_path.exists():
        print(f"✅ Executable created: {executable_path.absolute()}")

        # Make it executable on Unix systems
        if os.name == 'posix':
            os.chmod(executable_path, 0o755)
            print("✅ Made executable (chmod +x)")

        return executable_path
    else:
        print("❌ Executable not found after build!")
        sys.exit(1)

def test_executable(executable_path):
    """Test the built executable."""
    print("🧪 Testing executable...")

    # Test basic help command
    cmd = f"{executable_path} --help"
    result = run_command(cmd, "Testing --help command")

    if "Ansible Runner - Execute Ansible playbooks" in result.stdout:
        print("✅ Executable works correctly!")
    else:
        print("❌ Executable test failed!")
        print(f"Output: {result.stdout}")
        sys.exit(1)

    # Test validation with example config
    example_config = Path('schemas/timer_example.yaml')
    if example_config.exists():
        cmd = f"{executable_path} validate {example_config}"
        run_command(cmd, "Testing configuration validation")

def create_distribution():
    """Create a distribution package."""
    print("📦 Creating distribution package...")

    dist_dir = Path('build_system/dist')
    executable = dist_dir / 'ansible-runner'

    # Copy important files to dist directory
    files_to_copy = [
        ('README.md', 'README.md'),
        ('schemas/', 'examples/'),
        ('docs/', 'docs/'),
    ]

    for src, dst in files_to_copy:
        src_path = Path(src)
        dst_path = dist_dir / dst

        if src_path.is_file():
            dst_path.parent.mkdir(exist_ok=True)
            shutil.copy2(src_path, dst_path)
        elif src_path.is_dir():
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)

    print("✅ Distribution package created in dist/")

def print_usage_info(executable_path):
    """Print usage information for the built executable."""
    print("\n" + "="*60)
    print("🎉 BUILD SUCCESSFUL!")
    print("="*60)
    print(f"Executable location: {executable_path.absolute()}")
    print(f"File size: {executable_path.stat().st_size / (1024*1024):.1f} MB")
    print("\n📋 Usage:")
    print(f"  {executable_path} --help")
    print(f"  {executable_path} validate examples/timer_example.yaml")
    print(f"  {executable_path} run examples/timer_example.yaml --dry-run")
    print(f"  {executable_path} systemd generate examples/timer_example.yaml")
    print("\n📁 Distribution contents:")
    print("  build_system/dist/ansible-runner    - Main executable")
    print("  build_system/dist/examples/         - Configuration examples")
    print("  build_system/dist/docs/             - Complete documentation")
    print("  build_system/dist/README.md         - Project README")
    print("\n🚀 The executable is self-contained and ready to deploy!")

def main():
    """Main build process."""
    print("🏗️  Ansible Runner - Build Script")
    print("="*50)

    # Change to project root directory (parent of build_system)
    project_root = Path(__file__).parent.parent.absolute()
    os.chdir(project_root)
    print(f"📁 Working directory: {project_root}")

    # Build steps
    check_dependencies()
    clean_build()
    executable_path = build_executable()
    test_executable(executable_path)
    create_distribution()
    print_usage_info(executable_path)

if __name__ == "__main__":
    main()