#!/usr/bin/env python3
"""
MeerK40t Help Wiki Generator

This script extracts all help sections from the MeerK40t codebase and generates
template wiki pages for the GitHub wiki help system.

Usage:
    python generate_help_wiki.py [--upload]

Options:
    --upload    Automatically upload generated pages to GitHub wiki repository

This will create markdown files in a '../wiki-pages' directory that can be uploaded
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
    # First check local wiki-pages directory
    local_wiki_dir = "../wiki-pages"
    local_filename = f"Online-Help-{section}.md"
    local_filepath = os.path.join(local_wiki_dir, local_filename)

    if os.path.exists(local_filepath):
        try:
            with open(local_filepath, "r", encoding="utf-8") as f:
                content = f.read()
                if content and len(content.strip()) > 200:  # Substantial content check
                    return content
        except Exception:
            pass

    # Then check wiki repository if it exists
    wiki_filename = f"Online-Help:-{section.upper()}.md"
    wiki_repo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "meerk40t.wiki"
    )

    # Check if wiki repo exists
    if not os.path.exists(wiki_repo_path):
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
    for root, dirs, files in os.walk(".."):
        # Skip certain directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".")
            and d not in ["__pycache__", "build", "dist", "tools", "test", "testgui"]
        ]

        for file in files:
            filepath = os.path.join(root, file)
            if file.endswith(".py"):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        # Use AST parsing to find SetHelpText calls
                        try:
                            tree = ast.parse(content, filepath)
                            for node in ast.walk(tree):
                                if isinstance(node, ast.Call):
                                    # Handle both SetHelpText("string") and self.SetHelpText("string")
                                    func_name = None
                                    if (
                                        isinstance(node.func, ast.Name)
                                        and node.func.id == "SetHelpText"
                                    ):
                                        func_name = "SetHelpText"
                                    elif (
                                        isinstance(node.func, ast.Attribute)
                                        and node.func.attr == "SetHelpText"
                                    ):
                                        func_name = "SetHelpText"

                                    if func_name == "SetHelpText" and node.args:
                                        arg = node.args[0]

                                        # Handle SetHelpText("string")
                                        arg_value = None
                                        if isinstance(arg, ast.Constant) and isinstance(
                                            arg.value, str
                                        ):
                                            arg_value = arg.value

                                        if (
                                            arg_value
                                            and isinstance(arg_value, str)
                                            and arg_value.strip()
                                        ):
                                            help_sections.add(arg_value)
                                            help_context[arg_value].append(filepath)

                                        # Handle SetHelpText(_("string"))
                                        elif (
                                            isinstance(arg, ast.Call)
                                            and isinstance(arg.func, ast.Name)
                                            and arg.func.id == "_"
                                        ):
                                            if arg.args and len(arg.args) > 0:
                                                inner_arg = arg.args[0]
                                                inner_value = None
                                                if isinstance(
                                                    inner_arg, ast.Constant
                                                ) and isinstance(inner_arg.value, str):
                                                    inner_value = inner_arg.value

                                                if (
                                                    inner_value
                                                    and isinstance(inner_value, str)
                                                    and inner_value.strip()
                                                ):
                                                    help_sections.add(inner_value)
                                                    help_context[inner_value].append(
                                                        filepath
                                                    )

                                        # Handle SetHelpText(variable) - try to resolve if it's a simple string constant
                                        elif isinstance(arg, ast.Name):
                                            # Try to find the variable assignment in the same scope
                                            var_name = arg.id
                                            var_value = None

                                            # Look for assignment in the same function/class
                                            for scope_node in ast.walk(tree):
                                                if isinstance(scope_node, ast.Assign):
                                                    for target in scope_node.targets:
                                                        if (
                                                            isinstance(target, ast.Name)
                                                            and target.id == var_name
                                                        ):
                                                            if (
                                                                isinstance(
                                                                    scope_node.value,
                                                                    ast.Constant,
                                                                )
                                                                and isinstance(
                                                                    scope_node.value.value,
                                                                    str,
                                                                )
                                                                and scope_node.value.value.strip()
                                                            ):
                                                                var_value = scope_node.value.value
                                                                break
                                                    if var_value:
                                                        break

                                            if var_value:
                                                help_sections.add(var_value)
                                                help_context[var_value].append(filepath)

                                        # Handle f-strings (simple cases)
                                        elif (
                                            isinstance(arg, ast.JoinedStr)
                                            and arg.values
                                        ):
                                            # For simple f-strings like f"prefix{suffix}", try to extract
                                            parts = []
                                            for value in arg.values:
                                                if isinstance(
                                                    value, ast.Constant
                                                ) and isinstance(value.value, str):
                                                    parts.append(value.value)
                                                elif isinstance(
                                                    value, ast.FormattedValue
                                                ):
                                                    # For now, skip complex f-strings
                                                    parts = None
                                                    break

                                            if parts and "".join(parts).strip():
                                                fstring_value = "".join(parts)
                                                help_sections.add(fstring_value)
                                                help_context[fstring_value].append(
                                                    filepath
                                                )
                        except SyntaxError:
                            # Skip files with syntax errors - don't use regex fallback to avoid matching code
                            pass
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


def parse_docstring_sections(docstring):
    """
    Parse docstring to extract structured sections.

    Args:
        docstring (str): The docstring to parse

    Returns:
        dict: Dictionary with extracted sections
    """
    sections = {
        "technical_purpose": "",
        "signal_listeners": [],
        "end_user_perspective": "",
        "other_content": "",
    }

    if not docstring:
        return sections

    lines = docstring.split("\n")
    current_section = "other_content"
    current_content = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("**Technical Purpose:**") or stripped.startswith(
            "**Technical Details:**"
        ):
            # Save previous section
            if current_content:
                if current_section == "other_content":
                    sections[current_section] = "\n".join(current_content).strip()
                elif current_section == "signal_listeners":
                    sections[current_section] = current_content
                else:
                    sections[current_section] = "\n".join(current_content).strip()
                current_content = []

            current_section = "technical_purpose"
        elif stripped.startswith("**Signal Listeners:**") or stripped.startswith(
            "**Signals:**"
        ):
            # Save previous section
            if current_content:
                if current_section == "other_content":
                    sections[current_section] = "\n".join(current_content).strip()
                elif current_section == "signal_listeners":
                    sections[current_section] = current_content
                else:
                    sections[current_section] = "\n".join(current_content).strip()
                current_content = []

            current_section = "signal_listeners"
        elif (
            stripped.startswith("**End-User Perspective:**")
            or stripped.startswith("**User Experience:**")
            or stripped.startswith("**User Interface:**")
        ):
            # Save previous section
            if current_content:
                if current_section == "other_content":
                    sections[current_section] = "\n".join(current_content).strip()
                elif current_section == "signal_listeners":
                    sections[current_section] = current_content
                else:
                    sections[current_section] = "\n".join(current_content).strip()
                current_content = []

            current_section = "end_user_perspective"
        else:
            if current_section == "signal_listeners":
                if stripped.startswith("- ") or stripped.startswith("* "):
                    current_content.append(stripped[2:].strip())
                elif stripped and not stripped.startswith("**"):
                    current_content.append(stripped)
            else:
                current_content.append(line)

    # Save final section
    if current_content:
        if current_section == "other_content":
            sections[current_section] = "\n".join(current_content).strip()
        elif current_section == "signal_listeners":
            sections[current_section] = current_content
        else:
            sections[current_section] = "\n".join(current_content).strip()

    return sections


def find_related_help_sections(current_section, all_sections, help_context):
    """
    Find related help sections based on various criteria.

    Args:
        current_section (str): Current help section
        all_sections (set): All available help sections
        help_context (dict): Mapping of sections to their files

    Returns:
        list: List of related section names
    """
    related = []
    current_files = help_context.get(current_section, [])
    current_category = None

    # Determine category of current section
    for file_path in current_files:
        if "grbl" in file_path.lower():
            current_category = "GRBL"
            break
        elif "lihuiyu" in file_path.lower() or "k40" in file_path.lower():
            current_category = "Lihuiyu/K40"
            break
        elif "balor" in file_path.lower():
            current_category = "Balor"
            break
        elif "moshi" in file_path.lower():
            current_category = "Moshi"
            break
        elif "newly" in file_path.lower():
            current_category = "Newly"
            break
        elif "tools" in file_path.lower():
            current_category = "Tools"
            break
        elif "navigation" in file_path.lower():
            current_category = "Navigation"
            break

    # Find sections from same module
    current_module = None
    for file_path in current_files:
        # Extract module path (e.g., meerk40t/grbl/gui/ -> grbl)
        parts = file_path.replace("\\", "/").split("/")
        if "meerk40t" in parts:
            idx = parts.index("meerk40t")
            if idx + 1 < len(parts):
                current_module = parts[idx + 1]
                break

    if current_module:
        for section, files in help_context.items():
            if section != current_section:
                for file_path in files:
                    parts = file_path.replace("\\", "/").split("/")
                    if "meerk40t" in parts:
                        idx = parts.index("meerk40t")
                        if idx + 1 < len(parts) and parts[idx + 1] == current_module:
                            related.append(section)
                            break

    # Find sections in same category
    if current_category:
        for section, files in help_context.items():
            if section != current_section and section not in related:
                section_category = None
                for file_path in files:
                    if "grbl" in file_path.lower():
                        section_category = "GRBL"
                        break
                    elif "lihuiyu" in file_path.lower():
                        section_category = "Lihuiyu/K40"
                        break
                    elif "balor" in file_path.lower():
                        section_category = "Balor"
                        break
                    elif "moshi" in file_path.lower():
                        section_category = "Moshi"
                        break
                    elif "newly" in file_path.lower():
                        section_category = "Newly"
                        break
                    elif "tools" in file_path.lower():
                        section_category = "Tools"
                        break
                    elif "navigation" in file_path.lower():
                        section_category = "Navigation"
                        break

                if section_category == current_category:
                    related.append(section)

    # Find sections with similar keywords
    current_words = set(current_section.lower().replace("_", " ").split())
    for section in all_sections:
        if section != current_section and section not in related:
            section_words = set(section.lower().replace("_", " ").split())
            # Check for common words
            if current_words & section_words:
                related.append(section)
                if len(related) >= 3:  # Limit to 3 related sections
                    break

    return related[:3]  # Return max 3 related sections


def generate_wiki_page(section, files, all_sections, help_context):
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
        elif "lihuiyu" in file_path.lower():
            categories.append("Lihuiyu/K40")
        elif "balor" in file_path.lower():
            categories.append("Balor")
        elif "moshi" in file_path.lower():
            categories.append("Moshi")
        elif "newly" in file_path.lower():
            categories.append("Newly")
        elif "tools" in file_path.lower():
            categories.append("Tools")
        elif "navigation" in file_path.lower():
            categories.append("Navigation")
        elif "element" in section.lower() and (
            "property" in section.lower() or "modify" in section.lower()
        ):
            categories.append("Element Properties")
        elif "operation" in section.lower() and "property" in section.lower():
            categories.append("Operation Properties")
        elif "element" in section.lower() and (
            "transform" in section.lower()
            or "align" in section.lower()
            or "modify" in section.lower()
        ):
            categories.append("Element Modification")
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
    docstring_sections = None

    for analysis in module_analyses:
        # Get class docstrings and parse them
        for class_info in analysis.get("class_info", []):
            if class_info.get("docstring"):
                parsed_sections = parse_docstring_sections(class_info["docstring"])
                if (
                    parsed_sections["technical_purpose"]
                    or parsed_sections["signal_listeners"]
                    or parsed_sections["end_user_perspective"]
                ):
                    docstring_sections = parsed_sections
                    break
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

    # Use end-user perspective if available
    if docstring_sections and docstring_sections["end_user_perspective"]:
        description += "\n\n" + docstring_sections["end_user_perspective"]
    elif class_descriptions:
        description += "\n\n" + class_descriptions[0]  # Use the first class docstring

    # If we have existing content, use it instead of generated content
    if existing_description and existing_description.strip():
        description = existing_description.strip()
    else:
        # If we have existing content, add it to the description
        if existing_description:
            description += "\n\n" + existing_description

    # Generate usage information based on UI elements
    usage_info = ""
    if ui_elements:
        usage_info += "### Available Controls\n\n"
        for element in ui_elements[:8]:  # Limit to first 8 elements
            usage_info += f"- **{element['label']}** ({element['type']})\n"
        usage_info += "\n"

    # Add functionality hints
    if functionality_hints:
        unique_hints = list(set(functionality_hints))[:3]  # Limit to 3 unique hints
        usage_info += "### Key Features\n\n"
        for hint in unique_hints:
            usage_info += f"- Integrates with: `{hint}`\n"
        usage_info += "\n"

    # Generate technical details section
    technical_details = ""
    if docstring_sections:
        if docstring_sections["technical_purpose"]:
            technical_details += docstring_sections["technical_purpose"] + "\n\n"

        if docstring_sections["signal_listeners"]:
            technical_details += "**Signal Integration:**\n"
            for signal in docstring_sections["signal_listeners"][
                :5
            ]:  # Limit to 5 signals
                technical_details += f"- {signal}\n"
            technical_details += "\n"

    # Find related topics
    related_sections = find_related_help_sections(section, all_sections, help_context)
    related_links = ""
    if related_sections:
        for related_section in related_sections:
            related_title = related_section.replace("_", " ").title()
            related_links += f"- [[Online Help: {related_title}]]\n"

    # Check if we have substantial existing content to determine template style
    has_existing_content = (
        existing_description and len(existing_description.strip()) > 100
    )

    if has_existing_content:
        # Use a simpler template that preserves existing content
        template = f"""# Online Help: {title}

