"""
Optimization testcase scenario generators and utilities.

This module contains both the utility functions for generating geometric test patterns
and the console commands for creating various testcase scenarios for path optimization
testing and benchmarking. Each scenario creates different geometric patterns to test
specific optimization algorithms and edge cases.
"""

import random
import math
from meerk40t.tools.geomstr import Geomstr
from meerk40t.core.units import Length

# ==========
# TEST CASE CONSTANTS
# ==========

# Shape generation constants
DEFAULT_SHAPE_COUNT = 10
MIN_SHAPE_SIZE = 10000
MAX_SHAPE_SIZE = 50000
DEFAULT_CIRCLE_POINTS = 16
MIN_STAR_POINTS = 5
MAX_STAR_POINTS = 10

# Test pattern bounds (as percentages)
PATTERN_BOUNDS = {
    'min_x': 5, 'max_x': 95,
    'min_y': 5, 'max_y': 95,
    'min_size': 5, 'max_size': 20
}

# Shape type distribution
SHAPE_TYPES = {
    0: 'line',
    1: 'polyline_open', 
    2: 'polyline_closed',
    3: 'rectangle',
    4: 'ellipse'
}


# ==========
# SHAPE CREATION UTILITIES
# ==========

def create_test_line(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label):
    """
    Create a test line element.
    
    Args:
        branch: Element branch to add to
        x, y: Starting position (percentage)
        w, h: Width and height offsets (percentage)
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        label: Element label
        
    Returns:
        Created line element
    """
    x2 = min(100, max(0, x + w))
    y2 = min(100, max(0, y + h))
    
    return branch.add(
        "elem line",
        x1=float(Length(f"{x}%", relative_length=device_view.width)),
        y1=float(Length(f"{y}%", relative_length=device_view.height)),
        x2=float(Length(f"{x2}%", relative_length=device_view.width)),
        y2=float(Length(f"{y2}%", relative_length=device_view.height)),
        stroke=default_stroke,
        stroke_width=default_strokewidth,
        label=label,
    )


def create_test_polyline(branch, x, y, device_view, default_stroke, default_strokewidth, label, closed=False):
    """
    Create a test polyline element (open or closed).
    
    Args:
        branch: Element branch to add to
        x, y: Starting position (percentage)
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        label: Element label
        closed: Whether to close the polyline
        
    Returns:
        Created polyline element
    """
    points = []
    n_points = random.randint(3, 6)
    px = x
    py = y
    
    for _ in range(n_points):
        px += random.uniform(-10, 10)
        py += random.uniform(-10, 10)
        px = min(max(px, 0), 100)
        py = min(max(py, 0), 100)
        points.append(
            (
                float(Length(f"{px}%", relative_length=device_view.width)),
                float(Length(f"{py}%", relative_length=device_view.height))
            )
        )
    
    if closed:
        points.append(points[0])  # Close the polyline
    
    return branch.add(
        "elem polyline",
        geometry=Geomstr().lines(*points),
        stroke=default_stroke,
        stroke_width=default_strokewidth,
        fill=None,
        label=label,
    )


def create_test_rectangle(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label):
    """
    Create a test rectangle element.
    
    Args:
        branch: Element branch to add to
        x, y: Position (percentage)
        w, h: Width and height (percentage)
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        label: Element label
        
    Returns:
        Created rectangle element
    """
    x = min(max(x, w), 100 - w)
    y = min(max(y, h), 100 - h)
    
    return branch.add(
        "elem rect",
        x=float(Length(f"{x}%", relative_length=device_view.height)),
        y=float(Length(f"{y}%", relative_length=device_view.width)),
        width=float(Length(f"{w}%", relative_length=device_view.height)),
        height=float(Length(f"{h}%", relative_length=device_view.width)),
        stroke=default_stroke,
        stroke_width=default_strokewidth,
        fill=None,
        label=label,
    )


def create_test_ellipse(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label):
    """
    Create a test ellipse element.
    
    Args:
        branch: Element branch to add to
        x, y: Center position (percentage)
        w, h: Width and height (percentage)
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        label: Element label
        
    Returns:
        Created ellipse element
    """
    x = min(max(x, w), 100 - w)
    y = min(max(y, h), 100 - h)
    
    return branch.add(
        "elem ellipse",
        cx=float(Length(f"{x}%", relative_length=device_view.height)),
        cy=float(Length(f"{y}%", relative_length=device_view.width)),
        rx=float(Length(f"{w}%", relative_length=device_view.height)),
        ry=float(Length(f"{h}%", relative_length=device_view.width)),
        stroke=default_stroke,
        stroke_width=default_strokewidth,
        fill=None,
        label=label,
    )


