# SefroCut GUI Test Suite

This directory contains specialized tests for SefroCut's graphical user interface components. These tests focus on GUI functionality, wxPython widget interactions, and visual component behavior.

## Overview

GUI tests are **optional and not automatically executed** in CI/CD pipelines due to:
- wxPython GUI framework requirements
- Platform-specific GUI behavior differences
- Headless environment limitations
- Complex setup requirements for GUI testing

## Test Environment Setup

### Prerequisites

**Required Dependencies:**
```bash
pip install wxPython
```

**Platform Considerations:**
- **Windows**: Native wxPython support
- **macOS**: May require additional setup for GUI testing
- **Linux**: Requires X11 or virtual display (Xvfb) for headless testing

### Running GUI Tests

**Manual Execution:**
```bash
# Run all GUI tests
python -m unittest discover testgui -v

# Run specific GUI test
python -m unittest testgui.test_gui_choicepropertypanel -v

# Run with pytest
pytest testgui/
```

**Headless Linux Testing:**
```bash
# Install virtual display
sudo apt-get install xvfb

# Run tests with virtual display
xvfb-run -a python -m unittest discover testgui -v
```

## Test Architecture

### Bootstrap System

GUI tests use a specialized bootstrap system (`bootstrap.py`) that:
- Initializes a test kernel with GUI-capable plugins
- Sets up dummy devices for testing
- Configures SVG and DXF I/O support
- Enables console output for debugging

```python
from testgui import bootstrap

def test_gui_component():
    kernel = bootstrap.bootstrap()  # GUI-enabled kernel
    try:
        # GUI test code here
        pass
    finally:
        bootstrap.destroy(kernel)  # Proper cleanup
```

### Mock Context System

The `mock_context.py` provides a minimal wxPython-free context for testing GUI logic without actual GUI components:

```python
from testgui.mock_context import MockContext

def test_without_wxpython():
    context = MockContext()
    # Test GUI logic without wxPython widgets
    # Useful for testing business logic separately
```

**MockContext Features:**
- Signal/listener system simulation
- Theme property mocking
- Channel logging (no-op for tests)
- Setting defaults for GUI preferences

## Test Categories

### GUI Component Tests

#### test_gui_choicepropertypanel.py
Tests for choice property panel widgets and configuration dialogs.

**Test Coverage:**
- Property panel creation and initialization
- Choice widget behavior and validation
- Configuration dialog interactions
- Setting persistence and restoration

**Example Test Pattern:**
```python
def test_choice_panel_creation(self):
    """Test creating choice property panels"""
    app = wx.App()  # GUI application required
    try:
        panel = ChoicePropertyPanel(parent=None, context=self.context)
        # Test panel functionality
        self.assertIsNotNone(panel.choice_widget)
    finally:
        app.Destroy()
```

### Font and Typography Tests

#### test_ttf.py
Tests for TrueType font rendering and GUI font selection components.

**Test Coverage:**
- Font loading and validation
- Character mapping and glyph rendering
- Font selection dialog behavior
- Text rendering performance

### Algorithm Validation Scripts

#### testscripts/ Directory
Performance and correctness validation scripts for GUI-exposed algorithms:

- **complete_cag_comparison.py**: Comprehensive algorithm comparison testing
- **test_optimization_comparison.py**: Optimization algorithm benchmarking
- **test_reorder_optimization.py**: Path reordering optimization validation
- **threshold_testing.py**: Threshold parameter testing and validation

**Running Validation Scripts:**
```python
# From testgui directory
python testscripts/complete_cag_comparison.py
python testscripts/test_optimization_comparison.py
```

## GUI Testing Challenges

### wxPython Specific Issues

**Platform Dependencies:**
```python
import platform
import wx

def is_platform_supported():
    """Check if current platform supports GUI testing"""
    system = platform.system().lower()
    if system == "windows":
        return True
    elif system == "darwin":  # macOS
        return True
    elif system == "linux":
        # Check for display
        return os.environ.get('DISPLAY') is not None
    return False
```

**Widget Lifecycle Management:**
```python
def test_with_widget_lifecycle(self):
    """Proper wxPython widget testing pattern"""
    app = wx.App(False)  # Create app without redirecting stdout
    try:
        frame = wx.Frame(None, title="Test Frame")
        panel = TestPanel(frame)

        # Test widget interactions
        self.assertTrue(panel.IsShown())

        frame.Destroy()  # Explicit cleanup
    finally:
        app.Destroy()  # Always destroy app
```

### Event Handling Testing

**Mock Event Testing:**
```python
def test_button_click(self):
    """Test button click event handling"""
    app = wx.App()
    try:
        frame = wx.Frame(None)
        button = wx.Button(frame, label="Test")

        # Create mock event
        event = wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId())
        event.SetEventObject(button)

        # Simulate click
        button.Command(event)

        # Verify expected behavior
        self.assertTrue(button_clicked_flag)

    finally:
        frame.Destroy()
        app.Destroy()
```

### Dialog Testing

**Modal Dialog Testing:**
```python
def test_modal_dialog(self):
    """Test modal dialog behavior"""
    app = wx.App()
    try:
        parent = wx.Frame(None)

        # Create dialog
        dialog = TestDialog(parent)

        # Simulate user interaction
        dialog.choice.SetSelection(1)
        dialog.OnOK(None)  # Simulate OK button click

        # Verify dialog result
        self.assertEqual(dialog.result, expected_value)

    finally:
        parent.Destroy()
        app.Destroy()
```

