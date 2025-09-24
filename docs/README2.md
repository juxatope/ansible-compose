# Ansible Runner Service Documentation

This directory contains comprehensive documentation for the Ansible Runner Service.

## Documentation Files

### `configuration-reference.md`
Complete reference for all configuration variables available in JSON and YAML files, including:
- Field descriptions and types
- Default values
- Example configurations
- Timer scheduling options
- SystemD service settings

## Quick Links

- [Configuration Reference](configuration-reference.md) - All available configuration options
- [Timer Examples](../schemas/timer_example.yaml) - SystemD timer configuration examples
- [Basic Examples](../schemas/) - All configuration examples

## Getting Started

1. See the main [README](../README.md) for basic usage
2. Review the [Configuration Reference](configuration-reference.md) for all available options
3. Check example configurations in [../schemas/](../schemas/) directory
4. Use `python main.py validate config.yaml` to validate your configuration