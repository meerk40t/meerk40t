"""
translate.py

This script checks .po translation files for errors and compiles them into .mo files for Meerk40t.
Features:
    - Checks for mismatched curly braces and smart quotes in .po files
    - Verifies consistency of curly-bracketed variables between msgid and msgstr
    - Reports empty msgid/msgstr pairs
    - Compiles valid .po files into .mo files
    - Supports force recompilation and locale selection via CLI

Usage:
    python translate.py [--force] [locales...]
    --force      Force recompilation of all .mo files
    <locales>    List of locale codes to process (default: all)
"""

import os
import re
import argparse


def are_curly_brackets_matched(input_str: str) -> bool:
    """
    Checks if curly brackets are properly matched in a string, considering escaped brackets.
    """
    stack = []
    escaped = False
    for char in input_str:
        if char == "\\":
            escaped = True
            continue
        if escaped:
            escaped = False
            continue
        if char == "{":
            stack.append("{")
        elif char == "}":
            if not stack:
                return False
            stack.pop()
    return not stack


def contain_smart_quotes(line: str) -> bool:
    """
    Returns True if the line contains smart quotes (e.g., ”) in msgid or msgstr.
    """
    # Check for ”
    line_str = line.strip()
    return bool(
        line_str.startswith("msgid ”")
        or line_str.startswith("msgstr ”")
        or line_str.startswith("”")
    )


def find_erroneous_translations(file_path: str) -> bool:
    """
    Checks a .po file for translation errors:
    - Mismatched curly braces
    - Smart quotes
    - Inconsistent curly-bracketed variables between msgid and msgstr
    - Empty msgid/msgstr pairs
    Returns True if any errors are found.
    """
    with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as file:
        file_lines = file.readlines()

    found_error = False
    index = 0
    msgids = []
    msgstrs = []
    lineids = []

    for i, line in enumerate(file_lines):
        if not are_curly_brackets_matched(line):
            found_error = True
            print(f"Error: {file_path}\nLine {i} has mismatched curly braces:\n{line}")
        if contain_smart_quotes(line):
            found_error = True
            print(f"Error: {file_path}\nLine {i} contains invalid quotes:\n{line}")

    m_id = ""
    m_msg = ""
    while index < len(file_lines):
        try:
            if file_lines[index].strip() == "" or file_lines[index].startswith("#"):
                pass
            else:
                msgids.append("")
                lineids.append(index)
                # Find msgid and all multi-lined message ids
                if re.match(r'msgid \s*"(.*)"', file_lines[index]):
                    m = re.match(r'msgid \s*"(.*)"', file_lines[index])
                    msgids[-1] = m.group(1)
                    m_id = m.group(1)
                    index += 1
                    if index >= len(file_lines):
                        break
                    while re.match('^"(.*)"$', file_lines[index]):
                        m = re.match('^"(.*)"$', file_lines[index])
                        msgids[-1] += m.group(1)
                        m_id += m.group(1)
                        index += 1
                msgstrs.append("")
                m_msg = ""
                # find all message strings and all multi-line message strings
                if re.match('msgstr "(.*)"', file_lines[index]):
                    m = re.match('msgstr "(.*)"', file_lines[index])
                    msgstrs[-1] += m.group(1)
                    m_msg += m.group(1)
                    index += 1
                    while re.match('^"(.*)"$', file_lines[index]):
                        m = re.match('^"(.*)"$', file_lines[index])
                        msgstrs[-1] += m.group(1)
                        m_msg += m.group(1)
                        index += 1
            index += 1
        except IndexError:
            break

    if len(msgids) != len(msgstrs):
        print(
            f"Error: Inconsistent Count of msgid/msgstr {file_path}: {len(msgstrs)} to {len(msgids)}"
        )
        found_error = True

    for msgid, msgstr in zip(msgids, msgstrs):
        # Find words inside curly brackets in both msgid and msgstr
        words_msgid = re.findall(r"\{(.+?)\}", msgid)
        words_msgstr = re.findall(r"\{(.+?)\}", msgstr)
        if not words_msgstr or not words_msgid:
            continue

        # Compare words and check for differences
        for word_msgstr in words_msgstr:
            if word_msgstr not in words_msgid:
                print(
                    f"Error: Inconsistent translation in {file_path}: '{word_msgstr}' in msgstr, {words_msgid} in msgids"
                )
                found_error = True

    erct = 0
    idx = 0
    er_s = list()
    for msgid, msgstr, line in zip(msgids, msgstrs, lineids):
        idx += 1
        if len(msgid) == 0 and len(msgstr) == 0:
            erct += 1
            er_s.append(str(line))
    if erct > 0:
        print(
            f"{erct} empty pair{'s' if erct == 0 else ''} msgid '' + msgstr '' found in {file_path}\n{','.join(er_s)}"
        )
        found_error = True
    return found_error


