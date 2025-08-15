"""
translate.py

This script manages and validates .po translation files for Meerk40t.

Features:
    - Checks for mismatched curly braces and smart quotes in .po files
    - Verifies consistency of curly-bracketed variables between msgid and msgstr
    - Reports empty msgid/msgstr pairs
    - Compiles valid .po files into .mo files
    - Integrates delta_xx.po files into main .po files using polib, avoiding duplicates and updating only if msgstr is empty
    - Supports force recompilation and locale selection via CLI

Usage:
    python translate.py [--force] [--integrate] [locales...]
    --force       Force recompilation of all .mo files
    --integrate   Integrate delta_xx.po files into the main .po files
    <locales>     List of locale codes to process (default: all)
"""

import argparse
import os
import re

import polib

LOCALE_DIR = "./locale"


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

    def check_line_errors(file_lines, file_path):
        found_error = False
        for i, line in enumerate(file_lines):
            if not are_curly_brackets_matched(line):
                found_error = True
                print(
                    f"Error: {file_path}\nLine {i} has mismatched curly braces:\n{line}"
                )
            if contain_smart_quotes(line):
                found_error = True
                print(f"Error: {file_path}\nLine {i} contains invalid quotes:\n{line}")
        return found_error

    def extract_msg_pairs(file_lines):
        msgids, msgstrs, lineids = [], [], []
        index = 0
        while index < len(file_lines):
            try:
                if file_lines[index].strip() == "" or file_lines[index].startswith("#"):
                    index += 1
                    continue
                msgids.append("")
                lineids.append(index)
                # Find msgid and all multi-lined message ids
                if re.match(r'^msgid\s+"(.*)"', file_lines[index]):
                    m = re.match(r'^msgid\s+"(.*)"', file_lines[index])
                    m_id = m[1]
                    msgids[-1] = m_id
                    index += 1
                    if index >= len(file_lines):
                        break
                    while re.match('^"(.*)"$', file_lines[index]):
                        m = re.match('^"(.*)"$', file_lines[index])
                        msgids[-1] += m[1]
                        m_id += m[1]
                        index += 1
                msgstrs.append("")
                # find all message strings and all multi-line message strings
                if re.match('msgstr "(.*)"', file_lines[index]):
                    m = re.match('msgstr "(.*)"', file_lines[index])
                    m_msg = m[1]
                    msgstrs[-1] += m_msg
                    index += 1
                    while re.match('^"(.*)"$', file_lines[index]):
                        m = re.match('^"(.*)"$', file_lines[index])
                        msgstrs[-1] += m[1]
                        m_msg += m[1]
                        index += 1
                index += 1
            except IndexError:
                break
        return msgids, msgstrs, lineids

    def check_variable_consistency(msgids, msgstrs, file_path):
        found_error = False
        for msgid, msgstr in zip(msgids, msgstrs):
            words_msgid = re.findall(r"\{(.+?)\}", msgid)
            words_msgstr = re.findall(r"\{(.+?)\}", msgstr)
            if not words_msgstr or not words_msgid:
                continue
            for word_msgstr in words_msgstr:
                if word_msgstr not in words_msgid:
                    print(
                        f"Error: Variable {{{word_msgstr}}} in msgstr but not in msgid: {file_path}\n  msgid: {msgid}\n  msgstr: {msgstr}"
                    )
                    found_error = True
            for word_msgid in words_msgid:
                if word_msgid not in words_msgstr:
                    print(
                        f"Error: Variable {{{word_msgid}}} in msgid but not in msgstr: {file_path}\n  msgid: {msgid}\n  msgstr: {msgstr}"
                    )
                    found_error = True
        return found_error

    def check_empty_pairs(lineids, msgids, msgstrs, file_path):
        erct = 0
        er_s = []
        for line, (msgid, msgstr) in zip(lineids, zip(msgids, msgstrs)):
            if len(msgid) == 0 and len(msgstr) == 0:
                erct += 1
                er_s.append(str(line))
        if erct > 0:
            print(
                f"{erct} empty pair{'s' if erct != 1 else ''} msgid '' + msgstr '' found in {file_path}\n{','.join(er_s)}"
            )
            return True
        return False

    with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as file:
        file_lines = file.readlines()

    found_error = check_line_errors(file_lines, file_path)
    msgids, msgstrs, lineids = extract_msg_pairs(file_lines)

    if len(msgids) != len(msgstrs):
        print(
            f"Error: Inconsistent Count of msgid/msgstr {file_path}: {len(msgstrs)} to {len(msgids)}"
        )
        found_error = True

    found_error = check_variable_consistency(msgids, msgstrs, file_path) or found_error
    found_error = check_empty_pairs(lineids, msgids, msgstrs, file_path) or found_error

    return found_error