## Best Practices

### Test Isolation

**GUI Test Setup:**
```python
class TestGUIComponents(unittest.TestCase):

    def setUp(self):
        """Set up GUI test environment"""
        self.app = wx.App(False)  # Don't redirect stdout
        self.frame = wx.Frame(None, title="Test Frame")
        self.context = MockContext()

    def tearDown(self):
        """Clean up GUI test environment"""
        if hasattr(self, 'frame') and self.frame:
            self.frame.Destroy()
        if hasattr(self, 'app') and self.app:
            self.app.Destroy()
```

### Platform-Specific Testing

**Conditional Test Execution:**
```python
@unittest.skipUnless(is_platform_supported(), "GUI testing not supported on this platform")
class TestGUIComponents(unittest.TestCase):
    # GUI tests that only run on supported platforms
    pass
```

### Memory Management

**Prevent Memory Leaks:**
```python
def test_large_gui_operation(self):
    """Test operations that create many GUI objects"""
    app = wx.App()
    objects_created = []

    try:
        for i in range(100):
            obj = create_gui_object()
            objects_created.append(obj)
            # Test object functionality

        # Verify all objects are valid
        self.assertTrue(all(obj.IsOk() for obj in objects_created))

    finally:
        # Explicit cleanup
        for obj in objects_created:
            if hasattr(obj, 'Destroy'):
                obj.Destroy()
        app.Destroy()
```

### Performance Testing

**GUI Responsiveness Testing:**
```python
def test_gui_performance(self):
    """Test GUI operation performance"""
    app = wx.App()
    start_time = time.time()

    try:
        frame = wx.Frame(None)
        # Perform GUI operations
        for i in range(1000):
            panel = wx.Panel(frame)
            panel.Destroy()  # Immediate cleanup

        end_time = time.time()
        duration = end_time - start_time

        # Assert reasonable performance
        self.assertLess(duration, 2.0)  # Should complete in < 2 seconds

    finally:
        frame.Destroy()
        app.Destroy()
```

## CI/CD Integration

### Selective Test Execution

**Environment Detection:**
```python
def should_run_gui_tests():
    """Determine if GUI tests should run in current environment"""
    # Check for GUI capabilities
    try:
        import wx
        app = wx.App(False)
        app.Destroy()
        return True
    except ImportError:
        return False
    except Exception:
        return False
```

**Conditional Test Suite:**
```python
if should_run_gui_tests():
    # Import and run GUI tests
    from testgui import test_gui_choicepropertypanel
    # ... other GUI test imports
else:
    print("GUI tests skipped - wxPython not available or display not accessible")
```

### Docker Testing

**Dockerfile for GUI Testing:**
```dockerfile
FROM python:3.9

# Install GUI testing dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    libgtk-3-0 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Set up virtual display
ENV DISPLAY=:99

# Run GUI tests
CMD xvfb-run -a python -m unittest discover testgui -v
```

## Debugging GUI Tests

### Visual Debugging

**Screenshot Capture:**
```python
def capture_screenshot(widget, filename):
    """Capture screenshot of GUI widget for debugging"""
    if hasattr(widget, 'GetScreenRect'):
        rect = widget.GetScreenRect()
        # Capture and save screenshot
        # (Implementation depends on platform)
        pass
```

### Logging GUI Events

**Event Logging:**
```python
def log_gui_events(widget):
    """Log GUI events for debugging"""
    def on_event(event):
        print(f"GUI Event: {event.GetEventType()} on {widget.__class__.__name__}")
        event.Skip()  # Continue event processing

    widget.Bind(wx.EVT_ANY, on_event)
```

### Test Failure Analysis

**Common GUI Test Failures:**
- **Widget not found**: Check widget creation timing
- **Event not fired**: Verify event binding and triggering
- **Platform differences**: Test on multiple platforms
- **Memory issues**: Ensure proper cleanup in tearDown

## Contributing GUI Tests

### Adding New GUI Tests

1. **Follow naming convention**: `test_gui_*.py`
2. **Use proper setup/teardown**: Initialize and cleanup wxPython objects
3. **Platform compatibility**: Test on Windows, macOS, and Linux
4. **Mock when possible**: Use MockContext for logic testing
5. **Document platform requirements**: Note any platform-specific behavior

### GUI Test Checklist

- [ ] wxPython app properly initialized and destroyed
- [ ] All widgets properly parented and destroyed
- [ ] Events properly bound and tested
- [ ] Platform-specific code conditional
- [ ] Memory leaks prevented through proper cleanup
- [ ] Test runs in headless environment (Linux with Xvfb)
- [ ] MockContext used for non-visual logic testing

## Troubleshooting

### Common Issues

**"wxPython not found" Error:**
```bash
# Install wxPython
pip install wxPython

# On Linux, may need system dependencies
sudo apt-get install python3-wxgtk4.0
```

**"Display not accessible" Error:**
```bash
# Use virtual display on Linux
xvfb-run -a python -m unittest testgui.test_gui_choicepropertypanel
```

**"Segmentation fault" on Linux:**
- Ensure X11 or Xvfb is properly configured
- Check wxPython version compatibility
- Try running with different display settings

**Memory leaks in tests:**
- Always call `Destroy()` on wxPython objects
- Use proper tearDown methods
- Monitor memory usage during test runs

This GUI test suite ensures SefroCut's user interface components maintain functionality and performance across different platforms and usage scenarios.
