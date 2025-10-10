# Online Help: Wordlist

## Overview

This help page covers the **Wordlist** functionality in MeerK40t.

The Wordlist system provides a powerful dynamic text templating and variable management system for laser cutting designs. It enables users to create reusable text templates with variables that can be substituted with different values, imported from CSV files, or automatically incremented. This is particularly useful for batch processing, serial numbering, personalized items, and any scenario requiring variable text content.

- Element ID management and identification
- Auto-hide controls for visibility management
- Stroke color selection with classification callbacks
- Wobble radius control for distortion amplitude
- Wobble interval setting for pattern spacing along path
- Wobble speed control for rotation rate around path
- Fill style selection from available wobble pattern plugins
- Auto-classification toggle for color changes

## Location in MeerK40t

This help section is accessed from:
- `meerk40t\gui\wordlisteditor.py`
- `meerk40t\core\wordlist.py`
- `meerk40t\core\elements\wordlist.py`

## Category

**Text & Variables**

## Description

The Wordlist system is a comprehensive text templating engine that allows you to create dynamic text elements with variables that can be substituted at runtime. It supports three types of variables:

**Variable Types:**
- **Static Text**: Simple text variables that can have multiple values cycled through
- **CSV Data**: Variables populated from CSV files with automatic header detection
- **Counters**: Auto-incrementing numeric values for serial numbering

**Key Features:**
- **Template Syntax**: Use `{variable}` patterns in text elements for substitution
- **Index Management**: Control which value from a variable list is currently active
- **CSV Import**: Automatically import data from CSV files with header detection
- **Batch Processing**: Advance through variable combinations for batch jobs
- **Date/Time Variables**: Built-in date and time formatting with custom patterns
- **Offset Support**: Use `{variable#+1}` or `{variable#-1}` for relative offsets
- **Transaction Support**: Atomic operations with rollback capability
- **Persistent Storage**: Save and load wordlist configurations

**Common Use Cases:**
- Serial numbering products with `{counter}`
- Personalizing items with names from CSV: `{name}`
- Batch processing with date stamps: `{date@%Y-%m-%d}`
- Creating numbered tickets or labels
- Managing product variants with different text elements
- Automated document generation with variable content

## How to Use

### Basic Usage

1. **Open Wordlist Editor**: Click the "Edit" button in the Wordlist Mini Panel or use the menu: Tools → Wordlist Editor
2. **Add Variables**: Use the "Add Text" or "Add Counter" buttons to create new variables
3. **Set Values**: For text variables, add multiple values that can be cycled through
4. **Use in Text Elements**: In any text element, use `{variable_name}` syntax for substitution
5. **Control Navigation**: Use Next/Prev buttons to cycle through variable combinations
6. **Batch Processing**: Use the Advance function to move through all combinations systematically

### Advanced Configuration

**Template Syntax:**
- `{name}` - Basic variable substitution using current index
- `{name#+1}` - Next value in the variable list
- `{name#-2}` - Two positions back in the variable list
- `{counter}` - Auto-incrementing counter value
- `{date@%Y-%m-%d}` - Current date with custom formatting
- `{time@%H:%M}` - Current time with custom formatting

**Variable Management:**
- **Static Variables**: Store multiple text values that can be cycled through
- **CSV Variables**: Import entire columns from CSV files automatically
- **Counter Variables**: Numeric values that increment with each use
- **System Variables**: Built-in variables like `version`, `date`, `time`, operation parameters

**Index Control:**
- Each variable maintains its own current index position
- Use "Next"/"Prev" buttons to advance through combinations
- Right-click buttons for page-based advancement (moves all variables at once)
- Set specific indices using the dropdown controls

### Tips and Best Practices

- Start with simple variable names without special characters
- Use CSV import for large datasets of names, addresses, or product codes
- Combine counters with dates for unique serial numbers: `SN-{date@%Y%m%d}-{counter}`
- Test your templates with the Preview function before cutting
- Use relative offsets `{variable#+1}` to show "next" values in designs
- Save frequently used wordlist configurations for reuse
- Use the autosave feature to prevent data loss

## Technical Details

The Wordlist system uses a sophisticated data structure where each variable is stored as a list with specific indices:

