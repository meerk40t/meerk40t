#!/usr/bin/env python3
"""
MeerK40t Help Wiki Generator

This script extracts all help sections from the MeerK40t codebase and generates
template wiki pages for the GitHub wiki help system.

Usage:
    python generate_help_wiki.py [--upload]

Options:
    --upload    Automatically upload generated pages to GitHub wiki repository

This will create markdown files in a 'wiki-pages' directory that can be uploaded
to the GitHub wiki repository.
"""

import argparse
import ast
import os
import re
import subprocess
from collections import defaultdict


def check_existing_wiki_page(section):
    """Check if an existing wiki page exists and return its content."""
    wiki_filename = f"Online-Help:-{section.upper()}.md"
    wiki_repo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "meerk40t.wiki"
    )

    # Check if wiki repo exists
    if not os.path.exists(wiki_repo_path):
        print(
            f"Warning: Wiki repository not found at {wiki_repo_path}. Skipping existing content check."
        )
        return None

    try:
        # Use git to get the content of the existing wiki page
        result = subprocess.run(
            ["git", "show", f"HEAD:{wiki_filename}"],
            cwd=wiki_repo_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def extract_existing_content(existing_content):
    """Extract the main content from an existing wiki page, excluding the title."""
    if not existing_content:
        return ""

    lines = existing_content.split("\n")

    # Skip the title line (first line starting with #)
    content_lines = []
    skip_title = True

    for line in lines:
        if skip_title and line.strip().startswith("#"):
            skip_title = False
            continue
        if not skip_title:
            content_lines.append(line)

    # Remove leading/trailing empty lines
    while content_lines and not content_lines[0].strip():
        content_lines.pop(0)
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()

    return "\n".join(content_lines)


def extract_help_sections():
    """Extract all unique help sections from Python files."""
    help_sections = set()
    help_context = defaultdict(list)  # section -> list of files using it

    # Walk through all Python files
    for root, dirs, files in os.walk("."):
        # Skip certain directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["__pycache__", "build", "dist"]
        ]

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Find all SetHelpText calls
                        matches = re.findall(
                            r'SetHelpText\(\s*["\']([^"\']+)["\']', content
                        )
                        for match in matches:
                            help_sections.add(match)
                            help_context[match].append(filepath)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

    return help_sections, help_context


