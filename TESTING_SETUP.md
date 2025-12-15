# Testing and Code Quality Setup

This document describes the testing infrastructure and code quality tools for the Pill Assistant integration.

## Testing Framework

The integration uses [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component) which provides the same testing utilities as Home Assistant core.

### Running Tests

```bash
# Install test dependencies
pip install -r requirements_test.txt

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_init.py -v
```

### Test Structure

```
tests/
├── __init__.py           # Test package marker
├── conftest.py           # Pytest fixtures and configuration
└── test_init.py          # Integration setup/unload tests
```

## Code Quality Tools

### Black (Code Formatting)

Black is used for automatic code formatting following PEP 8 style guide.

```bash
# Check if files need formatting
black --check custom_components/pill_assistant/

# Format files automatically
black custom_components/pill_assistant/
black tests/
```

### Mypy (Type Checking)

Mypy performs static type checking to catch type errors before runtime.

```bash
# Run type checking
mypy custom_components/pill_assistant/
```

## Configuration Files

### setup.cfg

Contains configuration for:
- pytest (test discovery and asyncio mode)
- flake8 (linting rules)
- mypy (type checking options)

### requirements_test.txt

Defines test dependencies:
- pytest-homeassistant-custom-component (Home Assistant test framework)
- black (code formatter)
- mypy (type checker)

## Current Test Coverage

### test_init.py

Tests for integration initialization:
- `test_setup_entry`: Verifies config entry setup succeeds
- `test_unload_entry`: Verifies config entry unload succeeds

## Adding New Tests

When adding new functionality, create corresponding test files:

1. **Config Flow Tests** (`test_config_flow.py`):
   - Test UI wizard steps
   - Test input validation
   - Test options flow

2. **Sensor Tests** (`test_sensor.py`):
   - Test state transitions
   - Test attribute calculations
   - Test schedule logic

3. **Service Tests** (`test_services.py`):
   - Test take_medication service
   - Test skip_medication service
   - Test refill_medication service
   - Test logging functionality

### Example Test Structure

```python
"""Test module description."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.pill_assistant.const import DOMAIN


async def test_feature(hass: HomeAssistant, mock_config_entry: MockConfigEntry):
    """Test feature description."""
    # Setup
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    
    # Test
    # ... your test code
    
    # Assert
    assert expected == actual
```

## Continuous Integration

The testing infrastructure is designed to work with GitHub Actions or other CI systems. Example workflow:

```yaml
- name: Install dependencies
  run: pip install -r requirements_test.txt

- name: Format check with black
  run: black --check custom_components/

- name: Type check with mypy
  run: mypy custom_components/

- name: Run tests
  run: pytest tests/ -v
```

## Quality Checks Passed

✅ **Black formatting**: All Python files formatted according to PEP 8  
✅ **Mypy type checking**: No type errors found  
✅ **Pytest**: All tests passing  

## Best Practices

1. **Always run tests before committing**: `pytest tests/`
2. **Format code with black**: `black custom_components/ tests/`
3. **Check types with mypy**: `mypy custom_components/`
4. **Write tests for new features**: Follow existing test patterns
5. **Use type hints**: Helps catch errors early with mypy
6. **Mock external dependencies**: Use pytest fixtures for clean tests

## Troubleshooting

### Issue: "Module not found" errors
**Solution**: Ensure `custom_components/__init__.py` exists (empty file is fine)

### Issue: AsyncIO warnings
**Solution**: Already configured in `setup.cfg` with `asyncio_mode = auto`

### Issue: Import errors in tests
**Solution**: Use `from pytest_homeassistant_custom_component.common import ...` for test utilities

## Resources

- [pytest-homeassistant-custom-component](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component)
- [Home Assistant Testing Documentation](https://developers.home-assistant.io/docs/development_testing)
- [Black Documentation](https://black.readthedocs.io/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
