# Online Help: Vectortext

## Overview

This help page covers the **Vectortext** functionality in MeerK40t.

The Vector Text system provides comprehensive font management and text creation capabilities using vector-based fonts. MeerK40t supports multiple font formats designed for laser cutting, including Hershey fonts, TrueType fonts, and AutoCAD SHX fonts, all rendered as scalable vector paths.

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\hersheymanager.py`
- `meerk40t\gui\toolwidgets\toollinetext.py`

## Category

**GUI**

## Description

Vector text in MeerK40t refers to text created using fonts that are rendered as vector paths rather than bitmap images. This approach offers several advantages for laser cutting:

- **Infinite Scalability**: Vector fonts can be scaled to any size without quality loss
- **Laser-Optimized**: Text becomes vector paths that can be cut, engraved, or rastered like any other shape
- **Editability**: Individual letters can be modified as vector shapes
- **Compatibility**: Works with all MeerK40t operations (cut, engrave, raster, etc.)

The system supports three main font types:
- **Hershey Fonts**: Classic vector fonts designed specifically for plotters and CNC machines
- **TrueType Fonts**: Standard TTF fonts converted to vector paths
- **AutoCAD SHX Fonts**: Technical fonts from AutoCAD, optimized for engineering drawings

Vector text is created using the Line Text tool and managed through the Font Manager interface.

## How to Use

### Accessing Vector Text Features

1. **Font Manager**: Access via Window menu → Font-Manager, or the Font-Manager button in configuration
2. **Line Text Tool**: Select the "A" (text) tool from the toolbar to create vector text
3. **Text Properties**: Use the Properties panel to modify existing vector text

### Font Manager Interface

The Font Manager provides comprehensive font management capabilities:

#### Font Directory Management
- **Font Work Directory**: Set a custom directory for user fonts and cache files
- **System Directories**: Configure system font search paths
- **Directory Validation**: Invalid directories are highlighted and won't be used

#### Font List and Preview
- **Font List**: Shows all available fonts with family and subfamily information
- **Preview**: Displays a sample of the selected font
- **Tooltips**: Hover over fonts to see detailed information (family, subfamily, file path)

#### Font Operations
- **Import**: Add new fonts from files or web sources
- **Delete**: Remove user-installed fonts (system fonts are protected)
- **Refresh**: Reload font cache and update the font list

#### Font Sources
The manager provides quick access to font resources:
- **Hershey Fonts**: Classic vector fonts from various online repositories
- **AutoCAD SHX Fonts**: Technical fonts for engineering applications
- **Web Resources**: Direct links to font download sites

### Creating Vector Text

1. **Select Tool**: Click the text tool ("A") in the toolbar
2. **Click Position**: Click on the design area where you want the text
3. **Enter Text**: The Properties panel opens automatically for text entry
4. **Choose Font**: Select from available vector fonts
5. **Set Size**: Adjust font size (supports any scaling)
6. **Apply Operations**: Use cut, engrave, or raster operations on the text

### Available Controls

- **Font Directory Field**: Text field for custom font directory path
- **Directory Browse Button**: "..." button to select font directory
- **Font List**: List box showing all available fonts
- **Font Preview**: Bitmap display showing font sample
- **Import Button**: Add new fonts to the collection
- **Delete Button**: Remove selected user font
- **Refresh Button**: Reload font cache
- **Web Resources Dropdown**: Quick access to font download sites

### Key Features

- **Multi-Format Support**: Hershey, TrueType, and SHX font compatibility
- **Font Preview**: Visual preview of fonts before selection
- **Cache Management**: Automatic caching for performance
- **Directory Flexibility**: Custom font directories with validation
- **Web Integration**: Direct links to font resources
- **System Protection**: Prevents deletion of system fonts

### Basic Usage Workflow

1. **Set Up Fonts**: Open Font Manager and configure font directories
2. **Import Fonts**: Add desired vector fonts using the Import button
3. **Select Text Tool**: Choose the line text tool from the toolbar
4. **Place Text**: Click in the design area to create text insertion point
5. **Configure Text**: Use Properties panel to set content, font, and size
6. **Apply Operations**: Assign cut/engrave operations to the text paths

### Advanced Usage

- **Font Research**: Use web resources dropdown to find specialized fonts
- **Batch Import**: Import multiple fonts at once with progress tracking
- **Cache Management**: Use Refresh to update font previews and metadata
- **Directory Organization**: Set up dedicated directories for different font types
- **Font Validation**: Automatic checking ensures only valid fonts are listed

## Technical Details

The Vector Text system is built around a sophisticated font management architecture:

### Font Formats Supported
- **Hershey Fonts**: Single-stroke vector fonts designed for plotters
- **TrueType Fonts**: Outline fonts converted to vector paths
- **SHX Fonts**: AutoCAD shape fonts with technical symbols

### Font Storage and Caching
- **Directory Structure**: Fonts stored in user-configurable directories
- **Cache System**: Preview bitmaps cached for performance
- **Metadata Tracking**: Font family, subfamily, and file information maintained
- **System Integration**: Automatic discovery of system font directories

### Text Creation Process
1. **Tool Selection**: Line Text tool captures click position
2. **Command Generation**: Creates `linetext` console command with coordinates
3. **Element Creation**: Generates vector paths for each character
4. **Property Integration**: Opens Properties panel for text configuration

### Performance Optimizations
- **Lazy Loading**: Fonts loaded only when needed
- **Preview Caching**: Bitmap previews cached to disk
- **Directory Watching**: Automatic font discovery in configured directories
- **Memory Management**: Efficient handling of large font collections

## Troubleshooting

### Common Issues

- **Fonts not appearing**: Check font directory validity and refresh the list
- **Import failures**: Ensure font files are valid and accessible
- **Preview issues**: Use Refresh to regenerate font previews
- **Text not rendering**: Verify font selection and text content

### Font Directory Issues
- **Invalid Directory**: Highlighted in red, won't be used for font storage
- **Permission Problems**: Ensure write access to custom font directories
- **Path Length Limits**: Very long paths may cause issues on some systems

### Performance Considerations
- **Large Collections**: Many fonts may slow initial loading
- **Cache Files**: Font previews stored in font directory
- **Memory Usage**: Font data loaded on-demand to minimize memory footprint

## Related Topics

*Link to related help topics:*

- [[Online Help: Textproperty]] - Text formatting and editing options
- [[Online Help: Properties]] - Element property configuration
- [[Online Help: Tools]] - Available drawing and creation tools
- [[Online Help: Console]] - Command-line text creation options

## Screenshots

The Vector Text system includes several key interfaces:

1. **Font Manager Window**: Main interface showing font list, preview, and controls
2. **Font Directory Setup**: Directory configuration with validation feedback
3. **Font Import Dialog**: File selection for adding new fonts
4. **Text Creation Tool**: Line text tool in the toolbar
5. **Text Properties Panel**: Configuration options for created text
6. **Font Preview Display**: Sample text showing font appearance

The Font Manager window is resizable and remembers its position. Font previews update automatically when fonts are selected, and the interface provides comprehensive tooltips for all controls.

---

*This help page provides comprehensive documentation for MeerK40t's vector text and font management system.*
