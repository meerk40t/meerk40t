#!/usr/bin/env python3
"""
Test script for spiral hatch patterns with different shapes
"""

import matplotlib.pyplot as plt
import sys
import os
import math

# Add the meerk40t directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from meerk40t.core.geomstr import Geomstr, TYPE_LINE

def create_shape_tests():
    """Test spiral hatch patterns with different shapes"""

    print("Testing spiral hatch patterns with different shapes...")

    # Test shapes
    test_shapes = []

    # 1. Rectangle
    rect = Geomstr.rect(0, 0, 100, 100)
    test_shapes.append(("Rectangle", rect))

    # 2. Circle (approximated with many segments)
    circle = Geomstr()
    center_x, center_y = 50, 50
    radius = 40
    num_segments = 32
    for i in range(num_segments):
        angle1 = 2 * math.pi * i / num_segments
        angle2 = 2 * math.pi * (i + 1) / num_segments
        x1 = center_x + radius * math.cos(angle1)
        y1 = center_y + radius * math.sin(angle1)
        x2 = center_x + radius * math.cos(angle2)
        y2 = center_y + radius * math.sin(angle2)
        circle.line(complex(x1, y1), complex(x2, y2))
    circle.close()
    test_shapes.append(("Circle", circle))

    # 3. Triangle
    triangle = Geomstr()
    triangle.line(complex(20, 20), complex(80, 20))
    triangle.end()
    triangle.line(complex(80, 20), complex(50, 80))
    triangle.end()
    triangle.line(complex(50, 80), complex(20, 20))
    triangle.end()
    test_shapes.append(("Triangle", triangle))

    # 4. Star shape
    star = Geomstr()
    center_x, center_y = 50, 50
    outer_radius = 40
    inner_radius = 20
    num_points = 5
    for i in range(num_points * 2):
        radius = outer_radius if i % 2 == 0 else inner_radius
        angle = math.pi / 2 + 2 * math.pi * i / (num_points * 2)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        star.line(complex(x, y), complex(
            center_x + (outer_radius if (i + 1) % 2 == 0 else inner_radius) * math.cos(math.pi / 2 + 2 * math.pi * (i + 1) / (num_points * 2)),
            center_y + (outer_radius if (i + 1) % 2 == 0 else inner_radius) * math.sin(math.pi / 2 + 2 * math.pi * (i + 1) / (num_points * 2))
        ))
        star.end()
    test_shapes.append(("Star", star))

    # 5. Complex shape (rectangle with cutout)
    complex_shape = Geomstr.rect(0, 0, 100, 100)
    # Add a circular cutout
    complex_shape.append(Geomstr.circle(15, 70, 70))
    # For simplicity, just test the rectangle for now
    test_shapes.append(("Rect with hole", complex_shape))

    # 6. Complex shape (Self-overlapping polygon)
    complex_shape = Geomstr()
    complex_shape.line(complex(0, 0), complex(50, 100))
    complex_shape.line(complex(50, 100), complex(100, 0))
    complex_shape.line(complex(100, 0), complex(0, 66))
    complex_shape.line(complex(0, 66), complex(100, 66))
    complex_shape.line(complex(100, 66), complex(0, 0))
    test_shapes.append(("Overlapping polygon", complex_shape))


    # Create visualization
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for idx, (shape_name, orgshape) in enumerate(test_shapes[:6]):  # Limit to 6 shapes
        ax = axes[idx]
        shape = orgshape.segmented(distance=2)
        # Plot shape outline
        for i in range(shape.index):
            segment = shape.segments[i]
            seg_type = shape._segtype(segment)
            if seg_type == TYPE_LINE:
                start = segment[0]
                end = segment[4]
                ax.plot([start.real, end.real], [start.imag, end.imag], 'k-', linewidth=2)

        # Generate spiral hatch
        try:
            spiral_hatch = Geomstr.hatch_spiral(shape, angle=math.pi/4, spacing=8)
            print(f"{shape_name}: {spiral_hatch.index} hatch segments")

            # Plot spiral hatch lines with different visibility settings for different shapes
            hatch_count = 0
            for i in range(spiral_hatch.index):
                segment = spiral_hatch.segments[i]
                seg_type = spiral_hatch._segtype(segment)
                if seg_type == TYPE_LINE:
                    start = segment[0]
                    end = segment[4]
                    # Use different alpha and linewidth for better visibility
                    if shape_name in ["Triangle", "Star"]:
                        # Make lines more visible for complex shapes
                        ax.plot([start.real, end.real], [start.imag, end.imag], 'r-', alpha=0.9, linewidth=1.5)
                    else:
                        ax.plot([start.real, end.real], [start.imag, end.imag], 'r-', alpha=0.7, linewidth=1)
                    hatch_count += 1
                    if hatch_count > 200:  # Limit for performance
                        break

        except Exception as e:
            print(f"Error hatching {shape_name}: {e}")

        ax.set_title(f'{shape_name}\n{spiral_hatch.index if "spiral_hatch" in locals() else 0} segments')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        
        # Set axis limits based on shape type for better visibility
        if shape_name == "Triangle":
            ax.set_xlim(15, 85)
            ax.set_ylim(15, 85)
        elif shape_name == "Star":
            ax.set_xlim(5, 95)
            ax.set_ylim(5, 95)
        else:
            ax.set_xlim(-10, 110)
            ax.set_ylim(-10, 110)

    # Hide empty subplots
    for idx in range(len(test_shapes), 6):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.savefig('spiral_hatch_shape_tests.png', dpi=150, bbox_inches='tight')
    print("Shape tests saved as spiral_hatch_shape_tests.png")
    print("Red lines = spiral hatch patterns, Black lines = shape outlines")

if __name__ == "__main__":
    create_shape_tests()