# ==========
# PATTERN GENERATION FUNCTIONS
# ==========

def generate_random_test_case(branch, device_view, default_stroke, default_strokewidth, amount=None, seed=42):
    """
    Generate a random test case with various geometric shapes.
    
    Args:
        branch: Element branch to add shapes to
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        amount: Number of shapes to create (default: DEFAULT_SHAPE_COUNT)
        seed: Random seed for reproducible results
        
    Returns:
        List of created elements
    """
    if amount is None or amount < 1:
        amount = DEFAULT_SHAPE_COUNT
    
    random.seed(seed)
    data = []
    
    for i in range(amount):
        x = random.uniform(PATTERN_BOUNDS['min_x'], PATTERN_BOUNDS['max_x'])
        y = random.uniform(PATTERN_BOUNDS['min_y'], PATTERN_BOUNDS['max_y'])
        w = random.uniform(PATTERN_BOUNDS['min_size'], PATTERN_BOUNDS['max_size'])
        h = random.uniform(PATTERN_BOUNDS['min_size'], PATTERN_BOUNDS['max_size'])
        
        type_selector = random.randint(0, 4)  # 0=line, 1=poly open, 2=poly closed, 3=rectangle, 4=ellipse
        
        if type_selector == 0:
            # Line
            node = create_test_line(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, f"Testline #{i + 1}")
        elif type_selector == 1:
            # Polyline open
            node = create_test_polyline(branch, x, y, device_view, default_stroke, default_strokewidth, f"Polyline open #{i + 1}", closed=False)
        elif type_selector == 2:
            # Polyline closed
            node = create_test_polyline(branch, x, y, device_view, default_stroke, default_strokewidth, f"Polyline closed #{i + 1}", closed=True)
        elif type_selector == 3:
            # Rectangle
            node = create_test_rectangle(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, f"Rectangle #{i + 1}")
        else:
            # Ellipse
            node = create_test_ellipse(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, f"Ellipse #{i + 1}")
        
        data.append(node)
    
    return data


def generate_grid_test_case(branch, device_view, default_stroke, default_strokewidth, rows=3, cols=3, shape_type='rectangle'):
    """
    Generate a grid pattern test case.
    
    Args:
        branch: Element branch to add shapes to
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        rows: Number of rows in the grid
        cols: Number of columns in the grid
        shape_type: Type of shapes to create ('rectangle', 'ellipse', 'line')
        
    Returns:
        List of created elements
    """
    data = []
    
    # Calculate grid spacing
    x_step = 80 / cols  # Leave margins
    y_step = 80 / rows
    x_start = 10
    y_start = 10
    
    for row in range(rows):
        for col in range(cols):
            x = x_start + col * x_step
            y = y_start + row * y_step
            w = x_step * 0.6  # Size relative to grid spacing
            h = y_step * 0.6
            
            label = f"Grid {shape_type} R{row + 1}C{col + 1}"
            
            if shape_type == 'rectangle':
                node = create_test_rectangle(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label)
            elif shape_type == 'ellipse':
                node = create_test_ellipse(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label)
            elif shape_type == 'line':
                node = create_test_line(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label)
            else:
                # Default to rectangle
                node = create_test_rectangle(branch, x, y, w, h, device_view, default_stroke, default_strokewidth, label)
            
            data.append(node)
    
    return data


def generate_circular_pattern_test_case(branch, device_view, default_stroke, default_strokewidth, count=8, radius=30.0):
    """
    Generate a circular pattern test case.
    
    Args:
        branch: Element branch to add shapes to
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        count: Number of shapes in the circle
        radius: Radius of the circular pattern (percentage)
        
    Returns:
        List of created elements
    """
    data = []
    center_x = 50  # Center of canvas
    center_y = 50
    
    for i in range(count):
        angle = 2 * math.pi * i / count
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        
        # Vary shape size slightly
        size = 5 + random.uniform(-2, 2)
        
        label = f"Circle pattern #{i + 1}"
        node = create_test_ellipse(branch, x, y, size, size, device_view, default_stroke, default_strokewidth, label)
        data.append(node)
    
    return data


