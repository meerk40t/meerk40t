#!/usr/bin/env python3
"""
Script to analyze generated wiki pages and identify areas with insufficient documentation.
"""

import os
import re
from pathlib import Path


def analyze_wiki_pages(wiki_dir):
    """Analyze all wiki pages for placeholder content and documentation quality."""

    placeholder_patterns = [
        r"\*Add a detailed description.*?\*",
        r"\*Step 1\*",
        r"\*Step 2\*",
        r"\*Step 3\*",
        r"\*Add technical information.*?\*",
        r"\*Add screenshots.*?\*",
        r"\*Link to related help topics:\*",
        r"TODO",
        r"FIXME",
        r"placeholder",
        # Removed 'template' as it's too broad and matches legitimate content in templates.md
    ]

    results = {"insufficient": [], "minimal": [], "adequate": [], "good": []}

    # Skip index files
    skip_files = {"Home.md", "README.md"}

    for file_path in Path(wiki_dir).glob("*.md"):
        if file_path.name in skip_files:
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Count placeholder instances
        placeholder_count = 0
        for pattern in placeholder_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            placeholder_count += len(matches)

        # Analyze content quality
        lines = content.split("\n")
        content_lines = [
            line
            for line in lines
            if line.strip() and not line.startswith("#") and not line.startswith("---")
        ]

        # Check for actual descriptive content
        has_description = bool(
            re.search(r"## Description\s*\n.*?(?=\n##|\n---|\Z)", content, re.DOTALL)
        )
        has_screenshots = "![grafik]" in content or "screenshots" in content.lower()
        has_detailed_steps = (
            len([line for line in content_lines if len(line.strip()) > 50]) > 5
        )

        # Categorize documentation quality
        if placeholder_count >= 3:
            results["insufficient"].append(
                {
                    "file": file_path.name,
                    "placeholders": placeholder_count,
                    "has_description": has_description,
                    "has_screenshots": has_screenshots,
                }
            )
        elif placeholder_count == 1 or 2:
            results["minimal"].append(
                {
                    "file": file_path.name,
                    "placeholders": placeholder_count,
                    "has_description": has_description,
                    "has_screenshots": has_screenshots,
                }
            )
        elif has_description and has_detailed_steps:
            results["good"].append(
                {
                    "file": file_path.name,
                    "placeholders": placeholder_count,
                    "has_description": has_description,
                    "has_screenshots": has_screenshots,
                }
            )
        else:
            results["adequate"].append(
                {
                    "file": file_path.name,
                    "placeholders": placeholder_count,
                    "has_description": has_description,
                    "has_screenshots": has_screenshots,
                }
            )

    return results


def print_analysis(results):
    """Print the analysis results."""

    print("=== MeerK40t Wiki Documentation Analysis ===\n")

    print("📊 SUMMARY:")
    print(f"   Insufficient documentation: {len(results['insufficient'])} pages")
    print(f"   Minimal documentation: {len(results['minimal'])} pages")
    print(f"   Adequate documentation: {len(results['adequate'])} pages")
    print(f"   Good documentation: {len(results['good'])} pages")
    print()

    if results["insufficient"]:
        print("🚨 CRITICAL: Pages with INSUFFICIENT documentation (3+ placeholders):")
        for item in sorted(
            results["insufficient"], key=lambda x: x["placeholders"], reverse=True
        ):
            status = []
            if item["has_description"]:
                status.append("has desc")
            if item["has_screenshots"]:
                status.append("has screenshots")
            status_str = f" ({', '.join(status)})" if status else ""
            print(
                f"   • {item['file']} - {item['placeholders']} placeholders{status_str}"
            )
        print()

    if results["minimal"]:
        print("⚠️  WARNING: Pages with MINIMAL documentation (1-2 placeholders):")
        for item in sorted(
            results["minimal"], key=lambda x: x["placeholders"], reverse=True
        ):
            status = []
            if item["has_description"]:
                status.append("has desc")
            if item["has_screenshots"]:
                status.append("has screenshots")
            status_str = f" ({', '.join(status)})" if status else ""
            print(
                f"   • {item['file']} - {item['placeholders']} placeholders{status_str}"
            )
        print()

    if results["adequate"]:
        print("✅ ADEQUATE: Pages with acceptable documentation:")
        for item in results["adequate"]:
            status = []
            if item["has_description"]:
                status.append("has desc")
            if item["has_screenshots"]:
                status.append("has screenshots")
            status_str = f" ({', '.join(status)})" if status else ""
            print(f"   • {item['file']}{status_str}")
        print()

    if results["good"]:
        print("🎯 EXCELLENT: Pages with comprehensive documentation:")
        for item in results["good"]:
            status = []
            if item["has_description"]:
                status.append("has desc")
            if item["has_screenshots"]:
                status.append("has screenshots")
            status_str = f" ({', '.join(status)})" if status else ""
            print(f"   • {item['file']}{status_str}")
        print()

    # Priority recommendations
    print("🎯 PRIORITY RECOMMENDATIONS:")
    print(
        f"   1. Focus on the {len(results['insufficient']) // 10 * 10}+ pages with 3+ placeholders first"
    )
    print("   2. Add detailed descriptions and usage steps")
    print("   3. Include screenshots for visual features")
    print("   4. Remove placeholder text and replace with actual content")
    print("   5. Test documentation by having new users follow the guides")


if __name__ == "__main__":
    wiki_dir = "wiki-pages"
    if not os.path.exists(wiki_dir):
        print(f"Error: {wiki_dir} directory not found!")
        exit(1)

    results = analyze_wiki_pages(wiki_dir)
    print_analysis(results)
