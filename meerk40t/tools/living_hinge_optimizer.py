#!/usr/bin/env python3

"""
Living Hinge Pattern Optimization for MeerK40t

This module provides optimized pattern generation specifically for living hinge applications,
building on the analysis that living hinges require pattern-based rather than line-based approaches.
"""

import math
import os
import sys
import time

from meerk40t.core.geomstr import Geomstr

class LivingHingeOptimizer:
    """
    Specialized optimizer for living hinge pattern generation.
    
    Based on analysis of the existing Pattern class system in patterns.py,
    this provides optimized algorithms specifically for flexible material applications.
    """
    
    PATTERN_TYPES = {
        'line': 'Simple parallel cuts for basic flexibility',
        'fishbone': 'Fishbone pattern for enhanced multi-directional flexibility', 
        'diagonal': 'Diagonal pattern for controlled flex direction',
        'zigzag': 'Zigzag pattern for controlled flex direction',
        'honeycomb': 'Honeycomb cells for omnidirectional flexibility',
        'spiral': 'Spiral cuts for twist flexibility'
    }
    
    @staticmethod
    def generate_optimized_hinge(outer: Geomstr, pattern_type: str, 
                                cell_width: float, cell_height: float,
                                cut_width: float = 0.1, 
                                margin: float = 0.5) -> Geomstr:
        """
        Generate optimized living hinge patterns.
        
        Args:
            outer: Boundary shape for the hinge area
            pattern_type: Type of hinge pattern ('line', 'fishbone', etc.)
            cell_width: Width of each pattern cell
            cell_height: Height of each pattern cell  
            cut_width: Width of cuts (kerf consideration)
            margin: Margin from edges
            
        Returns:
            Geomstr containing the optimized hinge pattern
        """
        if pattern_type not in LivingHingeOptimizer.PATTERN_TYPES:
            raise ValueError(f"Unknown pattern type: {pattern_type}")
        
        # Get shape bounds
        bbox = outer.bbox()
        if not bbox:
            return Geomstr()
        
        min_x, min_y, max_x, max_y = bbox
        
        # Calculate grid parameters with margins
        grid_min_x = min_x + margin
        grid_min_y = min_y + margin
        grid_max_x = max_x - margin
        grid_max_y = max_y - margin
        
        if grid_max_x <= grid_min_x or grid_max_y <= grid_min_y:
            return Geomstr()  # No space for pattern
        
        # Generate pattern grid
        result = Geomstr()
        
        y = grid_min_y
        while y < grid_max_y:
            x = grid_min_x
            while x < grid_max_x:
                # Generate pattern cell at this position
                cell_pattern = LivingHingeOptimizer._create_pattern_cell(
                    pattern_type, x, y, cell_width, cell_height, cut_width
                )
                
                # Clip to boundary and add to result
                if LivingHingeOptimizer._point_in_shape(x + cell_width/2, y + cell_height/2, outer):
                    result.append(cell_pattern)
                
                x += cell_width
            y += cell_height
        
        return result
    
    @staticmethod
    def _create_pattern_cell(pattern_type: str, x: float, y: float,
                           cell_width: float, cell_height: float, 
                           cut_width: float) -> Geomstr:
        """Create a single pattern cell at the specified position."""
        pattern = Geomstr()
        
        if pattern_type == 'line':
            # Simple horizontal cuts for flexibility
            cut_length = cell_width * 0.8
            cut_y = y + cell_height / 2
            
            pattern.line(
                complex(x + (cell_width - cut_length) / 2, cut_y),
                complex(x + (cell_width + cut_length) / 2, cut_y)
            )
            pattern.end()
            
        elif pattern_type == 'fishbone':
            # Central spine with diagonal branches
            spine_start_x = x + cell_width * 0.1
            spine_end_x = x + cell_width * 0.9
            spine_y = y + cell_height / 2
            
            # Central spine
            pattern.line(complex(spine_start_x, spine_y), complex(spine_end_x, spine_y))
            pattern.end()
            
            # Diagonal branches
            branch_length = cell_height * 0.3
            num_branches = 3
            
            for i in range(num_branches):
                branch_x = spine_start_x + (spine_end_x - spine_start_x) * (i + 1) / (num_branches + 1)
                
                # Upper branch
                pattern.line(
                    complex(branch_x, spine_y),
                    complex(branch_x + branch_length * 0.5, spine_y + branch_length * 0.5)
                )
                pattern.end()
                
                # Lower branch  
                pattern.line(
                    complex(branch_x, spine_y),
                    complex(branch_x + branch_length * 0.5, spine_y - branch_length * 0.5)
                )
                pattern.end()
                
        elif pattern_type == 'zigzag':
            # Zigzag pattern for controlled direction
            num_points = 5
            amplitude = cell_height * 0.3
            
            points = []
            for i in range(num_points):
                point_x = x + cell_width * i / (num_points - 1)
                point_y = y + cell_height / 2 + amplitude * (1 if i % 2 == 0 else -1)
                points.append(complex(point_x, point_y))
            
            for i in range(len(points) - 1):
                pattern.line(points[i], points[i + 1])
                pattern.end()
                
        elif pattern_type == 'honeycomb':
            # Hexagonal cell pattern
            hex_radius = min(cell_width, cell_height) * 0.3
            center_x = x + cell_width / 2
            center_y = y + cell_height / 2
            
            # Create hexagon
            hex_points = []
            for i in range(7):  # 7 points to close the hexagon
                angle = 2 * math.pi * i / 6
                hex_x = center_x + hex_radius * math.cos(angle)
                hex_y = center_y + hex_radius * math.sin(angle)
                hex_points.append(complex(hex_x, hex_y))
            
            for i in range(len(hex_points) - 1):
                pattern.line(hex_points[i], hex_points[i + 1])
                pattern.end()
                
        elif pattern_type == 'spiral':
            # Spiral pattern for twist flexibility
            center_x = x + cell_width / 2
            center_y = y + cell_height / 2
            max_radius = min(cell_width, cell_height) * 0.4
            
            # Create spiral
            num_turns = 2
            points_per_turn = 8
            total_points = num_turns * points_per_turn
            
            spiral_points = []
            for i in range(total_points + 1):
                t = i / points_per_turn  # Parameter from 0 to num_turns
                angle = 2 * math.pi * t
                radius = max_radius * t / num_turns
                
                spiral_x = center_x + radius * math.cos(angle)
                spiral_y = center_y + radius * math.sin(angle)
                spiral_points.append(complex(spiral_x, spiral_y))
            
            for i in range(len(spiral_points) - 1):
                pattern.line(spiral_points[i], spiral_points[i + 1])
                pattern.end()
        
        return pattern
    
    @staticmethod
    def _point_in_shape(x: float, y: float, shape: Geomstr) -> bool:
        """Simple point-in-polygon test."""
        # Simplified implementation - would use proper winding number in production
        bbox = shape.bbox()
        if not bbox:
            return False
        
        min_x, min_y, max_x, max_y = bbox
        return min_x <= x <= max_x and min_y <= y <= max_y
    
    @staticmethod
    def benchmark_hinge_patterns():
        """Benchmark different living hinge patterns."""
        print("LIVING HINGE PATTERN OPTIMIZATION")
        print("=" * 50)
        
        # Test shape: 100x50mm rectangle
        test_shape = Geomstr.rect(0, 0, 100, 50)
        
        # Test parameters
        cell_configs = [
            {'width': 5.0, 'height': 5.0, 'description': 'Coarse (5x5mm)'},
            {'width': 2.0, 'height': 2.0, 'description': 'Medium (2x2mm)'},
            {'width': 1.0, 'height': 1.0, 'description': 'Fine (1x1mm)'},
        ]
        
        for config in cell_configs:
            print(f"\n{config['description']} cells:")
            print("-" * 30)
            
            for pattern_type in LivingHingeOptimizer.PATTERN_TYPES:
                start_time = time.perf_counter()
                
                result = LivingHingeOptimizer.generate_optimized_hinge(
                    test_shape, pattern_type, 
                    config['width'], config['height']
                )
                
                execution_time = time.perf_counter() - start_time
                line_count = count_lines(result)
                
                print(f"  {pattern_type:12s}: {execution_time*1000:5.1f}ms, {line_count:4d} cuts")
        
        print("\nPattern Descriptions:")
        print("-" * 30)
        for pattern_type, description in LivingHingeOptimizer.PATTERN_TYPES.items():
            print(f"  {pattern_type:12s}: {description}")


