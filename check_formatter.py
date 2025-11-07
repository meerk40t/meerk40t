import re

with open("wiki-pages/Online-Help-formatter.md", "r", encoding="utf-8") as f:
    content = f.read()

patterns = [
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
]

total = 0
for pattern in patterns:
    matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
    if matches:
        print(f"Pattern {pattern}: {len(matches)} matches")
        for match in matches:
            print(f"  - {match}")
        total += len(matches)

print(f"Total placeholders: {total}")
