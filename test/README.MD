# Meerk40t Test Suite

This directory contains comprehensive automated tests for MeerK40t's various functionalities to prevent regressions after code changes and ensure system stability.

## Test Frameworks

MeerK40t supports multiple testing frameworks for flexibility and comprehensive coverage.

### unittest (Primary Framework)

The primary test framework using Python's built-in unittest module.

**Running Tests:**
```bash
# Run all tests with verbose output
python -m unittest discover test -v

# Run specific test file
python -m unittest test.test_kernel -v

# Run specific test class
python -m unittest test.test_kernel.TestKernel -v

# Run specific test method
python -m unittest test.test_kernel.TestKernel.test_object_service_commands -v

# Run with coverage (requires coverage package)
coverage run -m unittest discover test
coverage report
```

### pytest (Alternative Framework)

pytest provides a more modern testing experience with better error reporting and additional features.

**Running Tests with pytest:**
```bash
# Run all tests
pytest

# Run specific test file
pytest test_kernel.py

# Run specific test class
pytest test_kernel.py::TestKernel

# Run specific test method
pytest test_kernel.py::TestKernel::test_object_service_commands

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=meerk40t

# Run tests matching pattern
pytest -k "kernel"

# Generate HTML coverage report
pytest --cov=meerk40t --cov-report=html
```

## Test Structure and Patterns

### Bootstrap System

All tests use a standardized bootstrap system (`bootstrap.py`) that creates a minimal MeerK40t kernel with essential plugins for testing.

```python
from test import bootstrap

def test_example():
    kernel = bootstrap.bootstrap()  # Creates test kernel
    try:
        # Test code here
        kernel.console("rect 0 0 100 100\n")  # Example command
        # Assertions here
    finally:
        kernel()  # Cleanup - calls kernel shutdown
```

### Test Categories

#### Core System Tests
- **test_kernel.py**: Kernel functionality, plugin system, lifecycle management
- **test_lifecycle.py**: Plugin lifecycle events and state transitions
- **test_settings.py**: Configuration and settings persistence

#### Device Driver Tests
- **test_drivers_*.py**: Hardware-specific driver testing (GRBL, Lihuiyu, Moshi, etc.)
- **test_spooler.py**: Job spooling and execution management

#### Core Functionality Tests
- **test_core_*.py**: Core system components (elements, cutcode, plotplanner, viewports)
- **test_elements_*.py**: Element manipulation and geometry operations
- **test_operations*.py**: Laser operation processing and optimization

#### Algorithm and Tool Tests
- **test_geomstr*.py**: Geometric data structure operations
- **test_tools_*.py**: Utility library testing (rasterplotter, pmatrix, etc.)
- **test_fill.py**: Hatch fill and wobble pattern generation

#### File Format Tests
- **test_file_svg.py**: SVG file parsing and processing
- **test_dxf_import.py**: DXF file import functionality

#### Specialized Tests
- **test_cutplan_*.py**: Cut planning and optimization algorithms
- **test_imagetools_*.py**: Image processing and manipulation
- **test_units_*.py**: Unit conversion and measurement systems

## Writing Tests

### Basic Test Structure

```python
import unittest
from test import bootstrap

class TestMyFeature(unittest.TestCase):

    def setUp(self):
        """Called before each test method"""
        self.kernel = bootstrap.bootstrap()

    def tearDown(self):
        """Called after each test method"""
        self.kernel()

    def test_basic_functionality(self):
        """Test basic feature operation"""
        # Arrange
        self.kernel.console("rect 0 0 100 100\n")

        # Act
        result = self.kernel.elements.count()

        # Assert
        self.assertGreater(result, 0)
```

### Testing Console Commands

```python
def test_console_command(self):
    """Test console command execution"""
    kernel = bootstrap.bootstrap()
    try:
        # Capture console output
        output = []
        kernel.channel("console").watch(lambda msg: output.append(msg))

        # Execute command
        kernel.console("version\n")

        # Verify output
        self.assertTrue(any("MeerK40t" in line for line in output))
    finally:
        kernel()
```

### Testing Plugin Integration

```python
def test_plugin_registration(kernel, lifecycle):
    """Example plugin for testing"""
    if lifecycle == "register":
        @kernel.console_command("test_command")
        def test_cmd(command, channel, **kwargs):
            return "test_result"

# In test method
def test_plugin_loading(self):
    kernel = bootstrap.bootstrap(plugins=[test_plugin_registration])
    try:
        result = kernel.console("test_command\n")
        self.assertEqual(result.strip(), "test_result")
    finally:
        kernel()
```

### Testing Element Operations

