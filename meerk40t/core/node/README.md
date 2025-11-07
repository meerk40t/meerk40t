# Nodes

The primary method of storing tree data for the elements object are within nodes. These tend to store all the required
data for operations, elements, or other data objects within a project. There are three primary node types. And many
minor operation types.

## Overview

The Node module provides MeerK40t's hierarchical tree data structure, serving as the foundation for all project data management. It implements a sophisticated node-based architecture that supports operations, elements, effects, and structural organization with advanced features like mixins, notifications, and dynamic type registration.

## Architecture

### Core Components

#### Node Base Class (`node.py`)
- **Abstract Base Class**: Foundation for all node types (1557+ lines)
- **Tree Structure**: Parent-child relationships with navigation methods
- **Notification System**: Event-driven updates and listener management
- **Serialization**: Persistent storage and loading capabilities
- **Type System**: Dynamic node type registration and bootstrapping

#### Bootstrap System (`bootstrap.py`)
- **Node Registration**: Automatic registration of all available node types
- **Default Settings**: Pre-configured parameters for different node types
- **Type Mapping**: String-to-class mapping for dynamic instantiation

#### Mixin System (`mixins.py`)
- **Stroked**: Stroke scaling and width management
- **FunctionalParameter**: Dynamic parameter evaluation
- **LabelDisplay**: Custom labeling and formatting
- **Suppressable**: Node visibility and processing control

### Node Hierarchy

#### Root Node (`rootnode.py`)
- **Tree Root**: Top-level container for all project data
- **Event Management**: Global tree event notification system
- **Branch Creation**: Automatic creation of primary branches (ops, elems, regmarks)
- **Listener System**: Registration of tree modification listeners

#### Branch Nodes
- **BranchOperationsNode** (`branch_ops.py`): Operation execution ordering
- **BranchElementsNode** (`branch_elems.py`): Element display and organization
- **BranchRegmarkNode** (`branch_regmark.py`): Registration mark management

### Node Types

#### Operation Nodes
Operations define laser processing actions with specific parameters and settings.

##### Cutting Operations
- **CutOpNode** (`op_cut.py`): Standard vector cutting with kerf compensation
- **EngraveOpNode** (`op_engrave.py`): Engraving operations with depth control
- **DotsOpNode** (`op_dots.py`): Dot pattern generation for special effects

##### Raster Operations
- **RasterOpNode** (`op_raster.py`): Raster engraving with DPI control
- **ImageOpNode** (`op_image.py`): Image processing operations

#### Element Nodes
Elements represent geometric and visual content in the project.

##### Geometric Elements
- **PathNode** (`elem_path.py`): Complex vector paths with geometry processing
- **RectNode** (`elem_rect.py`): Rectangular shapes
- **EllipseNode** (`elem_ellipse.py`): Elliptical and circular shapes
- **LineNode** (`elem_line.py`): Simple line segments
- **PolylineNode** (`elem_polyline.py`): Multi-segment polylines
- **PointNode** (`elem_point.py`): Single coordinate points

##### Text and Images
- **TextNode** (`elem_text.py`): Text elements with font and styling
- **ImageNode** (`elem_image.py`): Raster images with processing capabilities

##### Special Elements
- **ImageRasterNode** (`image_raster.py`): Processed raster data
- **ImageProcessedNode** (`image_processed.py`): Image processing results

#### Effect Nodes
Effects modify geometry during processing to create special laser effects.

- **WobbleEffectNode** (`effect_wobble.py`): Path wobbling for texture effects
- **HatchEffectNode** (`effect_hatch.py`): Cross-hatching patterns
- **WarpEffectNode** (`effect_warp.py`): Geometric distortion effects

#### Utility Nodes
Utility operations provide control flow and system interactions.

- **ConsoleOperation** (`util_console.py`): Console command execution
- **WaitOperation** (`util_wait.py`): Processing delays
- **HomeOperation** (`util_home.py`): Laser homing commands
- **GotoOperation** (`util_goto.py`): Position movement commands
- **InputOperation** (`util_input.py`): External input handling
- **OutputOperation** (`util_output.py`): External output control

#### Placement Nodes
Placement operations control laser positioning and job flow.

- **PlacePointNode** (`place_point.py`): Specific coordinate placement
- **PlaceCurrentNode** (`place_current.py`): Current position-based placement

#### Structural Nodes
Organizational nodes for project structure and data management.

