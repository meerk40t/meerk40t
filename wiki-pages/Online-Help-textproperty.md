# Online Help: Textproperty

## Overview

This help page covers the **Textproperty** functionality in MeerK40t.

TextPropertyPanel - User interface panel for laser cutting operations
Technical Purpose:
Provides user interface controls for textproperty functionality. Features checkbox controls for user interaction. Integrates with refresh_scene for enhanced functionality.
End-User Perspective:
This panel provides controls for textproperty functionality. Key controls include "Translate Variables" (checkbox).

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\propertypanels\textproperty.py`

## Category

**GUI**

## Description

The Textproperty panel provides comprehensive text editing and formatting capabilities for text elements in MeerK40t designs. This feature allows users to modify text content, font properties, colors, positioning, and formatting while providing real-time preview of changes.

Users would use this feature when:
- **Creating and editing text elements**: Adding text to designs with full formatting control
- **Customizing text appearance**: Changing fonts, sizes, colors, and text effects
- **Positioning text precisely**: Adjusting text alignment, anchor points, and positioning
- **Using dynamic text**: Incorporating variables that can be substituted with dynamic content
- **Maintaining text consistency**: Using font history and saved formatting preferences

The panel integrates seamlessly with MeerK40t's element system, providing immediate visual feedback and maintaining text properties across the design workflow.

## How to Use

### Available Controls

#### Text Content
- **Text Input Field**: Main text editing area for entering and modifying text content
- **Translate Variables Checkbox**: Enables/disables variable substitution in text preview

#### Font Controls
- **Font Selection Dropdown**: Choose from system fonts with auto-complete
- **Font Size Buttons**: "A" (larger) and "a" (smaller) buttons for adjusting font size
- **Font Style Buttons**: Bold (B), Italic (I), Underline (U), and Strikethrough (S) toggles
- **Font Chooser Button**: Opens system font dialog for advanced font selection

#### Text Formatting
- **Alignment Radio Box**: Left, Center, Right text alignment options
- **Color Panels**: Separate stroke and fill color controls for text elements

#### Advanced Features
- **Text Variables Panel**: List of available variables for dynamic text insertion
- **Font History Panel**: Quick access to recently used font settings
- **Position/Size Panel**: Precise positioning and scaling controls
- **ID and Lock Panels**: Element identification and change prevention controls

### Key Features

- **Real-time Preview**: Live text rendering with formatting changes
- **Variable Substitution**: Dynamic text replacement using predefined variables
- **Font History**: Quick access to recently used font configurations
- **System Integration**: Full access to system fonts and font properties
- **Color Management**: Independent stroke and fill color controls
- **Precise Positioning**: Anchor point and alignment controls

### Basic Usage

1. **Select Text Element**: Choose a text element in the design to edit its properties
2. **Edit Text Content**: Type or modify text in the main input field
3. **Choose Font**: Select font family from the dropdown or use font chooser button
4. **Adjust Size and Style**: Use size buttons and style toggles to format text appearance
5. **Set Colors**: Configure stroke and fill colors using the color panels
6. **Position Text**: Adjust alignment and positioning using the anchor controls
7. **Add Variables**: Double-click variables from the list to insert dynamic content
8. **Preview Changes**: View real-time updates in the design scene

## Technical Details

The Textproperty panel implements comprehensive text element management through several integrated systems:

**Font Management:**
- wxPython font objects converted to SVG-compatible font specifications
- Font history persistence using context settings (fonthistory_0 through fonthistory_3)
- System font enumeration with auto-complete functionality
- Fractional point sizes for precise font scaling

**Text Rendering:**
- Real-time text measurement and bounds calculation
- SVG text element generation with proper font attributes
- Anchor point management (start, middle, end) for text alignment
- Variable substitution using wordlist translation system

**Color and Styling:**
- Independent stroke and fill color management
- Color swizzling for cross-platform compatibility
- Font weight, style, underline, and strikethrough attributes
- CSS-compatible text decoration properties

**Variable System:**
- Integration with wordlist system for dynamic text content
- Double-click insertion of variable placeholders ({variable_name})
- Real-time preview translation with increment control
- Context-aware variable resolution

**UI Architecture:**
- Multi-tab interface (Colors, Text-Variables, Font-History, Position)
- Scrolled panel for compact layout with extensive controls
- Signal integration for scene refresh and property updates
- Platform-specific optimizations (Linux text selection handling)

**Data Persistence:**
- Font settings stored in context configuration
- Text content and formatting saved with element properties
- History management for frequently used fonts
- Settings integration with MeerK40t's configuration system

## Related Topics

- [[Online Help: Vectortext]] - Creating vector text elements
- [[Online Help: Wordlist]] - Managing text variables and dynamic content
- [[Online Help: Position]] - Element positioning and transformation
- [[Online Help: Colors]] - Color selection and management
- [[Online Help: Fonts]] - Font selection and management
- [[Online Help: Tree]] - Working with elements in the design tree

## Screenshots

The Textproperty panel interface includes multiple organized sections:

1. **Main Text Area**: Large text input field with live preview display showing formatted text
2. **Font Controls**: Font selection dropdown, size adjustment buttons, and style toggles (Bold, Italic, Underline, Strikethrough)
3. **Alignment and Options**: Radio buttons for text alignment and variable translation checkbox
4. **Colors Tab**: Separate stroke and fill color selection panels
5. **Text-Variables Tab**: List box showing available variables for double-click insertion
6. **Font-History Tab**: Grid of recently used font configurations with visual previews
7. **Position Tab**: Precise positioning, sizing, and transformation controls

The interface provides comprehensive text editing capabilities with immediate visual feedback, making it easy to create and modify text elements with professional typography controls.

---

*This help page is automatically generated. Please update with specific information about the textproperty feature.*