## Overview

{description}

## Location in MeerK40t

This help section is accessed from:
{file_list}

## Category

**{category}**

## Technical Details

{technical_details}
## Related Topics

*Link to related help topics:*

{related_links}
## Screenshots

*Add screenshots showing the feature in action.*

---

*This help page was automatically updated. Please review and enhance with additional information about the {section} feature.*
"""
    else:
        # Use the full template with placeholders for new content
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

## Technical Details

{technical_details}*Add technical information about how this feature works internally.*

## Related Topics

*Link to related help topics:*

{related_links}
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
    Generate a structured docstring for a class based on its analysis.

    Args:
        class_name (str): Name of the class
        methods (list): List of method dictionaries
        ui_elements (list): List of UI element dictionaries
        functionality_hints (list): List of functionality indicators
        comments (list): List of relevant comments

    Returns:
        str: Generated structured docstring
    """
    # Get basic panel description
    panel_description = get_panel_description(class_name, ui_elements)

    # Extract signal-related information from methods
    signal_listeners = []
    signal_emissions = []

    for method in methods:
        method_code = method.get("code", "")

        # Look for signal listeners
        if "@signal_listener(" in method_code:
            # Extract signal name from decorator
            lines = method_code.split("\n")
            for line in lines:
                if "@signal_listener(" in line:
                    start = line.find("@signal_listener(")
                    if start != -1:
                        signal_part = line[start + 16 :]  # Skip "@signal_listener("
                        end = signal_part.find(")")
                        if end != -1:
                            signal_name = (
                                signal_part[:end].strip().strip('"').strip("'")
                            )
                            signal_listeners.append(signal_name)
                            break

        # Look for signal emissions in method body
        if "signal(" in method_code or "self.context.signal(" in method_code:
            # Try to extract signal names from method calls
            import re

            signal_matches = re.findall(r'signal\(\s*["\']([^"\']+)["\']', method_code)
            for signal in signal_matches:
                if signal not in signal_emissions:
                    signal_emissions.append(signal)

    # Generate technical purpose based on UI elements and functionality
    technical_purpose = generate_technical_purpose(
        class_name, ui_elements, functionality_hints
    )

    # Generate end-user perspective
    end_user_perspective = generate_end_user_perspective(class_name, ui_elements)

    # Build structured docstring
    docstring_parts = [f"{panel_description}"]

    if technical_purpose:
        docstring_parts.append(f"\n**Technical Purpose:**\n{technical_purpose}")

    if signal_listeners:
        docstring_parts.append(
            "\n**Signal Listeners:**\n"
            + "\n".join(
                f"- {signal}: Updates UI when {signal.replace('_', ' ')} changes externally"
                for signal in signal_listeners[:3]
            )
        )

    if signal_emissions:
        docstring_parts.append(
            "\n**Signal Emissions:**\n"
            + "\n".join(
                f"- {signal}: Emitted when {signal.replace('_', ' ')} changes to update display"
                for signal in signal_emissions[:3]
            )
        )

    if end_user_perspective:
        docstring_parts.append(f"\n**End-User Perspective:**\n{end_user_perspective}")

    return "".join(docstring_parts).strip()