def count_lines(geom: Geomstr) -> int:
    """Count lines in geometry."""
    if not hasattr(geom, 'index') or not hasattr(geom, 'segments'):
        return 0
    
    count = 0
    for i in range(geom.index):
        if geom._segtype(geom.segments[i]) == 41:  # TYPE_LINE
            count += 1
    return count


def demonstrate_living_hinge_integration():
    """Demonstrate integration with existing Pattern system."""
    print("\nINTEGRATION WITH EXISTING PATTERN SYSTEM")
    print("=" * 50)
    print("Recommended approach for meerk40t/patterns.py integration:")
    print()
    print("1. EXTEND LivingHinges class with optimized methods:")
    print("   - Add LivingHingeOptimizer.generate_optimized_hinge() as backend")
    print("   - Maintain existing UI compatibility")
    print("   - Add pattern type selection dropdown")
    print()
    print("2. PERFORMANCE IMPROVEMENTS:")
    print("   - Replace current Pattern-based generation with direct geometry")
    print("   - Add cell-based grid calculation for better performance")
    print("   - Implement boundary clipping for precise edges")
    print()
    print("3. NEW PATTERN TYPES:")
    print("   - fishbone: Enhanced multi-directional flexibility")
    print("   - zigzag: Controlled flex direction")
    print("   - honeycomb: Omnidirectional flexibility")
    print("   - spiral: Twist flexibility")
    print()
    print("4. CONFIGURATION OPTIONS:")
    print("   - Cell dimensions (width/height)")
    print("   - Cut width (kerf consideration)")
    print("   - Edge margins")
    print("   - Pattern density controls")


if __name__ == "__main__":
    # Add parent directory to path when running directly as a script
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    LivingHingeOptimizer.benchmark_hinge_patterns()
    demonstrate_living_hinge_integration()