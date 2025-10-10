import os
import re

# Find all Python files with SetHelpText calls
results = []
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "SetHelpText(" in content:
                        # Extract help sections
                        help_matches = re.findall(
                            r'SetHelpText\(\s*["\']([^"\']+)["\']', content
                        )
                        if help_matches:
                            results.append((filepath, help_matches))
            except Exception:
                pass

print("Modules with SetHelpText calls:")
for filepath, sections in results:
    print(f"{filepath}: {sections}")