def analyze_module_for_help_section(filepath, help_section):
    """Analyze a module to extract relevant information for a help section."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Could not read file: {e}"}

    analysis = {
        "filepath": filepath,
        "class_info": [],
        "methods": [],
        "ui_elements": [],
        "docstrings": [],
        "comments": [],
        "functionality": [],
    }

    # Parse the AST to extract class and method information
    try:
        tree = ast.parse(content, filepath)

        # First, find the class that contains the SetHelpText call for this section
        target_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class contains the SetHelpText call
                class_end = (
                    node.end_lineno
                    if hasattr(node, "end_lineno")
                    else len(content.split("\n"))
                )
                class_content = content.split("\n")[node.lineno - 1 : class_end]
                class_text = "\n".join(class_content)
                if (
                    f'SetHelpText("{help_section}")' in class_text
                    or f"SetHelpText('{help_section}')" in class_text
                ):
                    target_class = node
                    break

        if target_class:
            # Extract information for the specific target class
            class_info = {
                "name": target_class.name,
                "docstring": ast.get_docstring(target_class),
                "methods": [],
            }

            # Extract method information
            for item in target_class.body:
                if isinstance(item, ast.FunctionDef):
                    method_info = {
                        "name": item.name,
                        "docstring": ast.get_docstring(item),
                        "args": [arg.arg for arg in item.args.args],
                    }
                    class_info["methods"].append(method_info)

            analysis["class_info"].append(class_info)
        else:
            # Fallback: extract from all classes if no specific match
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "docstring": ast.get_docstring(node),
                        "methods": [],
                    }

                    # Extract method information
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                "name": item.name,
                                "docstring": ast.get_docstring(item),
                                "args": [arg.arg for arg in item.args.args],
                            }
                            class_info["methods"].append(method_info)

                    analysis["class_info"].append(class_info)

    except SyntaxError:
        analysis["error"] = "Could not parse Python AST"

    # Extract UI elements and functionality hints
    lines = content.split("\n")

    # Look for wxPython UI elements with more flexible pattern matching
    # This handles both standard wxPython widgets and custom meerk40t wxutils widgets
    ui_patterns = [
        # Standard wxPython widgets
        (r'wx\.Button\([^)]*?_\("([^"]+)"\)[^)]*\)', "Button"),
        (r'wx\.CheckBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Checkbox"),
        (r'wx\.RadioButton\([^)]*?_\("([^"]+)"\)[^)]*\)', "Radio Button"),
        (r'wx\.StaticText\([^)]*?_\("([^"]+)"\)[^)]*\)', "Label"),
        (r'wx\.ComboBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Combo Box"),
        (r'wx\.Slider\([^)]*?_\("([^"]+)"\)[^)]*\)', "Slider"),
        (r'wx\.SpinCtrl\([^)]*?_\("([^"]+)"\)[^)]*\)', "Spin Control"),
        (r'wx\.TextCtrl\([^)]*?_\("([^"]+)"\)[^)]*\)', "Text Control"),
        (r'wx\.RadioBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Radio Box"),
        # Custom meerk40t wxutils widgets
        (r'wxButton\([^)]*?_\("([^"]+)"\)[^)]*\)', "Button"),
        (r'wxCheckBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Checkbox"),
        (r'wxRadioButton\([^)]*?_\("([^"]+)"\)[^)]*\)', "Radio Button"),
        (r'wxStaticText\([^)]*?_\("([^"]+)"\)[^)]*\)', "Label"),
        (r'wxComboBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Combo Box"),
        (r'wxSlider\([^)]*?_\("([^"]+)"\)[^)]*\)', "Slider"),
        (r'wxSpinCtrl\([^)]*?_\("([^"]+)"\)[^)]*\)', "Spin Control"),
        (r'TextCtrl\([^)]*?_\("([^"]+)"\)[^)]*\)', "Text Control"),
        (r'wxRadioBox\([^)]*?_\("([^"]+)"\)[^)]*\)', "Radio Box"),
        # Handle keyword arguments like label=_("string")
        (r'wx\.Button\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Button"),
        (r'wx\.CheckBox\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Checkbox"),
        (r'wx\.RadioButton\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Radio Button"),
        (r'wx\.StaticText\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Label"),
        (r'wx\.ComboBox\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Combo Box"),
        # Custom widgets with keyword arguments
        (r'wxButton\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Button"),
        (r'wxCheckBox\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Checkbox"),
        (r'wxRadioButton\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Radio Button"),
        (r'wxStaticText\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Label"),
        (r'wxComboBox\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Combo Box"),
        (r'TextCtrl\([^)]*?label\s*=\s*_\("([^"]+)"\)[^)]*\)', "Text Control"),
    ]

    for line in lines:
        for pattern, element_type in ui_patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                analysis["ui_elements"].append(
                    {"type": element_type, "label": match.strip()}
                )

    # Look for comments that might indicate functionality
    for line in lines:
        line = line.strip()
        if line.startswith("#") and len(line) > 1:
            comment = line[1:].strip()
            if (
                len(comment) > 10
                and not comment.startswith("TODO")
                and not comment.startswith("FIXME")
            ):
                analysis["comments"].append(comment)

    # Look for signal listeners and other functionality indicators
    signal_patterns = [
        r'@signal_listener\("([^"]+)"\)',
        r'@lookup_listener\("([^"]+)"\)',
        r'context\.signal\("([^"]+)"',
        r'kernel\.register\("([^"]+)"',
    ]

    for pattern in signal_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            analysis["functionality"].append(match)

    # Extract tooltips and help text
    tooltip_patterns = [
        r'SetToolTip\(_\("([^"]+)"\)\)',
        r'SetHelpText\(_\("([^"]+)"\)\)',
    ]

    for pattern in tooltip_patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            analysis["docstrings"].append(match)

    return analysis


def generate_wiki_page(section, files):
    """Generate a wiki page template for a help section with enhanced analysis."""

    # Check for existing wiki content
    existing_content = check_existing_wiki_page(section)
    existing_description = (
        extract_existing_content(existing_content) if existing_content else ""
    )

    # Create a more readable title
    title = section.replace("_", " ").title()

    # Try to infer the category from the file paths
    categories = []
    for file_path in files:
        if "grbl" in file_path.lower():
            categories.append("GRBL")
        elif "lihuiyu" in file_path.lower() or "k40" in file_path.lower():
            categories.append("Lihuiyu/K40")
        elif "moshi" in file_path.lower():
            categories.append("Moshi")
        elif "newly" in file_path.lower():
            categories.append("Newly")
        elif "tools" in file_path.lower():
            categories.append("Tools")
        elif "gui" in file_path.lower():
            categories.append("GUI")

    category = list(set(categories))[0] if categories else "General"

    # Build file list
    file_list = "\n".join([f"- `{os.path.relpath(f, '.')}`" for f in files])

    # Analyze the modules for more detailed information
    module_analyses = []
    for filepath in files:
        analysis = analyze_module_for_help_section(filepath, section)
        module_analyses.append(analysis)

    # Extract useful information from analyses
    class_descriptions = []
    ui_elements = []
    functionality_hints = []
    relevant_comments = []

    for analysis in module_analyses:
        # Get class docstrings
        for class_info in analysis.get("class_info", []):
            if class_info.get("docstring"):
                class_descriptions.append(class_info["docstring"])

        # Get UI elements
        ui_elements.extend(analysis.get("ui_elements", []))

        # Get functionality hints
        functionality_hints.extend(analysis.get("functionality", []))

        # Get relevant comments
        relevant_comments.extend(
            analysis.get("comments", [])[:3]
        )  # Limit to first 3 comments

    # Generate description based on extracted information
    description = f"This help page covers the **{title}** functionality in MeerK40t."

    if class_descriptions:
        description += "\n\n" + class_descriptions[0]  # Use the first class docstring

    # If we have existing content, add it to the description
    if existing_description:
        description += "\n\n" + existing_description

    # Generate usage information based on UI elements
    usage_info = ""
    if ui_elements:
        usage_info += "### Available Controls\n\n"
        for element in ui_elements[:5]:  # Limit to first 5 elements
            usage_info += f"- **{element['label']}** ({element['type']})\n"
        usage_info += "\n"

    # Add functionality hints
    if functionality_hints:
        unique_hints = list(set(functionality_hints))[:3]  # Limit to 3 unique hints
        usage_info += "### Key Features\n\n"
        for hint in unique_hints:
            usage_info += f"- Integrates with: `{hint}`\n"
        usage_info += "\n"

    template = f"""# Online Help: {title}

