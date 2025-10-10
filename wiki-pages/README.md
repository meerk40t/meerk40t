# MeerK40t Help Wiki Generation

This directory contains automatically generated template pages for the MeerK40t online help system.

## What This Contains

- **61 help page templates** - One for each unique help section found in the MeerK40t codebase
- **OnlineHelp.md** - An index page that organizes help topics by category
- **generate_help_wiki.py** - The script that generated these pages

## How MeerK40t Help Works

MeerK40t uses a context-sensitive help system where UI elements can have help text assigned via `SetHelpText("sectionname")`. When users press F1 or click help buttons, the application constructs URLs like:

```
https://github.com/meerk40t/meerk40t/wiki/Online-Help:-sectionname
```

## Updating Help Pages with Minimal Effort

### Option 1: Bulk Upload to GitHub Wiki (Recommended)

1. **Clone the wiki repository:**
   ```bash
   git clone https://github.com/meerk40t/meerk40t.wiki.git
   cd meerk40t.wiki
   ```

2. **Copy the generated pages:**
   ```bash
   cp ../wiki-pages/*.md .
   ```

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "Add comprehensive help pages for all MeerK40t features"
   git push
   ```

### Option 2: Manual Creation via GitHub Web Interface

1. Go to https://github.com/meerk40t/meerk40t/wiki
2. Click "New Page" for each template
3. Copy/paste the content from the corresponding `.md` file
4. Name each page exactly as shown (e.g., "Online-Help:-devices")

### Option 3: Use the Wiki API (Advanced)

For automated updates, you could use GitHub's API to create/update wiki pages programmatically.

## Help Page Categories

The generated pages are organized into these categories:

- **GRBL** - GRBL device configuration and operation
- **Lihuiyu/K40** - Lihuiyu/K40 laser cutter features
- **Moshi** - Moshi device support
- **Newly** - Newly device support
- **Tools** - Various tools and utilities
- **GUI** - General user interface features

## Customizing the Templates

Each generated page contains:

- **Automatic metadata** - File locations, categories
- **Standard structure** - Overview, usage, troubleshooting
- **Placeholder content** - Marked with asterisks for easy identification

To customize:

1. Edit the template content in the `.md` files
2. Replace placeholder text (marked with `*asterisks*`)
3. Add screenshots, diagrams, or additional sections as needed
4. Update the "Related Topics" section with actual cross-references

## Regenerating Pages

If new help sections are added to the codebase:

1. Run the generator script again:
   ```bash
   python generate_help_wiki.py
   ```

2. The script will:
   - Find any new help sections
   - Update existing templates if needed
   - Preserve manual edits to content

## Maintenance Tips

- **Keep templates updated** - Regenerate periodically to catch new features
- **Use consistent formatting** - Follow the established template structure
- **Cross-reference liberally** - Link related topics for better navigation
- **Include screenshots** - Visual aids greatly improve usability
- **Test links** - Ensure all wiki links work correctly

## Technical Details

- **Source extraction**: Uses regex to find `SetHelpText()` calls in Python files
- **Category inference**: Automatically categorizes based on file paths
- **Template generation**: Creates standardized markdown with placeholders
- **Index generation**: Builds categorized index for easy navigation

This system allows maintaining comprehensive help documentation with minimal ongoing effort while ensuring all features have corresponding help pages.</content>
<parameter name="filePath">c:\_development\meerk40t\wiki-pages\README.md