def generate_technical_purpose(class_name, ui_elements, functionality_hints):
    """Generate technical purpose description."""
    class_lower = class_name.lower()

    # Base descriptions for different panel types
    if "transform" in class_lower:
        purpose = "Provides transformation controls for scaling, rotating, and positioning design elements. "
    elif "drag" in class_lower:
        purpose = "Provides interactive controls for positioning the laser head and aligning it with design elements. "
    elif "jog" in class_lower:
        purpose = "Provides manual movement controls for the laser head around the work area. "
    elif "move" in class_lower:
        purpose = "Provides coordinate-based movement controls for sending the laser to specific positions. "
    elif "pulse" in class_lower:
        purpose = "Provides pulse firing controls for laser alignment and testing operations. "
    elif "zmove" in class_lower or "z_move" in class_lower:
        purpose = "Provides Z-axis movement controls for adjusting laser head height. "
    elif "align" in class_lower:
        purpose = "Provides alignment and distribution controls for design elements. "
    elif "device" in class_lower:
        purpose = (
            "Provides device configuration and control interfaces for laser hardware. "
        )
    elif "material" in class_lower:
        purpose = "Provides material-specific settings and optimization controls. "
    elif "simulation" in class_lower:
        purpose = (
            "Provides job simulation and preview functionality before laser execution. "
        )
    elif "navigation" in class_lower:
        purpose = "Provides navigation and positioning controls for laser movement. "
    elif "magnet" in class_lower:
        purpose = (
            "Provides magnet snapping configuration controls for object alignment. "
        )
    else:
        purpose = f"Provides user interface controls for {class_name.lower().replace('panel', '').strip()} functionality. "

    # Add UI element details
    if ui_elements:
        ui_types = []
        for elem in ui_elements[:3]:  # Limit to first 3 elements
            elem_type = elem.get("type", "").lower()
            if elem_type and elem_type not in ui_types:
                ui_types.append(elem_type)

        if ui_types:
            purpose += f"Features {', '.join(ui_types)} controls for user interaction. "

    # Add functionality hints
    if functionality_hints:
        unique_hints = list(set(functionality_hints))[:2]  # Limit to 2 unique hints
        if unique_hints:
            purpose += (
                f"Integrates with {', '.join(unique_hints)} for enhanced functionality."
            )

    return purpose.strip()


