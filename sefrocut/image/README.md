# SefroCut Image Processing Module

## Overview

The Image Processing Module provides comprehensive image manipulation and analysis capabilities. 
This module enables users to process images for laser engraving, cutting, and other fabrication tasks 
through a set of image operations, computer vision algorithms, and console commands.

## Architecture

```
sefrocut/image/
├── imagetools.py      # Core image processing functions and console commands
├── dither.py          # Dithering algorithms with Numba optimization
├── __init__.py        # Module initialization
└── README.md          # This documentation
```

### Core Components

- **ImageTools (imagetools.py)**: Main processing engine with PIL/Pillow integration
- **Dither Engine (dither.py)**: High-performance dithering algorithms using Numba JIT compilation
- **Console Integration**: 30+ console commands for image manipulation
- **OpenCV Integration**: Advanced computer vision features (optional)

## Key Features

### Image Processing Operations
- **Thresholding**: Convert images to binary using various threshold methods
- **Dithering**: 12 different dithering algorithms including Floyd-Steinberg, Atkinson, Jarvis-Judice-Ninke
- **Color Adjustments**: Contrast, brightness, gamma correction
- **Filters**: Blur, sharpen, emboss, edge detection, smoothing
- **Transformations**: Flip, mirror, rotate, crop, resize
- **Morphological Operations**: Erosion, dilation, opening, closing

### Computer Vision (OpenCV)
- **Contour Detection**: Extract vector paths from images (`img_to_polygons`, `img_to_rectangles`)
- **Image Segmentation**: Split complex images into processable regions
- **Shape Analysis**: Convert raster images to geometric primitives

### Laser-Specific Processing
- **Image Loading**: Automatic scaling and centering for laser beds
- **Raster Optimization**: Prepare images for efficient laser processing
- **Format Conversion**: Support for various image formats (PNG, JPEG, BMP, etc.)

## Dependencies

### Required
- **PIL/Pillow**: Core image processing library
- **NumPy**: Array operations for image data

### Optional
- **OpenCV**: Advanced computer vision features
  - Contour detection and analysis
  - Morphological operations
  - Image segmentation algorithms

## Core Functions

### Image Analysis
```python
# Convert image contours to geometric polygons
polygons = img_to_polygons(image, threshold=128, contour_levels=3)

# Extract bounding rectangles from image regions
rectangles = img_to_rectangles(image, threshold=128, min_area=100)

# Split complex images into sub-regions
subimages = split_image_into_subimages(image, threshold=128, min_gap=10)
```

### Image Processing Pipeline
```python
# Load and preprocess image
image = Image.open('input.png')

# Apply processing operations
processed = adjust_contrast(image, factor=1.2)
processed = apply_filter(processed, 'sharpen')
processed = threshold_image(processed, method='otsu')

# Convert for laser processing
vectors = img_to_polygons(processed)
```

## Console Commands

The module integrates with SefroCut's console system, providing 30+ commands for image manipulation:

### Basic Operations
- `image threshold <value>` - Apply threshold to current image
- `image dither <method>` - Apply dithering (floyd-steinberg, atkinson, etc.)
- `image contrast <factor>` - Adjust image contrast
- `image brightness <factor>` - Adjust image brightness

### Filters and Effects
- `image blur <radius>` - Apply Gaussian blur
- `image sharpen <factor>` - Sharpen image
- `image emboss` - Apply emboss effect
- `image edge` - Detect edges
- `image smooth` - Apply smoothing filter

### Transformations
- `image flip` - Flip image vertically
- `image mirror` - Mirror image horizontally
- `image rotate <angle>` - Rotate image by specified angle
- `image crop <x> <y> <width> <height>` - Crop image region
- `image resize <width> <height>` - Resize image

### Advanced Processing
- `image opencv_contour` - Extract contours using OpenCV
- `image split` - Split image into regions
- `image gamma <value>` - Apply gamma correction