## Overview

{description}

## Location in MeerK40t

This help section is accessed from:
{file_list}

## Category

**{category}**

## Description

*Add a detailed description of what this feature does and when users would use it.*

## How to Use

{usage_info}### Basic Usage

1. *Step 1*
2. *Step 2*
3. *Step 3*

### Advanced Options

*Describe any advanced configuration options or settings.*

## Common Issues

*List common problems users might encounter and their solutions.*

## Related Topics

*Link to related help topics:*

- [[Online Help: Related Topic 1]]
- [[Online Help: Related Topic 2]]

## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page is automatically generated. Please update with specific information about the {section} feature.*
"""

    return template


def assess_docstring_quality(docstring, class_name, methods, ui_elements):
    """
    Assess the quality of a class docstring based on various criteria.

    Args:
        docstring (str): The current docstring to assess
        class_name (str): Name of the class
        methods (list): List of method dictionaries
        ui_elements (list): List of UI element dictionaries

    Returns:
        dict: Assessment results with quality score and recommendations
    """
    if not docstring:
        return {
            "quality": "missing",
            "score": 0,
            "recommendations": [
                "Add a comprehensive docstring describing the class purpose and functionality"
            ],
            "needs_improvement": True,
        }

    score = 0
    recommendations = []

    # Check length (minimum 50 characters for meaningful description)
    if len(docstring.strip()) < 50:
        recommendations.append(
            "Docstring is too short - expand with more detailed description"
        )
    else:
        score += 1

    # Check for class purpose description
    purpose_indicators = [
        "provides",
        "handles",
        "manages",
        "controls",
        "implements",
        "represents",
    ]
    has_purpose = any(
        indicator in docstring.lower() for indicator in purpose_indicators
    )
    if has_purpose:
        score += 1
    else:
        recommendations.append("Add description of what this class provides or handles")

    # Check for UI element coverage
    ui_labels = [elem.get("label", "").lower() for elem in ui_elements]
    ui_coverage = sum(1 for label in ui_labels if label and label in docstring.lower())
    if ui_elements and ui_coverage == 0:
        recommendations.append("Mention key UI elements and controls in the docstring")
        score -= 0.5
    elif ui_coverage > 0:
        score += 1

    # Check for method coverage (at least mention key methods)
    method_names = [method.get("name", "").lower() for method in methods]
    method_coverage = sum(
        1 for name in method_names if name and name in docstring.lower()
    )
    if methods and method_coverage == 0:
        recommendations.append(
            "Reference key methods or functionality in the docstring"
        )
    elif method_coverage > 0:
        score += 0.5

    # Check for formatting (basic structure)
    has_structure = any(
        line.strip().startswith(("-", "*", "•")) for line in docstring.split("\n")
    )
    if has_structure:
        score += 0.5

    # Determine overall quality
    if score >= 3:
        quality = "excellent"
    elif score >= 2:
        quality = "good"
    elif score >= 1:
        quality = "adequate"
    else:
        quality = "poor"

    return {
        "quality": quality,
        "score": score,
        "recommendations": recommendations,
        "needs_improvement": quality in ["poor", "missing"] or len(recommendations) > 0,
    }


def generate_docstring_for_class(
    class_name, methods, ui_elements, functionality_hints, comments
):
    """
    Generate a user-friendly docstring for a class based on its analysis.

    Args:
        class_name (str): Name of the class
        methods (list): List of method dictionaries
        ui_elements (list): List of UI element dictionaries
        functionality_hints (list): List of functionality indicators
        comments (list): List of relevant comments

    Returns:
        str: Generated user-friendly docstring
    """
    # Determine what this panel does based on class name and UI elements
    panel_description = get_panel_description(class_name, ui_elements)

    docstring = f"{panel_description}"

    return docstring.strip()


def get_panel_description(class_name, ui_elements):
    """Get a user-friendly description of what the panel does."""
    class_lower = class_name.lower()

    if "transform" in class_lower:
        return "Transform Panel - Scale, rotate, and move your design elements"
    elif "drag" in class_lower:
        return "Drag Panel - Position the laser head and align it with your design"
    elif "jog" in class_lower:
        return "Jog Panel - Manually move the laser head around the work area"
    elif "move" in class_lower:
        return "Move Panel - Send the laser to specific coordinates or saved positions"
    elif "pulse" in class_lower:
        return "Pulse Panel - Fire short test laser pulses for alignment and testing"
    elif "zmove" in class_lower or "z_move" in class_lower:
        return "Z-Move Panel - Control the up/down movement of the laser head"
    elif "align" in class_lower:
        return "Alignment Panel - Align and distribute design elements"
    elif "device" in class_lower:
        return "Device Panel - Configure and control your laser device settings"
    elif "material" in class_lower:
        return "Material Panel - Set up material settings for better cutting results"
    elif "simulation" in class_lower:
        return "Simulation Panel - Preview your laser job before running it"
    elif "navigation" in class_lower:
        return "Navigation Panel - Control laser movement and positioning"
    else:
        return f"{class_name} - User interface panel for laser cutting operations"


def update_class_docstring(filepath, class_name, new_docstring):
    """
    Update the docstring of a specific class in a Python file.

    Args:
        filepath (str): Path to the Python file
        class_name (str): Name of the class to update
        new_docstring (str): New docstring content

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    try:
        tree = ast.parse(content, filepath)
    except SyntaxError as e:
        print(f"Error parsing {filepath}: {e}")
        return False

    # Find the target class
    target_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            target_class = node
            break

    if not target_class:
        print(f"Class {class_name} not found in {filepath}")
        return False

    # Get the current docstring if it exists
    current_docstring = ast.get_docstring(target_class)

    # Find the position to replace
    lines = content.split("\n")

    # Get the class start line (0-indexed)
    class_start = target_class.lineno - 1

    # Find where the docstring starts and ends
    docstring_start = class_start + 1
    docstring_end = docstring_start

    if current_docstring:
        # Find the end of the existing docstring
        in_docstring = False
        quote_char = None
        for i in range(class_start, len(lines)):
            line = lines[i].strip()
            if not in_docstring and (line.startswith('"""') or line.startswith("'''")):
                in_docstring = True
                quote_char = '"""' if line.startswith('"""') else "'''"
                docstring_start = i
            elif in_docstring and quote_char and line.endswith(quote_char):
                docstring_end = i + 1
                break
    else:
        # No existing docstring, insert after class definition line
        docstring_start = class_start + 1
        docstring_end = class_start + 1

    # Prepare the new docstring with proper indentation
    # Get the indentation of the class definition
    class_indent = ""
    if class_start < len(lines):
        class_line = lines[class_start]
        class_indent = class_line[: len(class_line) - len(class_line.lstrip())]

    # Format the new docstring
    indented_docstring = f'{class_indent}    """{new_docstring}"""'

    # Replace the content
    new_lines = lines[:docstring_start] + [indented_docstring] + lines[docstring_end:]

    # Write back to file
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        print(f"Updated docstring for class {class_name} in {filepath}")
        return True
    except Exception as e:
        print(f"Error writing to {filepath}: {e}")
        return False


