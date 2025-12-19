"""
translate.py

This script manages and validates .po translation files for MeerK40t.

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
import sys

import polib

LOCALE_DIR = "./locale"

# Determine whether output is a TTY. If not (redirected), disable ANSI codes.
try:
    is_tty = sys.stdout.isatty()
except Exception:
    is_tty = False

# On Windows, enable ANSI VT processing when running in a real terminal.
# This avoids a dependency on `colorama` by enabling terminal
# virtual terminal (ANSI) processing via the Win32 API.
if os.name == "nt" and is_tty:
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        h = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE = -11
        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(h, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        # If anything fails, fall back silently (colors will simply not work)
        pass

if is_tty:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"
else:
    RED = GREEN = YELLOW = BLUE = BOLD = ENDC = ""


def print_header(text):
    print(f"{BLUE}{BOLD}{'=' * 60}{ENDC}")
    print(f"{BLUE}{BOLD}{text.center(60)}{ENDC}")
    print(f"{BLUE}{BOLD}{'=' * 60}{ENDC}")


def print_error(text):
    print(f"{RED}ERROR: {text}{ENDC}")


def print_warning(text):
    print(f"{YELLOW}WARNING: {text}{ENDC}")


def print_success(text):
    print(f"{GREEN}{text}{ENDC}")


def print_info(text):
    print(f"{BLUE}{text}{ENDC}")


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
    Returns True if the line contains smart quotes (e.g., " or ") in msgid or msgstr.
    """
    # Check for smart quotes: " (left double quotation mark) and " (right double quotation mark)
    return '"' in line or '"' in line


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
                print_error(
                    f"{file_path}\n  Line {i + 1}: Mismatched curly braces\n  {line.strip()}"
                )
            # Smart quote check disabled - was incorrectly flagging valid files
            # if contain_smart_quotes(line):
            #     found_error = True
            #     print_error(f"{file_path}\n  Line {i+1}: Contains invalid quotes\n  {line.strip()}")
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
                    print_error(
                        f"Variable {{{word_msgstr}}} in msgstr but not in msgid: {file_path}\n  msgid: {msgid}\n  msgstr: {msgstr}"
                    )
                    found_error = True
            for word_msgid in words_msgid:
                if word_msgid not in words_msgstr:
                    print_error(
                        f"Variable {{{word_msgid}}} in msgid but not in msgstr: {file_path}\n  msgid: {msgid}\n  msgstr: {msgstr}"
                    )
                    found_error = True
        return found_error

    def check_empty_pairs(lineids, msgids, msgstrs, file_path):
        erct = 0
        er_s = []
        for line, (msgid, msgstr) in zip(lineids, zip(msgids, msgstrs)):
            if len(msgid) == 0 and len(msgstr) == 0:
                erct += 1
                er_s.append(str(line + 1))
        if erct > 0:
            print_warning(
                f"{erct} empty pair{'s' if erct != 1 else ''} msgid '' + msgstr '' found in {file_path}\n  Lines: {', '.join(er_s)}"
            )
            return True
        return False

    with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as file:
        file_lines = file.readlines()

    found_error = check_line_errors(file_lines, file_path)
    msgids, msgstrs, lineids = extract_msg_pairs(file_lines)

    if len(msgids) != len(msgstrs):
        print_error(
            f"Inconsistent Count of msgid/msgstr {file_path}: {len(msgstrs)} to {len(msgids)}"
        )
        found_error = True

    found_error = check_variable_consistency(msgids, msgstrs, file_path) or found_error
    found_error = check_empty_pairs(lineids, msgids, msgstrs, file_path) or found_error

    return found_error