## Dithering Algorithms

The dithering engine provides 12 high-performance algorithms optimized with Numba:

### Error Diffusion Methods
- **Floyd-Steinberg**: Classic error diffusion algorithm
- **Atkinson**: Low-noise dithering for artistic effects
- **Jarvis-Judice-Ninke**: High-quality, low-noise dithering
- **Stucki**: Balanced quality and performance
- **Burkes**: Optimized for speed
- **Sierra**: Family of three algorithms (Sierra3, Sierra2, Sierra-2-4a)
- **Shiau-Fan**: Two variants for different quality levels

### Ordered Dithering
- **Bayer Matrix**: 8x8 ordered dithering matrix
- **Bayer-Blue**: Bayer matrix with blue noise addition

## Usage Examples

### Basic Image Processing Workflow
```bash
# Load an image
load input.png

# Apply processing
image contrast 1.2
image sharpen 1.5
image threshold 128

# Convert to vectors for cutting
image opencv_contour
```

### Dithering for Laser Engraving
```bash
# Load grayscale image
load photo.jpg

# Apply artistic dithering
image dither atkinson

# Or use classic Floyd-Steinberg
image dither floyd-steinberg
```

### Advanced Contour Extraction
```bash
# Load technical drawing
load schematic.png

# Extract vector paths
image opencv_contour

# Split into manageable regions
image split
```

## Integration with SefroCut

### Plugin Registration
The module registers with SefroCut's kernel system during the `register` lifecycle phase:

```python
def plugin(kernel, lifecycle=None):
    if lifecycle == "register":
        # Register image processing commands
        kernel.register("console/command/image", ImageCommands(kernel))
```

### Element Creation
Processed images are added to SefroCut's element tree as `elem image` nodes with proper matrix transformations for laser bed positioning.

### Settings Integration
The module respects SefroCut settings for:
- `scale_oversized_images`: Automatic scaling for laser bed dimensions
- `center_image_on_load`: Automatic centering on bed
- `create_image_group`: Group organization for multi-image operations

## Performance Considerations

### Numba Optimization
Dithering algorithms use Numba JIT compilation for significant performance improvements:
- **Without Numba**: ~10-50x slower execution
- **With Numba**: Near-native performance for pixel operations

### Memory Management
- Large images are processed in-place where possible
- NumPy arrays used for efficient memory access patterns
- PIL images converted to arrays only when necessary for computation

### OpenCV Acceleration
Optional OpenCV integration provides:
- Hardware-accelerated image processing
- Advanced morphological operations
- Real-time contour detection

## Error Handling

The module provides robust error handling for:
- **Missing Dependencies**: Graceful fallback when OpenCV is unavailable
- **Invalid Images**: Comprehensive validation of image formats and data
- **Memory Limits**: Chunked processing for large images
- **Parameter Validation**: Range checking for all numeric parameters

## Testing

The image processing module is validated through SefroCut's test suite:
- Unit tests for individual functions
- Integration tests for console commands
- Performance benchmarks for dithering algorithms
- Compatibility tests across different image formats

## Future Enhancements

Potential areas for expansion:
- **AI-Powered Processing**: Machine learning-based image enhancement
- **Advanced Segmentation**: More sophisticated region splitting algorithms
- **Real-time Processing**: Live preview during parameter adjustment
- **Format Support**: Additional image formats and color spaces
- **Hardware Acceleration**: GPU-based processing for large images

## Contributing

When contributing to the image processing module:
1. Maintain compatibility with existing SefroCut architecture
2. Add comprehensive tests for new functionality
3. Document new console commands in this README
4. Consider performance implications for large images
5. Test with both PIL-only and OpenCV-enhanced configurations

## Related Modules

- **core/elements**: Element tree management and node operations
- **core/cutplan**: Laser job optimization and path planning
- **gui/**: User interface components for image operations
- **device/**: Hardware-specific image processing adaptations