def upload_to_wiki(wiki_dir="wiki-pages", repo_url=None, commit_message=None):
    """
    Upload generated wiki pages to GitHub wiki repository.

    Args:
        wiki_dir (str): Directory containing generated wiki pages
        repo_url (str): GitHub repository URL (optional, will try to detect)
        commit_message (str): Commit message for the wiki update

    Returns:
        bool: True if successful, False otherwise
    """
    if not os.path.exists(wiki_dir):
        print(f"Error: Wiki directory '{wiki_dir}' not found")
        return False

    # Try to detect repository URL from git config
    if not repo_url:
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=".",
            )
            if result.returncode == 0:
                repo_url = result.stdout.strip()
                # Convert to wiki URL
                if repo_url.endswith(".git"):
                    repo_url = repo_url[:-4]
                if not repo_url.endswith(".wiki.git"):
                    repo_url = repo_url + ".wiki.git"
            else:
                print("Could not detect repository URL. Please specify --repo-url")
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Git not found or not in a git repository")
            return False

    # Create wiki repository directory
    wiki_repo_dir = "meerk40t.wiki"
    wiki_repo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), wiki_repo_dir
    )

    print(f"Using wiki repository: {repo_url}")
    print(f"Wiki repository path: {wiki_repo_path}")

    # Clone or update wiki repository
    if os.path.exists(wiki_repo_path):
        print("Updating existing wiki repository...")
        try:
            # Pull latest changes
            subprocess.run(
                ["git", "pull"], cwd=wiki_repo_path, check=True, capture_output=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Error updating wiki repository: {e}")
            return False
    else:
        print("Cloning wiki repository...")
        try:
            # Clone the wiki repository
            subprocess.run(
                ["git", "clone", repo_url, wiki_repo_path],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error cloning wiki repository: {e}")
            print("Make sure the wiki repository exists and is accessible")
            return False

    # Copy generated files to wiki repository
    print("Copying generated wiki pages...")
    copied_files = 0
    for filename in os.listdir(wiki_dir):
        if filename.endswith(".md"):
            src_path = os.path.join(wiki_dir, filename)
            dst_path = os.path.join(wiki_repo_path, filename)

            try:
                with open(src_path, "r", encoding="utf-8") as src:
                    content = src.read()
                with open(dst_path, "w", encoding="utf-8") as dst:
                    dst.write(content)
                copied_files += 1
                print(f"  Copied: {filename}")
            except Exception as e:
                print(f"  Error copying {filename}: {e}")

    if copied_files == 0:
        print("No files were copied to wiki repository")
        return False

    # Commit and push changes
    try:
        # Check if there are changes to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=wiki_repo_path,
            capture_output=True,
            text=True,
        )
        if not result.stdout.strip():
            print("No changes to commit")
            return True

        # Add all changes
        subprocess.run(
            ["git", "add", "."], cwd=wiki_repo_path, check=True, capture_output=True
        )

        # Create commit message
        if not commit_message:
            commit_message = f"Update wiki pages - {copied_files} pages updated"

        # Commit changes
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=wiki_repo_path,
            check=True,
            capture_output=True,
        )

        # Push changes
        subprocess.run(
            ["git", "push"], cwd=wiki_repo_path, check=True, capture_output=True
        )

        print(f"Successfully uploaded {copied_files} wiki pages")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error committing/pushing wiki changes: {e}")
        return False