def create_mo_files(force: bool, locales: set) -> list:
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
            print_warning(
                "chardet missing - falling back to polib's default encoding detection"
            )

        try:
            return polib.detect_encoding(file_path)
        except Exception as e:
            print_error(f"Error detecting encoding for {file_path}: {e}")
            return "utf-8"

    data_files = []
    po_dirs = []
    po_locales = []
    locales_lower = {loc.lower() for loc in locales}
    for locale_name in next(os.walk(LOCALE_DIR))[1]:
        po_dirs.append(f"{LOCALE_DIR}/{locale_name}/LC_MESSAGES/")
        po_locales.append(locale_name)
    counts = {
        "translated": 0,
        "ignored": 0,
        "errors": 0,
    }
    erroneous = []
    file_results = []  # Collect results for table display

    print_header("Compiling .po to .mo Files")

    for d_local, d in zip(po_locales, po_dirs):
        if locales and d_local.lower() not in locales_lower:
            print_info(f"Skipping locale {d_local}")
            file_results.append((d_local, "Skipped", "Not in selected locales"))
            continue
        print_info(f"Processing locale: {d_local}")
        mo_files = []
        po_files = [f for f in next(os.walk(d))[2] if os.path.splitext(f)[1] == ".po"]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            if find_erroneous_translations(d + po_file):
                file_results.append((d_local, "Error", f"Invalid file: {po_file}"))
                counts["errors"] += 1
                continue
            mo_file = f"{filename}.mo"
            doit = True
            status = ""
            details = ""
            if os.path.exists(d + mo_file):
                source_encoding = detect_encoding(d + po_file).lower()
                if source_encoding not in ("utf-8", "utf8"):
                    print_warning(
                        f"{d + po_file} has non-utf8 encoding ({source_encoding}), can lead to unexpected results."
                    )
                    source_encoding = "utf-8"
                target_encoding = "utf-8"  # Default target encoding
                po_date = os.path.getmtime(d + po_file)
                mo_date = os.path.getmtime(d + mo_file)
                if mo_date > po_date:
                    status = "Ignored"
                    details = f"Newer .mo exists ({source_encoding})"
                    doit = False
            if doit or force:
                empty_entries = 0
                duplicate_entries = 0
                action = "Force translating" if force and not doit else "Translating"
                status = "Translated"
                try:
                    po = polib.pofile(d + po_file, encoding=source_encoding)
                    entries_seen = set()
                    for entry in po:
                        if not entry.msgstr:
                            empty_entries += 1
                        if entry.msgid in entries_seen:
                            duplicate_entries += 1
                        entries_seen.add(entry.msgid)
                    po.save_as_mofile(d + mo_file)

                    details = f"{source_encoding} → utf-8"
                    if empty_entries > 0:
                        details += f", {empty_entries} empty"
                    if duplicate_entries > 0:
                        details += f", {duplicate_entries} dup"

                except OSError as err:
                    status = "Error"
                    details = f"Save failed: {err}"
                    counts["errors"] += 1
                    continue

                if empty_entries > 0 or duplicate_entries > 0:
                    erroneous.append(d_local)
                mo_files.append(d + mo_file)
                counts["translated"] += 1
            else:
                counts["ignored"] += 1

            if not status:  # For ignored files
                status = "Ignored"
                details = "Up to date"

            file_results.append((d_local, status, details))
        data_files.append((d, mo_files))

    # Print results in table format
    if file_results:
        print(f"{'Locale':<8} {'Status':<12} {'Details'}")
        print("-" * 60)
        for locale, status, details in file_results:
            status_color = (
                GREEN
                if status == "Translated"
                else YELLOW
                if status == "Ignored"
                else RED
                if status == "Error"
                else BLUE
            )
            print(f"{locale:<8} {status_color}{status:<12}{ENDC} {details}")
        print()

    total = counts["translated"] + counts["ignored"]
    print_header("Summary")

    # Create summary table
    summary_data = [
        ("Total files", str(total)),
        ("Translated", str(counts["translated"])),
        ("Ignored", str(counts["ignored"])),
        ("Errors", str(counts["errors"])),
        ("Warnings", str(len(erroneous))),
    ]

    print(f"{'Metric':<12} {'Count'}")
    print("-" * 20)
    for metric, count in summary_data:
        if metric == "Errors" and int(count) > 0:
            print(f"{metric:<12} {RED}{count}{ENDC}")
        elif metric == "Warnings" and int(count) > 0:
            print(f"{metric:<12} {YELLOW}{count}{ENDC}")
        else:
            print(f"{metric:<12} {count}")

    if erroneous:
        print()
        print_info(
            f"Consider running: python translate_check.py --validate {' '.join(erroneous)}"
        )
    return data_files