def generate_nested_shapes_test_case(branch, device_view, default_stroke, default_strokewidth, levels=3):
    """
    Generate nested shapes test case for containment testing.
    
    Args:
        branch: Element branch to add shapes to
        device_view: Device view for size calculations
        default_stroke: Default stroke color
        default_strokewidth: Default stroke width
        levels: Number of nesting levels
        
    Returns:
        List of created elements
    """
    data = []
    
    center_x = 50
    center_y = 50
    base_size = 40
    
    for level in range(levels):
        size = base_size - (level * 10)  # Each level gets smaller
        label = f"Nested level {level + 1}"
        
        if level % 2 == 0:
            # Alternating rectangles and ellipses
            node = create_test_rectangle(branch, center_x - size/2, center_y - size/2, size, size, device_view, default_stroke, default_strokewidth, label)
        else:
            node = create_test_ellipse(branch, center_x, center_y, size/2, size/2, device_view, default_stroke, default_strokewidth, label)
        
        data.append(node)
    
    return data


# ==========
# PLUGIN AND CONSOLE COMMANDS
# ==========

def plugin(kernel, lifecycle=None):
    """Plugin entry point following the standard MeerK40t plugin pattern."""
    if lifecycle == "postboot":
        init_commands(kernel)


def init_commands(kernel):
    """Initialize all testcase scenario generator commands."""
    self = kernel.elements

    # ==========
    # TESTCASE SCENARIO GENERATORS
    # ==========

    @self.console_argument(
        "amount",
        type=int,
        help="Number of shapes to create",
        default=DEFAULT_SHAPE_COUNT,
    )
    @self.console_command(
        "testcase",
        help="Create test case for optimization",
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase(channel, _, amount=None, data=None, post=None, **kwargs):
        """Create a random test case for path optimization testing."""
        branch = self.elem_branch

        # Generate random test case using the pattern generation functions
        created_elements = generate_random_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            amount=amount,
        )

        # Add classification post-processing
        post.append(self.post_classify(created_elements))

    @self.console_argument("rows", type=int, help="Number of rows", default=3)
    @self.console_argument("cols", type=int, help="Number of columns", default=3)
    @self.console_argument("shape", type=str, help="Shape type", default="rectangle")
    @self.console_command(
        "testcase_grid",
        help="Create grid pattern test case for optimization",
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_grid(
        channel, _, rows=None, cols=None, shape=None, data=None, post=None, **kwargs
    ):
        """Create a grid pattern test case for path optimization testing."""
        branch = self.elem_branch

        created_elements = generate_grid_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            rows=rows or 3,
            cols=cols or 3,
            shape_type=shape or "rectangle",
        )

        if post is not None:
            post.append(self.post_classify(created_elements))

    @self.console_argument(
        "count", type=int, help="Number of shapes in circle", default=8
    )
    @self.console_argument(
        "radius", type=float, help="Circle radius (percentage)", default=30.0
    )
    @self.console_command(
        "testcase_circle",
        help="Create circular pattern test case for optimization",
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_circle(
        channel, _, count=None, radius=None, data=None, post=None, **kwargs
    ):
        """Create a circular pattern test case for path optimization testing."""
        branch = self.elem_branch

        created_elements = generate_circular_pattern_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            count=count or 8,
            radius=radius or 30.0,
        )

        if post is not None:
            post.append(self.post_classify(created_elements))

    @self.console_argument(
        "levels", type=int, help="Number of nesting levels", default=3
    )
    @self.console_command(
        "testcase_nested",
        help="Create nested shapes test case for containment testing",
        input_type=None,
        output_type="elements",
    )
    def reorder_testcase_nested(
        channel, _, levels=None, data=None, post=None, **kwargs
    ):
        """Create nested shapes test case for containment testing."""
        branch = self.elem_branch

        created_elements = generate_nested_shapes_test_case(
            branch=branch,
            device_view=self.device.view,
            default_stroke=self.default_stroke,
            default_strokewidth=self.default_strokewidth,
            levels=levels or 3,
        )

        if post is not None:
            post.append(self.post_classify(created_elements))
        return "elements", data