- **FileNode** (`filenode.py`): File-based element containers
- **GroupNode** (`groupnode.py`): Hierarchical element grouping
- **LayerNode** (`layernode.py`): Layer-based organization
- **BlobNode** (`blobnode.py`): Binary data storage
- **CutNode** (`cutnode.py`): Cutcode data containers

#### Reference System
- **ReferenceNode** (`refnode.py`): Pointers to actual nodes without duplication

## Key Features

### Advanced Geometry Processing

#### Path to Cutcode Conversion (`nutils.py`)
- **Geometric Analysis**: Complex path segmentation and processing
- **Cutcode Generation**: Automatic conversion to laser-executable commands
- **Kerf Compensation**: Material thickness and cutting width adjustments
- **Closed Path Detection**: Automatic identification of closed vs open paths

#### Parameter System
- **Dynamic Evaluation**: Runtime parameter calculation and validation
- **Unit Conversion**: Automatic unit handling and conversion
- **Settings Persistence**: Configuration storage and restoration

### Mixin Architecture

#### Stroked Mixin
```python
class Stroked:
    """Advanced stroke scaling and rendering control"""
    @property
    def implied_stroke_width(self):
        """Calculates effective stroke width with scaling"""
        return self.stroke_width * self.stroke_factor if self.stroke_scale else self.stroke_width
```

- **Scale Control**: Independent stroke scaling from node transformation
- **Width Management**: Dynamic stroke width calculation
- **Rendering Optimization**: Efficient stroke geometry generation

#### FunctionalParameter Mixin
- **Expression Evaluation**: Mathematical expressions in parameters
- **Variable Substitution**: Dynamic value replacement
- **Validation**: Parameter range and type checking

#### LabelDisplay Mixin
- **Custom Formatting**: Configurable node display strings
- **Information Display**: Multi-field label composition
- **Localization Support**: Internationalization-ready labels

#### Suppressable Mixin
- **Visibility Control**: Node rendering suppression
- **Processing Control**: Selective operation execution
- **Debug Support**: Development and troubleshooting features

### Notification and Event System

#### Tree Events
- **Node Creation/Destruction**: Lifecycle event notifications
- **Modification Events**: Change tracking and undo support
- **Structural Changes**: Tree reorganization notifications

#### Listener Management
```python
def notify_created(self, node=None, **kwargs):
    """Broadcast node creation to all registered listeners"""
    for listener in self.listeners:
        if hasattr(listener, "node_created"):
            listener.node_created(node, **kwargs)
```

### Serialization and Persistence

#### Node Serialization
- **Type Preservation**: Maintains node types during save/load cycles
- **Parameter Storage**: Complete parameter state preservation
- **Relationship Maintenance**: Parent-child relationship restoration

#### Bootstrap Configuration
```python
defaults = {
    "op cut": {"speed": 12.0, "color": "red", "frequency": 30.0},
    "op engrave": {"speed": 35.0, "color": "blue", "frequency": 30.0},
    "op raster": {"speed": 150.0, "dpi": 500, "color": "black"},
    # ... additional defaults
}
```

## Technical Specifications

### Node Type Prefixes

#### Standard Prefixes
- **op**: Operation nodes (cutting, engraving, rastering)
- **elem**: Element nodes (geometric shapes, images, text)
- **effect**: Effect nodes (wobble, hatch, warp)
- **util**: Utility nodes (console, wait, home, goto)
- **place**: Placement nodes (point, current position)
- **branch**: Structural branch nodes (ops, elems, regmarks)

#### Special Types
- **root**: Tree root node
- **reference**: Reference pointer nodes
- **file**: File container nodes
- **group**: Grouping nodes
- **blob**: Binary data nodes

### Memory Management

#### Efficient Storage
- **Lazy Loading**: Nodes loaded on-demand to minimize memory usage
- **Reference System**: Avoids data duplication through intelligent referencing
- **Garbage Collection**: Automatic cleanup of unused node resources

#### Performance Optimization
- **Tree Traversal**: Efficient parent-child navigation algorithms
- **Event Batching**: Grouped notifications to reduce overhead
- **Caching**: Geometry and parameter calculation caching

### Thread Safety

#### Concurrent Access
- **Thread-Safe Operations**: Safe node manipulation across threads
- **Event Synchronization**: Proper synchronization of tree events
- **State Consistency**: Maintains data integrity during concurrent operations

## Usage Examples

### Node Creation and Manipulation
```python
# Create a root node
root = RootNode(context)

# Add branches
root.add(type="branch ops", label="Operations")
root.add(type="branch elems", label="Elements")

# Create operation nodes
cut_op = CutOpNode(speed=10.0, color="red")
root.branches["ops"].add_node(cut_op)

# Create element nodes
path_elem = PathNode(path=svg_path)
root.branches["elems"].add_node(path_elem)
```

