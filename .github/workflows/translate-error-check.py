import os
import re


def find_erroneous_translations(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    found_error = False
    matches_msgid = re.findall(r'msgid "(.*?)"', content, re.DOTALL)
    matches_msgstr = re.findall(r'msgstr "(.*?)"', content, re.DOTALL)

    if len(matches_msgid) != len(matches_msgstr):
        print(f"Error: Inconsistent Count of msgid/msgstr {file_path}: {len(matches_msgstr)} to {len(matches_msgid)}")
        found_error = True

    for msgid, msgstr in zip(matches_msgid, matches_msgstr):
        # Find words inside curly brackets in both msgid and msgstr
        words_msgid = re.findall(r"\{(.+?)\}", msgid)
        words_msgstr = re.findall(r"\{(.+?)\}", msgstr)
        if not words_msgstr or not words_msgid:
            continue

        # Compare words and check for differences
        for word_msgstr in words_msgstr:
            if word_msgstr not in words_msgid:
                print(
                    f"Error: Inconsistent translation in {file_path}: {word_msgstr} in msgstr, {words_msgid} in msgids"
                )
                found_error = True
    return found_error


def find_po_files(directory="."):
    found_error = False
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".po"):
                file_path = os.path.join(root, file)
                if find_erroneous_translations(file_path):
                    found_error = True
    if found_error:
        exit(1)


if __name__ == "__main__":
    find_po_files()
    print("No erroneous translations found.")