def create_mo_files(force: bool, locales: list[str]) -> list:
    """
    Recursively compiles all valid .po files into .mo files under ./locale/LC_MESSAGES.
    Skips files with errors. If force is True, always recompiles.
    Returns a list of tuples (locale_dir, [mo_files]).
    """

    def detect_encoding(file_path: str) -> str:
        """
        Detects the encoding of a file using polib's detect_encoding function.
        Returns the encoding as a string.
        """
        try:
            import chardet  # Ensure chardet is available for encoding detection

            return chardet.detect(open(file_path, "rb").read())["encoding"]  # type: ignore
        except ImportError:
            print(
                "chardet missing - falling back to polib's default encoding detection"
            )

        try:
            return polib.detect_encoding(file_path)
        except Exception as e:
            print(f"Error detecting encoding for {file_path}: {e}")
            return "utf-8"

    data_files = []
    po_dirs = []
    po_locales = []
    for locale_name in next(os.walk(LOCALE_DIR))[1]:
        po_dirs.append(f"{LOCALE_DIR}/{locale_name}/LC_MESSAGES/")
        po_locales.append(locale_name)
    counts = [0, 0, 0]
    for d_local, d in zip(po_locales, po_dirs):
        if locales and d_local not in locales:
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
            mo_file = f"{filename}.mo"
            doit = True
            if os.path.exists(d + mo_file):
                source_encoding = detect_encoding(d + po_file).lower()
                if source_encoding not in ("utf-8", "utf8"):
                    print(
                        f"Warning: {d + po_file} has non-utf8 encoding ({source_encoding}), can lead to unexpected results."
                    )
                    source_encoding = "utf-8"
                target_encoding = "utf-8"  # Default target encoding
                po_date = os.path.getmtime(d + po_file)
                mo_date = os.path.getmtime(d + mo_file)
                if mo_date > po_date:
                    print(
                        f"mo-File for {d}{po_file} is newer (input encoded={source_encoding}, output encoded={target_encoding})..."
                    )
                    doit = False
            if doit or force:
                action = "Translate" if doit else "Forced translate"
                try:
                    po = polib.pofile(d + po_file, encoding=source_encoding)
                    po.save_as_mofile(d + mo_file)
                except OSError as err:
                    print(f"Unexpected {err=}")
                    counts[2] += 1
                    continue

                target_encoding = "utf-8"

                print(
                    f"{action} {d}{po_file} (input encoded={source_encoding}, output encoded={target_encoding})"
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


def integrate_delta_files(locales: list[str]) -> None:
    """
    This code integrates translation updates from delta .po files (named delta_xx.po)
    into the main translation .po files for specified locales.
    It updates existing entries with new translations and adds new entries
    as needed, then removes the delta file.
    """
    for locale in locales:
        updates_applied = False
        main_po_file = f"./locale/{locale}/LC_MESSAGES/meerk40t.po"
        delta_po_file = f"./delta_{locale}.po"
        if not os.path.exists(delta_po_file):
            print(f"No delta file found for {locale}")
            continue
        if not os.path.exists(main_po_file):
            print(f"No main po file found for {locale}")
            continue
        print(f"Integrating {delta_po_file} into {main_po_file}")

        # Load main and delta .po files
        main_po = polib.pofile(main_po_file)
        delta_po = polib.pofile(delta_po_file)

        # Build dictionaries for fast lookup and to check duplicates
        main_entries = {entry.msgid: entry for entry in main_po}
        delta_entries = {}
        duplicate_msgids = set()
        for entry in delta_po:
            if entry.msgid in delta_entries:
                duplicate_msgids.add(entry.msgid)
            else:
                delta_entries[entry.msgid] = entry

        if duplicate_msgids:
            print(f"Duplicate msgid(s) found in delta file for {locale}:")
            for msgid in duplicate_msgids:
                print(f"  - {msgid}")

        # Integrate delta into main, handling conflicts
        conflicts = []
        for msgid, delta_entry in delta_entries.items():
            if msgid in main_entries:
                main_entry = main_entries[msgid]
                if main_entry.msgstr != delta_entry.msgstr:
                    conflicts.append(msgid)
                    # Prefer delta's translation, but log the conflict
                    main_entry.msgstr = delta_entry.msgstr
                    updates_applied = True
            else:
                # Add new entry from delta
                main_po.append(delta_entry)
                updates_applied = True

        if conflicts:
            print(f"Conflicting msgid(s) updated from delta for {locale}:")
            for msgid in conflicts:
                print(f"  - {msgid}")

        # Save the updated main .po file
        if updates_applied:
            main_po.save(main_po_file)
            print(
                f"Integrated delta for {locale}. {len(delta_entries)} entries processed."
            )
        else:
            print(
                f"No updates applied for {locale} (delta contained {len(delta_entries)} entries)."
            )

        # Remove the delta file after integration
        try:
            os.remove(delta_po_file)
        except Exception as e:
            print(f"Error removing {delta_po_file}: {e}")


def main() -> None:
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
    parser.add_argument(
        "--integrate",
        action="store_true",
        help="Integrate delta_xx.po files into the main .po files",
    )
    args = parser.parse_args()

    if args.locales:
        print(f"Will compile po-files for {', '.join(args.locales)}")
    else:
        print("Will compile all po-files")
    if len(args.locales) == 0:
        locales = []
        locales.extend(iter(next(os.walk(LOCALE_DIR))[1]))
        args.locales = locales

    if args.integrate:
        integrate_delta_files(args.locales)
    create_mo_files(args.force, args.locales)


if __name__ == "__main__":
    main()