def get_repo_info():
    """
    Get repository information for wiki upload.

    Returns:
        dict: Repository information including URL and name
    """
    try:
        # Get repository URL
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        repo_url = result.stdout.strip() if result.returncode == 0 else None

        # Get repository name
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            cwd=".",
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extract repo name from URL
            if "/" in url:
                repo_name = url.split("/")[-1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]
            else:
                repo_name = "meerk40t"
        else:
            repo_name = "meerk40t"

        return {
            "url": repo_url,
            "name": repo_name,
            "wiki_url": repo_url.replace(".git", ".wiki.git") if repo_url else None,
        }
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main():
    """Main function to generate wiki pages."""
    parser = argparse.ArgumentParser(description="Generate MeerK40t help wiki pages")
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Automatically upload generated pages to GitHub wiki repository",
    )
    parser.add_argument(
        "--repo-url",
        type=str,
        help="GitHub repository URL (auto-detected if not specified)",
    )
    parser.add_argument(
        "--commit-message",
        type=str,
        help="Commit message for wiki update (auto-generated if not specified)",
    )

    args = parser.parse_args()

    print("Extracting help sections from MeerK40t codebase...")

    help_sections, help_context = extract_help_sections()

    print(f"Found {len(help_sections)} unique help sections")

    # Assess and update docstrings for classes with SetHelpText calls
    print("\nAssessing docstring quality and updating as needed...")
    updated_classes = 0

    for section, files in help_context.items():
        for filepath in files:
            analysis = analyze_module_for_help_section(filepath, section)

            for class_info in analysis.get("class_info", []):
                class_name = class_info.get("name")
                current_docstring = class_info.get("docstring")
                methods = class_info.get("methods", [])
                ui_elements = analysis.get("ui_elements", [])
                functionality_hints = analysis.get("functionality", [])
                comments = analysis.get("comments", [])

                # Assess docstring quality
                assessment = assess_docstring_quality(
                    current_docstring, class_name, methods, ui_elements
                )

                # Check if docstring contains non-helpful sections that should be removed
                needs_simplification = False
                if current_docstring:
                    sections_to_remove = [
                        "Integration Points:",
                        "Main Methods:",
                        "Usage Notes:",
                        "Controls:",
                        "How to Use:",
                        "When to Use:",
                    ]
                    for section in sections_to_remove:
                        if section in current_docstring:
                            needs_simplification = True
                            break

                if assessment["needs_improvement"] or needs_simplification:
                    print(f"Improving docstring for {class_name} in {filepath}")
                    print(
                        f"  Current quality: {assessment['quality']} (score: {assessment['score']})"
                    )

                    # Generate new docstring
                    new_docstring = generate_docstring_for_class(
                        class_name, methods, ui_elements, functionality_hints, comments
                    )

                    # Update the class docstring
                    if update_class_docstring(filepath, class_name, new_docstring):
                        updated_classes += 1
                        print(f"  ✓ Updated docstring for {class_name}")
                    else:
                        print(f"  ✗ Failed to update docstring for {class_name}")

    if updated_classes > 0:
        print(f"\nUpdated docstrings for {updated_classes} classes")

    # Create output directory
    output_dir = "wiki-pages"
    os.makedirs(output_dir, exist_ok=True)

    # Generate wiki pages
    generated_pages = []
    reused_content_count = 0

    for section in sorted(help_sections):
        filename = f"Online-Help-{section}.md"
        filepath = os.path.join(output_dir, filename)

        content = generate_wiki_page(section, help_context[section])

        # Check if we reused existing content
        existing_content = check_existing_wiki_page(section)
        if existing_content and extract_existing_content(existing_content):
            reused_content_count += 1
            print(f"Generated: {filename} (reused existing content)")
        else:
            print(f"Generated: {filename}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        generated_pages.append(filename)

    # Create an index page
    index_content = "# MeerK40t Online Help Index\n\n"
    index_content += f"This wiki contains help pages for {len(help_sections)} different features in MeerK40t.\n\n"
    index_content += "## Help Pages by Category\n\n"

    # Group by category
    categories = defaultdict(list)
    for section in help_sections:
        # Infer category from context
        category = "General"
        files = help_context[section]
        if any("grbl" in f.lower() for f in files):
            category = "GRBL"
        elif any("lihuiyu" in f.lower() or "k40" in f.lower() for f in files):
            category = "Lihuiyu/K40"
        elif any("moshi" in f.lower() for f in files):
            category = "Moshi"
        elif any("newly" in f.lower() for f in files):
            category = "Newly"
        elif any("tools" in f.lower() for f in files):
            category = "Tools"
        elif any("gui" in f.lower() for f in files):
            category = "GUI"

        categories[category].append(section)

    for category, sections in sorted(categories.items()):
        index_content += f"### {category}\n\n"
        for section in sorted(sections):
            index_content += f"- [[Online Help: {section.replace('_', ' ').title()}]]\n"
        index_content += "\n"

    index_content += "\n---\n\n"
    index_content += (
        "*This index is automatically generated. Last updated: "
        + __import__("datetime").datetime.now().strftime("%Y-%m-%d")
        + "*"
    )

    with open(os.path.join(output_dir, "Home.md"), "w", encoding="utf-8") as f:
        f.write(index_content)

    print("\nGenerated index page: Home.md")
    print(f"\nTotal pages generated: {len(generated_pages) + 1}")
    if reused_content_count > 0:
        print(f"Pages with reused existing content: {reused_content_count}")

    # Upload to wiki if requested
    if args.upload:
        print("\nUploading to GitHub wiki...")
        if upload_to_wiki(output_dir, args.repo_url, args.commit_message):
            print("✓ Wiki upload completed successfully")
        else:
            print("✗ Wiki upload failed")
            return 1

    print("\nNext steps:")
    if not args.upload:
        print("1. Review and edit the generated pages in the 'wiki-pages' directory")
        print("2. Upload these files to your GitHub wiki repository")
        print("3. Or copy/paste the content to create wiki pages manually")
        print("4. Or run with --upload to automatically upload to wiki")
    else:
        print("1. Check your GitHub wiki repository for the updated pages")
        print("2. Review and edit pages as needed directly in the wiki")

    print(
        "\nNote: GitHub wiki pages should be named exactly as shown (e.g., 'Online-Help-sectionname')"
    )

    return 0


if __name__ == "__main__":
    exit(main())