### Effect Application
```python
# Create wobble effect
wobble = WobbleEffectNode(
    wobble_radius="1.5mm",
    wobble_interval="0.1mm",
    wobble_type="circle"
)

# Add geometry to effect
wobble.add_child(path_elem)

# Process effect
processed_geometry = wobble.process_geometry()
```

### Tree Navigation
```python
# Traverse tree structure
def traverse_tree(node, depth=0):
    indent = "  " * depth
    print(f"{indent}{node.type}: {node.label}")

    for child in node.children:
        traverse_tree(child, depth + 1)

traverse_tree(root)
```

## Development

### Creating Custom Nodes

#### Basic Node Structure
```python
from meerk40t.core.node.node import Node
from meerk40t.core.node.mixins import Stroked, LabelDisplay

class CustomNode(Node, Stroked, LabelDisplay):
    def __init__(self, **kwargs):
        super().__init__(type="custom", **kwargs)
        self.custom_property = "default_value"

    def custom_method(self):
        """Custom node functionality"""
        return self.process_data()
```

#### Node Registration
```python
# In bootstrap.py
from .custom_node import CustomNode

# Add to node registry
kernel.register_node_type("custom", CustomNode)

# Set defaults
defaults["custom"] = {"property": "value"}
```

### Mixin Development

#### Custom Mixin Creation
```python
from abc import ABC, abstractmethod

class CustomMixin(ABC):
    @abstractmethod
    def custom_functionality(self):
        """Required method for custom behavior"""
        pass

    def helper_method(self):
        """Optional helper functionality"""
        return "helper result"
```

### Testing and Validation

#### Node Testing
- **Type Validation**: Ensure proper node type registration
- **Mixin Compatibility**: Verify mixin functionality integration
- **Serialization Testing**: Validate save/load cycle integrity
- **Performance Benchmarking**: Measure node operation efficiency

## Integration Points

### With MeerK40t Core Systems
- **Elements Service**: Primary interface for node management
- **Cut Planning**: Node-based operation sequencing
- **Render Engine**: Node-based geometry processing
- **Undo System**: Node state change tracking

### External Dependencies
- **SVG Elements**: Geometry and path processing
- **Geomstr**: Advanced geometric operations
- **Units System**: Measurement and conversion handling

## Performance Characteristics

### Scalability
- **Large Projects**: Efficient handling of thousands of nodes
- **Memory Usage**: Optimized storage for complex hierarchies
- **Operation Speed**: Fast tree traversal and node manipulation

### Optimization Features
- **Lazy Evaluation**: Deferred calculation of expensive operations
- **Caching System**: Result caching for repeated operations
- **Batch Processing**: Efficient bulk node operations

## Troubleshooting

### Common Issues
- **Node Type Errors**: Verify proper type registration in bootstrap
- **Mixin Conflicts**: Check mixin compatibility and method resolution
- **Serialization Failures**: Validate parameter types and custom properties
- **Memory Leaks**: Ensure proper cleanup of node references

### Debug Features
- **Tree Inspection**: Built-in tree structure visualization
- **Node Validation**: Integrity checking for node relationships
- **Performance Profiling**: Operation timing and bottleneck identification

## Future Enhancements

### Planned Features
- **Advanced Effects**: Additional geometric transformation effects
- **Custom Node Types**: User-defined node type creation
- **Enhanced Serialization**: Improved persistence and versioning
- **Real-time Collaboration**: Multi-user node editing capabilities

### Research Areas
- **GPU Acceleration**: Hardware-accelerated geometry processing
- **Machine Learning**: AI-assisted node optimization
- **Distributed Processing**: Multi-machine node processing
- **Advanced Visualization**: 3D node relationship visualization

## Conclusion

The Node module represents the sophisticated architectural foundation of MeerK40t's project management system. With its advanced tree structure, mixin system, and comprehensive node type library, it provides the flexibility and power needed for professional laser processing workflows.

### Key Strengths
- **Extensibility**: Easy addition of new node types and functionality
- **Performance**: Optimized for large-scale project handling
- **Flexibility**: Mixin system allows custom behavior composition
- **Reliability**: Comprehensive testing and validation ensure stability
- **Integration**: Seamless integration with all MeerK40t subsystems

The node system successfully balances complexity with usability, providing developers and users with powerful tools for laser processing project management.