```python
def test_element_creation(self):
    """Test creating and manipulating elements"""
    kernel = bootstrap.bootstrap()
    try:
        # Create elements
        kernel.console("rect 0 0 100 100\n")
        kernel.console("circle 50 50 25\n")

        # Verify elements exist
        elements = list(kernel.elements.elems())
        self.assertEqual(len(elements), 2)

        # Test element properties
        rect = elements[0]
        self.assertEqual(rect.x, 0)
        self.assertEqual(rect.y, 0)
        self.assertEqual(rect.width, 100)
        self.assertEqual(rect.height, 100)

    finally:
        kernel()
```

### Testing Device Operations

```python
def test_device_spooling(self):
    """Test device job spooling"""
    kernel = bootstrap.bootstrap()
    try:
        # Get device service
        device = kernel.device

        # Create and spool a job
        kernel.console("rect 0 0 100 100\n")
        kernel.console("laser\n")  # Start laser operation

        # Verify spooling
        spooler = device.spooler
        self.assertGreater(len(spooler.queue), 0)

    finally:
        kernel()
```

## Test Data and Fixtures

### Test Files Directory

The `testfiles/` directory contains sample files for testing file import/export functionality:

- SVG files for vector import testing
- Image files for raster processing tests
- DXF files for CAD import validation
- Configuration files for settings tests

### Mock Objects

For testing components that require external dependencies:

```python
from unittest.mock import Mock, patch

def test_with_mock_device(self):
    """Test using mocked device"""
    with patch('meerk40t.device.SomeDevice') as mock_device:
        mock_device.return_value.connect.return_value = True

        kernel = bootstrap.bootstrap()
        try:
            # Test code that uses the mocked device
            result = kernel.device.connect()
            self.assertTrue(result)
        finally:
            kernel()
```

## Continuous Integration

Tests are automatically executed on pull requests and commits via GitHub Actions. The CI pipeline includes:

1. **Unit Tests**: All unittest/pytest test files
2. **Coverage Analysis**: Code coverage reporting
3. **Linting**: Code style and quality checks
4. **Type Checking**: Static type analysis

### CI Configuration

Tests run with specific environment configurations:
- Isolated test profile (`MeerK40t_TEST`)
- Disabled settings persistence
- Minimal plugin set for faster execution
- No GUI components (headless testing)

## Debugging Tests

### Running Tests in Debug Mode

```bash
# Run with Python debugger
python -m pdb -m unittest test.test_kernel.TestKernel.test_basic

# Run pytest with debugging
pytest --pdb test_kernel.py::TestKernel::test_basic
```

### Test Isolation Issues

Common issues and solutions:

1. **Settings Persistence**: Tests use `ignore_settings=True` to prevent config pollution
2. **Threading Issues**: Ensure proper kernel shutdown with `kernel()` calls
3. **Plugin Conflicts**: Use minimal bootstrap for focused testing
4. **Resource Cleanup**: Always use try/finally blocks for cleanup

### Performance Testing

```python
import time

def test_operation_performance(self):
    """Test operation performance"""
    kernel = bootstrap.bootstrap()
    try:
        start_time = time.time()

        # Perform operation
        for i in range(1000):
            kernel.console(f"rect {i} {i} {i+10} {i+10}\n")

        end_time = time.time()
        duration = end_time - start_time

        # Assert reasonable performance
        self.assertLess(duration, 5.0)  # Should complete in < 5 seconds

    finally:
        kernel()
```

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test method names
- Keep tests focused and atomic
- Use setUp/tearDown for common initialization

### Test Coverage
- Aim for high coverage of critical paths
- Test both success and failure scenarios
- Include edge cases and boundary conditions
- Test integration between components

### Test Maintenance
- Keep tests updated with code changes
- Remove obsolete tests
- Document complex test scenarios
- Use comments for non-obvious test logic

### CI/CD Integration
- Tests must pass before merging
- Monitor coverage trends
- Address flaky tests promptly
- Keep test execution time reasonable

## Contributing Tests

When adding new functionality:

1. Create corresponding test files
2. Follow existing naming conventions (`test_*.py`)
3. Include both unit and integration tests
4. Update this README if adding new test categories
5. Ensure tests run in CI environment

## Troubleshooting

### Common Test Failures

**Import Errors**: Ensure all dependencies are installed
```bash
pip install -r requirements-dev.txt
```

**Kernel Shutdown Issues**: Always call `kernel()` in finally blocks
```python
try:
    # test code
finally:
    kernel()  # Essential for cleanup
```

**Timing Issues**: Some tests may need small delays for async operations
```python
import time
time.sleep(0.1)  # Brief delay for async completion
```

**Platform Differences**: Tests should work across Windows, macOS, and Linux

This comprehensive test suite ensures MeerK40t maintains high quality and reliability across all supported platforms and use cases.