def generate_end_user_perspective(class_name, ui_elements):
    """Generate end-user perspective description."""
    class_lower = class_name.lower()

    # User-focused descriptions
    if "transform" in class_lower:
        perspective = "This panel lets you scale, rotate, and reposition your design elements. Use the controls to adjust size, orientation, and position before cutting."
    elif "drag" in class_lower:
        perspective = "This panel helps you position the laser head precisely. Use it to align the laser with specific points in your design or move to exact coordinates."
    elif "jog" in class_lower:
        perspective = "This panel gives you manual control over laser movement. Use the directional buttons to move the laser head around the work area for setup and testing."
    elif "move" in class_lower:
        perspective = "This panel lets you send the laser to specific coordinates or saved positions. Enter coordinates directly or select from saved locations."
    elif "pulse" in class_lower:
        perspective = "This panel lets you fire short test pulses from the laser. Use it to test laser power, alignment, and focus before running full jobs."
    elif "zmove" in class_lower or "z_move" in class_lower:
        perspective = "This panel controls the up and down movement of the laser head. Use it to adjust focus height and material clearance."
    elif "align" in class_lower:
        perspective = "This panel helps you align and distribute design elements. Use it to create evenly spaced objects or align them to specific positions."
    elif "device" in class_lower:
        perspective = "This panel lets you configure and control your laser device. Set up connection parameters, adjust settings, and monitor device status."
    elif "material" in class_lower:
        perspective = "This panel helps you set up material-specific settings. Choose your material type and adjust cutting parameters for optimal results."
    elif "simulation" in class_lower:
        perspective = "This panel shows you exactly what will happen when you run your laser job. Preview the cutting path, timing, and results before starting."
    elif "navigation" in class_lower:
        perspective = "This panel provides controls for moving the laser around your work area. Use it for setup, testing, and precise positioning."
    elif "magnet" in class_lower:
        perspective = "This panel lets you customize how objects snap to guide lines. Set attraction strength and choose which object parts get attracted to magnets."
    else:
        # Generic description based on UI elements
        if ui_elements:
            ui_descriptions = []
            for elem in ui_elements[:3]:
                label = elem.get("label", "").strip()
                elem_type = elem.get("type", "").lower()
                if label and elem_type:
                    ui_descriptions.append(f'"{label}" ({elem_type})')

            if ui_descriptions:
                perspective = f"This panel provides controls for {class_name.lower().replace('panel', '').strip()} functionality. Key controls include {', '.join(ui_descriptions)}."
            else:
                perspective = f"This panel provides user interface controls for {class_name.lower().replace('panel', '').strip()} functionality in MeerK40t."
        else:
            perspective = f"This panel provides user interface controls for {class_name.lower().replace('panel', '').strip()} functionality in MeerK40t."

    return perspective


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

    # For class docstrings, use the same indentation as the class
    # For method docstrings, add 4 more spaces
    if current_docstring:
        # Existing docstring - preserve its indentation level
        docstring_line = lines[docstring_start]
        docstring_indent = docstring_line[
            : len(docstring_line) - len(docstring_line.lstrip())
        ]
        indented_docstring = f'{docstring_indent}"""{new_docstring}"""'
    else:
        # New docstring - use class indentation
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