**Data Structure:**
```
content["variable_name"] = [type, current_index, value1, value2, value3, ...]
```

- **Index 0**: Variable type (0=static, 1=CSV, 2=counter)
- **Index 1**: Current position index for iteration
- **Index 2+**: Actual data values

**Template Processing:**
Text elements containing `{variable}` patterns are processed through the `translate()` method, which:
1. Finds all bracketed patterns using regex `\{[^}]+\}`
2. Parses variable names and offset modifiers
3. Substitutes patterns with current values from the wordlist
4. Handles special date/time formatting with strftime patterns

**CSV Import Process:**
1. Automatic encoding detection for various file formats
2. Header detection using CSV sniffer
3. Column-based variable creation
4. Data validation and error handling

**Performance Considerations:**
- Variables are processed once per text element during rendering
- Large CSV datasets are loaded entirely into memory
- Regex pattern matching is optimized for common use cases
- Transaction system prevents data corruption during batch operations

**Integration Points:**
- **Text Elements**: Primary integration through text content substitution
- **Console Commands**: Full command-line interface for automation
- **Batch Processing**: Integration with job spooling for automated production
- **File Operations**: Persistent storage in JSON format

## Related Topics

*Link to related help topics:*

- [[Online Help: Text Property]] - Text element creation and editing
- [[Online Help: Vector Text]] - Advanced text manipulation
- [[Online Help: Templates]] - Design template management
- [[Online Help: Operation Property]] - Operation configuration
- [[Online Help: Console]] - Command-line interface for automation

## Screenshots

### Wordlist Editor Main Interface
The Wordlist Editor window displaying variable management controls:
- **Variable List**: Table showing all defined variables with their types and current values
- **Add Buttons**: "Add Text" and "Add Counter" buttons for creating new variables
- **Navigation Controls**: Next/Prev buttons for cycling through variable combinations
- **Index Dropdowns**: Individual index selectors for each variable

### Variable Configuration Panel
The variable editing section showing detailed configuration:
- **Variable Name Field**: Input for naming the variable
- **Type Selection**: Dropdown for Static Text, CSV Data, or Counter types
- **Value List**: Multi-line text area for entering variable values
- **Current Index Display**: Shows which value is currently active

### CSV Import Interface
The CSV import dialog for bulk data loading:
- **File Selection**: Browse button for selecting CSV files
- **Encoding Options**: Character encoding selection for different file formats
- **Header Detection**: Automatic column header identification
- **Variable Creation**: Preview of variables that will be created from CSV columns

### Text Template Example
Demonstration of text elements using wordlist variables:
- **Template Text**: "Serial: {counter} - Name: {name} - Date: {date@%Y-%m-%d}"
- **Variable Substitution**: Shows how {variable} patterns are replaced with actual values
- **Dynamic Updates**: Text changes as variables are cycled through different values
- **Formatting Options**: Date/time formatting with custom patterns

### Counter Variable Configuration
The counter variable setup showing auto-increment functionality:
- **Counter Type**: Selected variable type for numeric sequencing
- **Start Value**: Initial number for the counter sequence
- **Increment Step**: How much to add with each advancement
- **Current Value Display**: Shows the present counter value

### Batch Processing Controls
The batch processing interface for systematic variable advancement:
- **Advance Button**: Moves all variables to their next combination
- **Transaction Support**: Atomic operations with rollback capability
- **Progress Tracking**: Shows current position in the variable matrix
- **Completion Status**: Indicates when all combinations have been processed

### Complex Template with Offsets
Example showing advanced templating with relative offsets:
- **Offset Syntax**: Using {variable#+1} and {variable#-1} for relative values
- **Preview Display**: Shows current, next, and previous values simultaneously
- **Multi-variable Integration**: Combining counters, text variables, and dates
- **Layout Examples**: How offsets create sequential numbering or preview systems

### Wordlist Mini Panel
The compact mini panel for quick wordlist access:
- **Edit Button**: Opens the full Wordlist Editor
- **Quick Navigation**: Simplified Next/Prev controls
- **Current Values**: Display of active variable values
- **Status Indicators**: Shows wordlist state and variable counts

---

*This help page provides comprehensive documentation for the wordlist text templating system in MeerK40t.*
