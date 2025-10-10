# Online Help: Imageproperty

## Overview

This help page covers the **Imageproperty** functionality in MeerK40t.

This panel provides controls for imageproperty functionality. Key controls include "Enable" (checkbox), "Reset" (button), "Invert" (checkbox).

## Generic Properties
![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/e521f077-6ec4-4464-a8d1-ae2e33c32ac8)

## Modification
![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/f0331aa4-76a9-4291-b8b2-642f38642bcc)

## Vectorization
![grafik](https://github.com/meerk40t/meerk40t/assets/2670784/24f98e75-65ab-42f9-90c0-a9c3a6a6ac38)

## Resolution / DPI: what it really means
Every image has a dpi value associated to it, so how many dots / pixels come to one inch. This is a device specific indicator, as the internal resolutions of different laser devices differ.
Additionally a picture can come already with an indicator of what the intended resolution of an image should look like. Please note that you need to set the associated preference setting to allow this to happen, if the option is not set (or the image has no dpi info) then the resolution will be set to 96 dpi.
![grafik](https://github.com/user-attachments/assets/ee673e54-9d9e-4891-b116-322151d62576)

Let's take a picture with an 'intrinsic' (associated) dpi value of 96 dpi and 192x192 pixel size:

![step1_transformed_682,66_682,66](https://github.com/user-attachments/assets/6fc75ba0-4c0c-4502-90c4-e79095822daa)

- The intention is that these 192 pixels would take up a space of 2 inches.
- On the scene, i.e. on the screen, that has intentionally a very high resolution to allow fine adjustments and be compatible with every device, a pixel of that 96 dpi image will be scaled up by 682 to end up at 682 internal units so that the image again ends up at 2 inches.
- If you look closely then you will see that due to the internal resolution of the device one pixel will be "painted" by a black rectangle (internally several device "pixel" wide). This is intentional to keep the image at the size that is given.

![grafik](https://github.com/user-attachments/assets/e8c54af5-9675-46db-bb76-f2405a7f09b5)

The internal representation of the image to be burned looks like this (192x192 pixel):

![step1_transformed_682,66_682,66](https://github.com/user-attachments/assets/ad2c263b-ca22-4699-bc0d-88a88e8812bb)

This internal resolution is kept, so if we scale the image to roughly half the size, then the internal image that will eventually to be burnt looks like this (96x96 pixel)

![grafik](https://github.com/user-attachments/assets/d17d8c48-728d-40dc-b27b-ca7fcd04f408)
![step1_transformed_682,66_682,66](https://github.com/user-attachments/assets/6b286620-3d87-4e11-934b-081ff0b645db)

- This credo of "size matters" is also used when we change the dpi value of the picture in the picture property dialog: we keep the size but do change the internal resolution of the associated image, so the above picture with a dpi of 500 will have an internal representation of 1001x1001 pixel.
(Starting with mk 0.95 you can disable the everactive "Keep size" checkbox and then the internal representation will remain at the original value but the overall image size will change (so a 100 dpi image of 100x100 pixels will still be 100x100 pixels internally but just 1 third of the size if we change the dpi to 300).

So what does this mean? Well, if you have a picture that should end up smaller as the "original" picture size (derived from the original image dpi value), then choose a higher resolution than the one the picture claims it had:

![grafik](https://github.com/user-attachments/assets/1ddea717-965b-40e8-b1cb-050b79fc5239)

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\imageproperty.py`

## Category

**GUI**

## Description

The Image Property Panel is the central control interface for image processing in MeerK40t. It provides advanced tools for preparing raster images for laser engraving, including resolution control, color manipulation, dithering algorithms, and special processing modes like depth mapping.

This panel appears when an image element is selected and offers controls for:

- **Resolution Management**: DPI settings and size preservation options
- **Color Processing**: Grayscale conversion with individual color channel control
- **Dithering**: Multiple algorithms for converting grayscale to black-and-white patterns
- **Depth Mapping**: Treating images as 3D depth maps for multi-pass engraving
- **Cropping Control**: Options for automatic cropping behavior
- **Image Enhancement**: Contrast, brightness, and inversion controls

Users would access this panel when they need to optimize raster images for laser engraving, adjust image properties for better engraving results, or apply special processing techniques like dithering or depth mapping.

## How to Use

### Available Controls

- **DPI**: Text field for setting image resolution (dots per inch)
- **Keep size on change**: Checkbox to maintain image dimensions when changing DPI
- **No final crop**: Checkbox to prevent automatic cropping after processing
- **Dither**: Checkbox to enable dithering with algorithm selection dropdown
- **3D-Treatment**: Checkbox for depth map processing with resolution selection
- **Grayscale Controls**: Sliders and values for Red, Green, Blue, and Lightness components
- **Invert**: Checkbox to invert grayscale values
- **Reset**: Button to restore default grayscale settings

### Key Features

- **Resolution Control**: Precise DPI management with size preservation options
- **Advanced Dithering**: Multiple algorithms (Floyd-Steinberg, Atkinson, Jarvis, etc.)
- **Depth Mapping**: Convert grayscale to engraving depth with configurable resolution
- **Color Channel Control**: Individual adjustment of RGB components and lightness
- **Real-time Preview**: Changes apply immediately to the image display
- **Integration**: Works with crop panels, position controls, and other image tools

### Basic Usage

1. **Select Image Element**: Choose an image in the tree view to access the property panel
2. **Adjust Resolution**: Set appropriate DPI value for your laser device and material
3. **Configure Processing**: Enable dithering or depth mapping as needed for your engraving style
4. **Fine-tune Colors**: Adjust grayscale components for optimal contrast and engraving results
5. **Apply Special Effects**: Use inversion or other modifications for creative effects
6. **Preview Results**: Check the image preview to ensure desired engraving appearance

### Advanced Techniques

- **DPI Optimization**: Higher DPI for fine detail, lower DPI for faster engraving
- **Dithering Selection**: Choose algorithms based on pattern preference (Floyd-Steinberg for quality, Atkinson for speed)
- **Depth Mapping**: Use for 3D-like effects where grayscale intensity controls engraving depth
- **Color Separation**: Adjust individual RGB channels for specialized engraving requirements
- **Size Preservation**: Control whether resolution changes affect physical image dimensions

## Technical Details

The Image Property Panel manages image processing through several key mechanisms:

- **DPI Management**: Controls image scaling and internal resolution representation
- **Grayscale Processing**: Applies color transformations using PIL (Python Imaging Library)
- **Dithering Algorithms**: Implements various error-diffusion algorithms for black-and-white conversion
- **Depth Mapping**: Converts grayscale values to engraving pass counts for 3D-like effects
- **Real-time Updates**: Signals the element system to refresh image processing and display

The panel integrates with multiple sub-panels including:
- **IdPanel**: Element identification controls
- **CropPanel**: Image cropping functionality
- **PositionSizePanel**: Dimension and positioning controls
- **KeyholePanel**: Special engraving pattern controls

**Dithering Algorithms Available:**
- Floyd-Steinberg (default, high quality)
- Legacy-Floyd-Steinberg
- Atkinson
- Jarvis-Judice-Ninke
- Stucki, Burkes, Sierra variants
- Bayer matrix dithering

**Depth Mapping Resolutions:**
- 256 levels (full grayscale resolution)
- 128, 64, 32, 16, 8, 4 levels (coarser quantization)

The panel uses wxPython sliders and text controls with validation to ensure proper value ranges and provides immediate visual feedback through the MeerK40t display system.

## Related Topics

*Link to related help topics:*

- [[Online Help: Imagesplit]] - Image splitting and tiling operations
- [[Online Help: Crop]] - Image cropping functionality
- [[Online Help: Dither]] - Dithering algorithm details
- [[Online Help: Raster]] - Raster engraving operations

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the imageproperty feature.*