def upload_to_wiki(wiki_dir="../wiki-pages", repo_url=None, commit_message=None):
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
        "--recreate",
        action="store_true",
        help="Recreate all wiki pages, even if they already exist with content",
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

    # Create output directory
    output_dir = "../wiki-pages"
    os.makedirs(output_dir, exist_ok=True)

    # Generate wiki pages
    generated_pages = []
    reused_content_count = 0
    skipped_pages_count = 0

    for section in sorted(help_sections):
        filename = f"Online-Help-{section}.md"
        filepath = os.path.join(output_dir, filename)

        # Check if page already exists and has substantial content
        existing_content = check_existing_wiki_page(section)
        existing_description = (
            extract_existing_content(existing_content) if existing_content else ""
        )

        # Skip generation if page exists with content and --recreate not used
        if existing_content and existing_description and not args.recreate:
            skipped_pages_count += 1
            print(
                f"Skipped: {filename} (already exists with content, use --recreate to overwrite)"
            )
            continue

        content = generate_wiki_page(
            section, help_context[section], help_sections, help_context
        )

        # Check if we reused existing content
        if existing_content and extract_existing_content(existing_content):
            reused_content_count += 1
            print(f"Generated: {filename} (reused existing content)")
        else:
            print(f"Generated: {filename}")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        generated_pages.append(filename)

    # Create an index page (only if it doesn't exist with substantial content)
    home_filepath = os.path.join(output_dir, "OnlineHelp.md")
    home_exists = os.path.exists(home_filepath)

    if home_exists:
        try:
            with open(home_filepath, "r", encoding="utf-8") as f:
                existing_home = f.read()
                # Check if it has substantial content (more than just a basic index)
                if len(existing_home.strip()) > 500:  # Substantial content threshold
                    print(
                        "Skipped: OnlineHelp.md (already exists with substantial content)"
                    )
                    total_pages = len(generated_pages)
                else:
                    home_exists = False  # Regenerate if it's just a basic index
        except Exception:
            home_exists = False

    if not home_exists:
        index_content = "# MeerK40t Online Help Index\n\n"
        index_content += f"This wiki contains help pages for {len(help_sections)} different features in MeerK40t.\n\n"
        index_content += "## Help Pages by Category\n\n"

        # Group by category
        categories = defaultdict(list)
        for section in help_sections:
            # Infer category from context
            category = "General"
            files = help_context[section]
            if any("balor" in f.lower() for f in files):
                category = "Balor"
            elif any("moshi" in f.lower() for f in files):
                category = "Moshi"
            elif any("newly" in f.lower() for f in files):
                category = "Newly"
            elif any("grbl" in f.lower() for f in files):
                category = "GRBL"
            elif any("lihuiyu" in f.lower() for f in files):
                category = "Lihuiyu/K40"
            elif any("tools" in f.lower() for f in files):
                category = "Tools"
            elif any("navigation" in f.lower() for f in files):
                category = "Navigation"
            elif "element" in section.lower() and (
                "property" in section.lower() or "modify" in section.lower()
            ):
                category = "Element Properties"
            elif "operation" in section.lower() and "property" in section.lower():
                category = "Operation Properties"
            elif "element" in section.lower() and (
                "transform" in section.lower()
                or "align" in section.lower()
                or "modify" in section.lower()
            ):
                category = "Element Modification"
            elif any("gui" in f.lower() for f in files):
                category = "GUI"

            categories[category].append(section)

        # Define category order (device categories first, then functional, then general)
        category_order = {
            "GRBL": 1,
            "Lihuiyu/K40": 2,
            "Balor": 3,
            "Moshi": 4,
            "Newly": 5,
            "Tools": 6,
            "Navigation": 7,
            "Element Properties": 8,
            "Operation Properties": 9,
            "Element Modification": 10,
            "GUI": 11,
            "General": 12,
        }

        for category, sections in sorted(
            categories.items(), key=lambda x: category_order.get(x[0], 99)
        ):
            index_content += f"### {category}\n\n"
            for section in sorted(sections):
                index_content += (
                    f"- [[Online Help: {section.replace('_', ' ').title()}]]\n"
                )
            index_content += "\n"

        index_content += "\n---\n\n"
        index_content += (
            "*This index is automatically generated. Last updated: "
            + __import__("datetime").datetime.now().strftime("%Y-%m-%d")
            + "*"
        )

        with open(home_filepath, "w", encoding="utf-8") as f:
            f.write(index_content)

        print("\nGenerated index page: OnlineHelp.md")
        total_pages = len(generated_pages) + 1
    else:
        total_pages = len(generated_pages)

    print(f"\nTotal pages generated: {total_pages}")
    if reused_content_count > 0:
        print(f"Pages with reused existing content: {reused_content_count}")
    if skipped_pages_count > 0:
        print(f"Pages skipped (already exist with content): {skipped_pages_count}")

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
        print("1. Review and edit the generated pages in the '../wiki-pages' directory")
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
