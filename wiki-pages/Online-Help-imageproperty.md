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

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

### Available Controls

- **Enable** (Checkbox)
- **Reset** (Button)
- **Invert** (Checkbox)
- **Original picture** (Checkbox)
- **Ignore inner** (Checkbox)
- **Automatic update** (Checkbox)
- **Update** (Button)
- **Generate contours** (Button)

### Key Features

- Integrates with: `nodetype`
- Integrates with: `element_property_force`
- Integrates with: `element_property_update`

### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

## Technical Details

Provides user interface controls for imageproperty functionality. Features checkbox, button controls for user interaction. Integrates with nodetype, element_property_force for enhanced functionality.

*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Alignment]]
- [[Online Help: Distribute]]
- [[Online Help: Arrangement]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the imageproperty feature.*