# Simple tool to recursively translate all .po-files into their .mo-equivalents under ./locale/LC_MESSAGES
def create_mo_files(force: bool, locales: list[str]) -> list:
    """
    Recursively compiles all valid .po files into .mo files under ./locale/LC_MESSAGES.
    Skips files with errors. If force is True, always recompiles.
    Returns a list of tuples (locale_dir, [mo_files]).
    """
    try:
        import polib
    except ImportError:
        print(
            "polib missing - you need to install that library, eg. 'pip install polib'"
        )
        return

    data_files = []
    localedir = "./locale"
    po_dirs = []
    po_locales = []
    for locale_name in next(os.walk(localedir))[1]:
        po_dirs.append(localedir + "/" + locale_name + "/LC_MESSAGES/")
        po_locales.append(locale_name)
    counts = [0, 0, 0]
    for d_local, d in zip(po_locales, po_dirs):
        if len(locales) > 0 and d_local not in locales:
            print(f"Skip locale {d_local}")
            continue
        mo_files = []
        po_files = [f for f in next(os.walk(d))[2] if os.path.splitext(f)[1] == ".po"]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            if find_erroneous_translations(d + po_file):
                print(f"Skipping {d + po_file} as invalid...")
                counts[2] += 1
                continue
            mo_file = filename + ".mo"
            doit = True
            if os.path.exists(d + mo_file):
                res = polib.detect_encoding(d + po_file)
                res2 = polib.detect_encoding(d + mo_file)
                po_date = os.path.getmtime(d + po_file)
                mo_date = os.path.getmtime(d + mo_file)
                if mo_date > po_date:
                    print(
                        f"mo-File for {d}{po_file} is newer (input encoded={res}, output encoded={res2})..."
                    )
                    doit = False
            if doit or force:
                if doit:
                    action = "Translate"
                else:
                    action = "Forced translate"
                res = polib.detect_encoding(d + po_file)
                try:
                    po = polib.pofile(d + po_file)
                    po.save_as_mofile(d + mo_file)
                except OSError as err:
                    print(f"Unexpected {err=}")
                    counts[2] += 1
                    continue

                res2 = polib.detect_encoding(d + mo_file)

                print(
                    f"{action} {d}{po_file} (input encoded={res}, output encoded={res2})"
                )
                mo_files.append(d + mo_file)
                counts[0] += 1
            else:
                counts[1] += 1
        data_files.append((d, mo_files))
    print(
        f"Total: {counts[0] + counts[1]}, Translated: {counts[0]}, Ignored: {counts[1]}, Errors: {counts[2]}"
    )
    return data_files


def main():
    """
    Main entry point for the script. Parses CLI arguments and triggers compilation.
    """
    parser = argparse.ArgumentParser(
        description="Check and compile Meerk40t .po translation files into .mo files."
    )
    parser.add_argument(
        "locales",
        nargs="*",
        default=[],
        help="Locale codes to process (default: all locales)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recompilation of all .mo files regardless of timestamps",
    )
    args = parser.parse_args()

    if args.locales:
        print(f"Will compile po-files for {', '.join(args.locales)}")
    else:
        print("Will compile all po-files")
    create_mo_files(args.force, args.locales)


if __name__ == "__main__":
    main()