def integrate_delta_files(locales: set) -> None:
    """
    This code integrates translation updates from delta .po files (named delta_xx.po)
    into the main translation .po files for specified locales.
    It updates existing entries with new translations and adds new entries
    as needed, then removes the delta file.
    """
    print_header("Integrating Delta Files")

    integration_results = []

    for locale in locales:
        print_info(f"Processing locale: {locale}")
        updates_applied = False
        main_po_file = f"./locale/{locale}/LC_MESSAGES/meerk40t.po"
        delta_po_file = f"./delta_{locale}.po"

        if not os.path.exists(delta_po_file):
            integration_results.append((locale, "No Delta", "No delta file found"))
            continue
        if not os.path.exists(main_po_file):
            integration_results.append((locale, "Error", "Main .po file missing"))
            continue

        # Load main and delta .po files
        main_po = polib.pofile(main_po_file)
        delta_po = polib.pofile(delta_po_file)

        # Build dictionaries for fast lookup and to check duplicates
        main_entries = {entry.msgid: entry for entry in main_po}
        delta_entries = {}
        duplicate_msgids = set()
        empty_msgids = set()
        for entry in delta_po:
            if not entry.msgstr:
                empty_msgids.add(entry.msgid)
            elif entry.msgid in delta_entries:
                duplicate_msgids.add(entry.msgid)
            else:
                delta_entries[entry.msgid] = entry

        status = "Integrated"
        details = f"{len(delta_entries)} entries"

        if duplicate_msgids:
            print_warning(f"Duplicate msgid(s) found in delta file for {locale}:")
            for msgid in duplicate_msgids:
                print(f"  - {msgid}")
        if empty_msgids:
            print_warning(
                f"Found {len(empty_msgids)} untranslated msgid(s) in delta file for {locale}:"
            )
            # for msgid in empty_msgids:
            #     print(f"  - {msgid}")

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
            print_warning(f"Conflicting msgid(s) updated from delta for {locale}:")
            for msgid in conflicts:
                print(f"  - {msgid}")
            details += f", {len(conflicts)} conflicts"

        # Save the updated main .po file
        if updates_applied:
            main_po.save(main_po_file)
        else:
            status = "No Changes"
            details = f"{len(delta_entries)} entries (no updates needed)"

        # Remove the delta file after integration
        try:
            os.remove(delta_po_file)
        except Exception as e:
            print_error(f"Error removing {delta_po_file}: {e}")

        integration_results.append((locale, status, details))

    # Print results in table format
    if integration_results:
        print(f"{'Locale':<8} {'Status':<12} {'Details'}")
        print("-" * 60)
        for locale, status, details in integration_results:
            status_color = (
                GREEN
                if status == "Integrated"
                else BLUE
                if status == "No Changes"
                else YELLOW
                if status == "No Delta"
                else RED
            )
            print(f"{locale:<8} {status_color}{status:<12}{ENDC} {details}")
        print()


def main() -> None:
    """
    Main entry point for the script. Parses CLI arguments and triggers compilation.
    """
    parser = argparse.ArgumentParser(
        description="Check and compile MeerK40t .po translation files into .mo files."
    )
    parser.add_argument(
        "locales",
        nargs="*",
        default=[],
        help="Locale codes to process (default: all locales)",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force recompilation of all .mo files regardless of timestamps",
    )
    parser.add_argument(
        "-i",
        "--integrate",
        action="store_true",
        help="Integrate delta_xx.po files into the main .po files",
    )
    args = parser.parse_args()
    if "all" in args.locales:
        args.locales = []
    locales = set()
    if len(args.locales) == 0:
        locales.update(iter(next(os.walk(LOCALE_DIR))[1]))
        args.locales = locales
    for loc in args.locales:
        locales.add(loc)
    print_header("MeerK40t Translation Tool")
    if args.locales:
        print_info(f"Processing locales: {', '.join(sorted(locales))}")
    else:
        print_info("Processing all locales")

    if args.integrate:
        integrate_delta_files(locales)
    create_mo_files(args.force, locales)


if __name__ == "__main__":
    main()
