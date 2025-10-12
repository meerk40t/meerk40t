"""
translate_check.py

This script scans the Meerk40t source tree for translatable strings and compares them with existing translations
for the specified locale(s). It can output a delta_{locale}.po file for new strings, validate .po files, and check encoding.

Features:
    - Scans Python source files and additional_strings.txt for translatable strings
    - Compares found strings with those in locale .po files
    - Outputs delta_{locale}.po for new/untranslated strings
    - Validates .po files, removing unused, empty, or duplicate entries
    - Checks .po files for encoding issues

Usage:
    python translate_check.py <locale> [options]

Arguments:
    <locale>         Locale code(s) to process (e.g., de, fr, ja, or 'all' for all supported)
    -v, --validate   Validate .po files for the given locale(s)
    -c, --check      Check encoding of .po files for the given locale(s)
    -a, --auto       Try a translation using an online service

Supported locales:
    de, es, fr, hu, it, ja, nl, pt_BR, pt_PT, ru, zh

Some testcases:
 _("This is a test string.")
 _("Another test string with a newline.\nSee?")
 _("String with a tab.\tSee?")
 _("String with {curly} braces.")
 _("String with a quote: \"See?\"")
"""

import argparse
import os
from contextlib import suppress

import polib

# ANSI color codes for terminal output
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
BOLD = "\033[1m"
ENDC = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"{BOLD}{'=' * 60}{ENDC}")
    print(f"{BOLD}{text.center(60)}{ENDC}")
    print(f"{BOLD}{'=' * 60}{ENDC}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{BLUE}ℹ{ENDC} {text}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{GREEN}✓{ENDC} {text}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{YELLOW}⚠{ENDC} {text}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{RED}✗{ENDC} {text}")


try:
    import re

    import googletrans

    GOOGLETRANS = True
except ImportError:
    GOOGLETRANS = False

IGNORED_DIRS = [
    ".git",
    ".github",
    "venv",
    ".venv",
    "tools",
    "build",
    "dist",
    "__pycache__",
    "docs",
]
LOCALE_LONG_NAMES = {
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "hu": "Hungarian",
    "it": "Italian",
    "ja": "Japanese",
    "nl": "Dutch",
    "pt_BR": "Portuguese (Brazil)",
    "pt_PT": "Portuguese (Portugal)",
    "ru": "Russian",
    "zh": "Chinese",
}
GETTEXT_PLURAL_FORMS = {
    "de": "nplurals=2; plural=(n != 1);",
    "es": "nplurals=2; plural=(n != 1);",
    "fr": "nplurals=2; plural=(n > 1);",
    "hu": "nplurals=2; plural=(n != 1);",
    "it": "nplurals=2; plural=(n != 1);",
    "ja": "nplurals=1; plural=0;",
    "nl": "nplurals=2; plural=(n != 1);",
    "pt_BR": "nplurals=2; plural=(n > 1);",
    "pt_PT": "nplurals=2; plural=(n != 1);",
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "zh": "nplurals=1; plural=0;",
}


def lf_coded(s: str) -> str:
    """
    Converts a string to a format suitable for msgid in .po files.
    Escapes quotes and handles newlines.
    """
    if not s:
        return ""
    return (
        s.replace("\\", "\\\\")  # Escape backslashes
        .replace('"', '\\"')  # Escape double quotes
        .replace("\t", "\\t")  # Escape tab
        .replace("\n", "\\n")  # Escape newlines
        .replace("\r", "\\r")
    )  # Escape newlines


def unescape_string(s: str) -> str:
    """
    Unescapes a string that was escaped for .po files.
    This is the reverse of lf_coded.
    """
    if not s:
        return ""
    return (
        s.replace("\\\\", "\\")  # Unescape backslashes
        .replace('\\"', '"')  # Unescape double quotes
        .replace("\\t", "\t")  # Unescape tab
        .replace("\\n", "\n")  # Unescape newlines
        .replace("\\r", "\r")
    )  # Unescape carriage returns


def read_source() -> tuple[list[str], list[str]]:
    """
    Scans the source directory for translatable strings (_ ("...") ).
    Also reads additional strings from 'additional_strings.txt' if present.
    Returns:
        id_strings_source: List of unique msgid strings found in the source.
        id_usage: List of usage locations for each msgid.
    """
    id_strings_source = []
    id_usage = []
    sourcedir = "./"
    linecount = 0
    filecount = 0

    import re

    # Compile a regex pattern to match translatable strings,
    # they should not find abc_() or any other valid python
    # function name
    pattern = re.compile(r"(?<![\w])_\(")
    for root, dirs, files in os.walk(sourcedir):
        # Skip ignored directories
        if any(root.startswith(s) or root.startswith(f"./{s}") for s in IGNORED_DIRS):
            continue
        for filename in files:
            fname = os.path.join(root, filename)
            if not fname.endswith(".py"):
                continue
            pfname = os.path.normpath(fname).replace("\\", "/")
            filecount += 1
            localline = 0
            msgid_mode = False
            msgid = ""
            with open(fname, mode="r", encoding="utf-8", errors="surrogateescape") as f:
                while True:
                    linecount += 1
                    localline += 1
                    line = f.readline()
                    if not line:
                        break
                    while line:
                        line = line.strip()
                        if not line:
                            break
                        if msgid_mode:
                            # ...existing code...
                            if line.startswith(")"):
                                # ...existing code...
                                idx = 0
                                while True:
                                    idx = msgid.find('"', idx)
                                    if idx == 0:
                                        msgid = "\\" + msgid
                                        idx += 1
                                    elif idx > 0:
                                        if msgid[idx - 1] != "\\":
                                            msgid = msgid[:idx] + "\\" + msgid[idx:]
                                            idx += 1
                                    else:
                                        break
                                    idx += 1
                                if msgid not in id_strings_source:
                                    id_strings_source.append(msgid)
                                    id_usage.append(f"#: {pfname}:{localline}")
                                else:
                                    found_index = id_strings_source.index(msgid)
                                    id_usage[found_index] += f" {pfname}:{localline}"
                                msgid_mode = False
                                msgid = ""
                                idx = 0
                                line = "" if idx + 1 >= len(line) else line[idx + 1 :]
                                continue
                            elif line.startswith("+"):
                                idx = 0
                                line = "" if idx + 1 >= len(line) else line[idx + 1 :]
                                continue
                            elif line.startswith("'"):
                                quote = "'"
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\":  # escape character
                                        startidx = idx + 1
                                    else:
                                        break
                                msgid += line[1:idx]
                                line = "" if idx + 1 >= len(line) else line[idx + 1 :]
                                continue
                            elif line.startswith('"'):
                                quote = '"'
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\":  # escape character
                                        startidx = idx + 1
                                    else:
                                        break
                                msgid += line[1:idx]
                                line = "" if idx + 1 >= len(line) else line[idx + 1 :]
                                continue
                            else:
                                msgid_mode = False
                                line = ""
                                break
                        elif m := pattern.search(line):
                            msgid_mode = True
                            msgid = ""
                            line = line[m.end() :]
                        else:
                            line = ""
                            break

    # Read additional strings from file if present
    fname = "additional_strings.txt"
    if os.path.exists(fname):
        additional_new = 0
        additional_existing = 0
        po = polib.pofile(fname, encoding="utf-8")
        for e in po:
            id_str = lf_coded(e.msgid)
            if not id_str:
                continue
            if e.comment:
                last_usage = e.comment
            else:
                last_usage = " ".join(
                    [f"{o_fname}:{o_lineno}" for o_fname, o_lineno in e.occurrences]
                )
            if id_str not in id_strings_source:
                id_strings_source.append(id_str)
                id_usage.append(f"#: {last_usage}")
                additional_new += 1
            else:
                found_index = id_strings_source.index(id_str)
                id_usage[found_index] += f" {last_usage}"
                additional_existing += 1

        print(
            f"Read additional strings from 'additional_strings.txt': {additional_new} new, {additional_existing} existing"
        )
    print(
        f"Read {filecount} files with {linecount} lines and found {len(id_strings_source)} entries..."
    )
    return id_strings_source, id_usage


def read_po(locale: str) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Reads all .po files for the given locale and extracts msgid/msgstr pairs.
    Returns:
        id_strings: List of msgid strings found in the .po files.
        pairs: List of (msgid, msgstr) tuples.
    """
    id_strings = []
    pairs = []
    if locale == "en":
        # For English, we create a default .po file with no translations
        return [], []
    po_dir = f"./locale/{locale}/LC_MESSAGES/"
    if not os.path.isdir(po_dir):
        print(f"Locale directory {po_dir} does not exist or is empty.")
        return id_strings, pairs
    try:
        po_files = [
            f for f in next(os.walk(po_dir))[2] if os.path.splitext(f)[1] == ".po"
        ]
    except StopIteration:
        print(f"Locale directory {po_dir} does not exist or is empty.")
        return id_strings, pairs
    for po_file in po_files:
        fname = po_dir + po_file
        po = polib.pofile(fname, encoding="utf-8")
        id_strings.extend([lf_coded(e.msgid) for e in po])
        pairs.extend([(e.msgid, lf_coded(e.msgstr)) for e in po])

    return id_strings, pairs


def compare(
    locale: str,
    id_strings: list[str],
    id_strings_source: list[str],
    id_usage: list[str],
) -> tuple[str, str]:
    """
    Compares source msgids with those in the .po file and writes new ones to delta_{locale}.po.
    Preserves existing translations from previous delta files.
    Returns (status, details) tuple for table display.
    """
    counts = [0, 0, 0]

    # Read existing translations from old delta file if it exists
    existing_translations = {}
    delta_file = f"./delta_{locale}.po"
    if os.path.exists(delta_file):
        try:
            old_po = polib.pofile(delta_file, encoding="utf-8")
            for entry in old_po:
                if entry.msgstr and entry.msgstr.strip():
                    # Store with unescaped msgid as key so it matches what we get from source
                    existing_translations[entry.msgid] = entry.msgstr
        except Exception as e:
            print(f"Warning: Could not read existing delta file {delta_file}: {e}")

    with open(delta_file, "w", encoding="utf-8", errors="surrogateescape") as outp:
        for idx, key in enumerate(id_strings_source):
            if not key:
                continue
            counts[0] += 1
            if key in id_strings:
                counts[1] += 1
            else:
                counts[2] += 1
                outp.write(f"{id_usage[idx]}\n")
                last = ""
                lkey = ""
                for kchar in key:
                    if kchar == '"' and last != "\\":
                        lkey += "\\"  # escape the quote
                    lkey += kchar
                    last = kchar
                outp.write(f'msgid "{lkey}"\n')

                # Check if we have an existing translation for this msgid
                # We need to unescape the key from source to match what polib gives us
                unescaped_key = unescape_string(key)
                if unescaped_key in existing_translations:
                    # Use existing translation
                    msgstr = existing_translations[unescaped_key]
                    # Use the lf_coded function to properly escape the string
                    escaped_msgstr = lf_coded(msgstr)
                    outp.write(f'msgstr "{escaped_msgstr}"\n\n')
                else:
                    # No existing translation, leave empty
                    outp.write('msgstr ""\n\n')

    if counts[2] == 0:
        print_info(f"No changes for {locale}, no file created.")
        if os.path.exists(delta_file):
            os.remove(delta_file)
        return "No Changes", f"{counts[0]} strings checked"
    else:
        preserved_count = len(existing_translations)
        if preserved_count > 0:
            print_success(
                f"Found {counts[0]} total, {counts[1]} existing, {counts[2]} new for {locale}. Preserved {preserved_count} existing translations."
            )
            return "Delta Created", f"{counts[2]} new, {preserved_count} preserved"
        else:
            print_success(
                f"Found {counts[0]} total, {counts[1]} existing, {counts[2]} new for {locale}."
            )
            return "Delta Created", f"{counts[2]} new strings"


def validate_po(
    locale: str,
    id_strings_source: list[str],
    id_usage: list[str],
    id_pairs: list[tuple[str, str]],
) -> tuple[str, int, int, int, int]:
    """
    Validates .po files and returns (status, written, empty, duplicate, unused) tuple for table display.
    """
    po = polib.POFile()
    # create header
    po.metadata = {
        "Project-Id-Version": "Meerk40t",
        "Language": locale,
        "Language-Team": "Meerk40t Translation Team",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "X-Generator": "translate_check.py",
        "Plural-Forms": GETTEXT_PLURAL_FORMS.get(locale, ""),
        # Add any other metadata you need
        # …
    }
    seen = set()
    written = 0
    ignored_empty = 0
    ignored_duplicate = 0
    ignored_unused = 0
    for msgid, msgstr in id_pairs:
        t_msgid = lf_coded(msgid)
        if not msgstr or t_msgid not in id_strings_source or msgid in seen:
            if t_msgid not in id_strings_source:
                ignored_unused += 1
            elif not msgstr:
                ignored_empty += 1
            else:
                ignored_duplicate += 1
            continue
        entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
        idx = id_strings_source.index(t_msgid)
        usage = id_usage[idx]
        if usage.startswith("#: "):
            usage = usage[3:]  # Remove the leading "#: "
        if usage:
            for loc in usage.split(" "):
                if ":" in loc:
                    file = loc.split(":")[0]  # Use only the file part
                    line = loc.split(":")[1]
                else:
                    file = loc.strip()
                    line = "1"
                entry.occurrences.append((file, line))
        po.append(entry)
        seen.add(msgid)
        written += 1
    po.save(f"./fixed_{locale}_meerk40t.po")
    print_success(
        f"Validation for {locale} completed: written={written}, ignored_empty={ignored_empty}, ignored_duplicate={ignored_duplicate}, ignored_unused={ignored_unused}"
    )
    return "Validated", written, ignored_empty, ignored_duplicate, ignored_unused


def check_encoding(locales: list[str]) -> list[tuple[str, str, str]]:
    """
    Checks all .po files for the given locales for invalid encoding.
    Returns a list of (locale, status, details) tuples for table display.
    """
    results = []
    for locale in locales:
        print_info(f"Processing locale: {locale}")
        po_dir = f"./locale/{locale}/LC_MESSAGES/"
        if not os.path.isdir(po_dir):
            print_warning(f"Locale directory {po_dir} does not exist or is empty.")
            results.append((locale, "Error", "Directory not found"))
            continue
        try:
            po_files = [
                f for f in next(os.walk(po_dir))[2] if os.path.splitext(f)[1] == ".po"
            ]
        except StopIteration:
            print_warning(f"Locale directory {po_dir} does not exist or is empty.")
            results.append((locale, "Error", "Directory empty"))
            continue

        locale_status = "OK"
        locale_details = []
        for po_file in po_files:
            print_info(f"Checking encoding: {po_file}")
            source_encoding = detect_encoding(po_dir + po_file)
            if source_encoding not in ("utf-8", "utf8"):
                # Create a fixed file with utf-8 encoding
                with open(
                    po_dir + po_file,
                    "r",
                    encoding=None if source_encoding == "unknown" else source_encoding,
                ) as f:
                    content = f.read()
                # Write the content to a temporary file with utf-8 encoding
                try:
                    temp_file = f"{po_dir}temp_{po_file}"
                    with open(temp_file, "w", encoding="utf-8") as f:
                        f.write(content)
                except Exception as e:
                    print_error(
                        f"{po_dir + po_file}: Error writing temporary file, please check: {e}"
                    )
                    locale_status = "Error"
                    locale_details.append(f"{po_file}: Write error")
                    continue
                source_encoding = detect_encoding(temp_file)
                if source_encoding not in ("utf-8", "utf8"):
                    print_warning(
                        f"{po_dir + po_file}: Warning: has non-utf8 encoding ({source_encoding}), cannot fix."
                    )
                    locale_status = "Warning"
                    locale_details.append(f"{po_file}: Non-UTF8 ({source_encoding})")
                    os.remove(temp_file)
                else:
                    # Rename the temporary file to the original file name
                    try:
                        os.remove(po_dir + po_file)  # Remove the original file
                        os.rename(temp_file, po_dir + po_file)
                        print_success(
                            f"{po_dir + po_file}: Fixed encoding for {source_encoding} to utf-8."
                        )
                        locale_details.append(
                            f"{po_file}: Fixed {source_encoding}→UTF-8"
                        )
                    except Exception as e:
                        print_error(
                            f"{po_dir + po_file}: Error renaming fixed file, please check: {e}"
                        )
                        locale_status = "Error"
                        locale_details.append(f"{po_file}: Rename error")
            else:
                print_success(f"{po_dir + po_file}: OK.")
                locale_details.append(f"{po_file}: OK")
                continue

        if locale_status == "OK" and not locale_details:
            results.append((locale, "OK", "No .po files found"))
        else:
            results.append((locale, locale_status, ", ".join(locale_details)))

    return results


def detect_encoding(file_path: str) -> str:
    """
    Detects the encoding of a file.
    Returns 'utf-8' if the file is encoded in UTF-8, otherwise returns the detected encoding.
    """
    with suppress(ImportError):
        import chardet  # Ensure chardet is available for encoding detection

        result = chardet.detect(open(file_path, "rb").read())
        return result["encoding"] if result and result.get("encoding") else "unknown"

    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
        # Try to decode as UTF-8 first
        raw_data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        # If it fails, return 'unknown' or another encoding if needed
        return "unknown"


def fix_result_string(translated: str, original: str) -> str:
    """
    Fixes common issues in the translated string to better match the original formatting.
    """
    if not translated:
        return ""
    # Escape quotes, if they are not already escaped
    translated = re.sub(r'(?<!\\)"', r'\\"', translated)
    # Handle newlines
    translated = translated.replace("\n", "\\n")
    translated = translated.replace("\r", "\\r")
    # Handle tabs
    translated = translated.replace("\t", "\\t")
    # Ensure curly braces are preserved
    if "{" in original and "}" in original:
        # We replace the contents between braces with the same in the translated string
        # to avoid issues with formatting placeholders.
        for original_brace, translated_brace in zip(
            re.findall(r"\{(.*?)\}", original), re.findall(r"\{(.*?)\}", translated)
        ):
            translated = translated.replace(translated_brace, original_brace)
    # There might be erroneous double escapes added, we remove them
    translated = translated.replace("\\\\", "\\")
    return translated


def main():
    """
    Main entry point for the script.
    """

    parser = argparse.ArgumentParser(
        description="Scan and validate Meerk40t translation files."
    )
    supported_locales = ", ".join(LOCALE_LONG_NAMES.keys())
    parser.add_argument(
        "locales",
        nargs="*",
        default=["de"],
        help=f"Locales to process (or 'all' for all supported locales: {supported_locales})",
    )
    parser.add_argument(
        "-v", "--validate", action="store_true", help="Validate .po files"
    )
    parser.add_argument(
        "-c", "--check", action="store_true", help="Check encoding of .po files"
    )
    parser.add_argument(
        "-a",
        "--auto",
        action="store_true",
        help="Try translation with Google Translate API (horrible results!)",
    )
    args = parser.parse_args()

    print("Usage: python ./translate_check.py <locale>")
    print(f"<locale> one of {supported_locales}")

    # Expand 'all' to all supported locales
    locales = set()
    for loc in args.locales:
        loc = loc.lower()
        if loc == "all":
            locales = set(LOCALE_LONG_NAMES.keys())
            break
        if loc == "en":
            print(
                "English is the default language, we will create the default .po file."
            )
            locales.add("en")
            continue
        found = False
        for key in LOCALE_LONG_NAMES:
            if loc == key.lower():
                locales.add(key)
                found = True
                break
        if not found:
            print(f"Unknown locale '{loc}', using 'de' as default.")
            if "de" not in locales:
                locales.add("de")

    print_header("Meerk40t Translation Check Tool")
    print_info(f"Processing locales: {', '.join(sorted(locales))}")
    print()

    if args.check:
        print_header("Checking Encoding")
        encoding_results = check_encoding(list(locales))

        # Display results in table format
        if encoding_results:
            print(f"{'Locale':<8} {'Status':<10} {'Details'}")
            print("-" * 70)
            for locale, status, details in encoding_results:
                status_color = (
                    GREEN if status == "OK" else YELLOW if status == "Warning" else RED
                )
                print(f"{locale:<8} {status_color}{status:<10}{ENDC} {details}")
        print()
        return

    do_translate = args.auto and GOOGLETRANS
    if args.auto and not GOOGLETRANS:
        print("googletrans module not found, cannot do automatic translation.")

    print("Reading sources...")
    id_strings_source, id_usage = read_source()

    check_results = []
    is_validation = args.validate
    for loc in locales:
        print_info(
            f"Processing locale: {loc} ({LOCALE_LONG_NAMES.get(loc, 'Unknown')})"
        )
        try:
            id_strings, pairs = read_po(loc)
        except Exception as e:
            print_error(f"Error reading locale {loc}: {e}")
            if is_validation:
                check_results.append(
                    (loc, "Error", 0, 0, 0, 0)
                )  # locale, status, written, empty, duplicate, unused
            else:
                check_results.append((loc, "Error", f"Read failed: {str(e)[:50]}"))
            continue

        if args.validate:
            print_info(f"Validating locale {loc}...")
            status, written, empty, duplicate, unused = validate_po(
                loc, id_strings_source, id_usage, pairs
            )
            check_results.append((loc, status, written, empty, duplicate, unused))
        else:
            print_info(f"Checking for new translation strings for locale {loc}...")
            status, details = compare(loc, id_strings, id_strings_source, id_usage)
            check_results.append((loc, status, details))

            if do_translate and loc != "en":
                print_info(f"Trying automatic translation for locale {loc}...")
                try:
                    translator = googletrans.Translator()
                    delta_po_file = f"./delta_{loc}.po"
                    polib_file = polib.pofile(delta_po_file, encoding="utf-8")
                    id_strings = [e.msgid for e in polib_file if e.msgstr == ""]
                    for id_string in id_strings:
                        translated = translator.translate(id_string, dest=loc)
                        entry = polib_file.find(id_string)
                        if entry:
                            entry.msgstr = fix_result_string(translated.text, id_string)
                            # print (f"{translated.src} -> {translated.dest}: '{translated.origin}' -> '{translated.text}' -> '{entry.msgstr}'")
                    polib_file.save(delta_po_file)
                    print_success(
                        f"Automatic translation for locale {loc} completed. PLEASE CHECK, PROBABLY INCORRECT!"
                    )
                except Exception as e:
                    print_error(
                        f"Error during automatic translation for locale {loc}: {e}"
                    )

    # Display results in table format
    if check_results:
        print()
        print_header("Summary")
        if is_validation:
            print(f"{'Locale':<8} {'Written':<8} {'Empty':<6} {'Dup':<4} {'Unused':<7}")
            print("-" * 50)
            for result in check_results:
                if (
                    len(result) == 6
                ):  # validation result: (locale, status, written, empty, duplicate, unused)
                    locale, status, written, empty, duplicate, unused = result
                    status_color = GREEN if status == "Validated" else RED
                    print(
                        f"{locale:<8} {status_color}{written:<8}{ENDC} {empty:<6} {duplicate:<4} {unused:<7}"
                    )
                elif (
                    len(result) == 5
                ):  # error result: (locale, status, written, empty, duplicate) - missing unused
                    locale, status, written, empty, duplicate = result
                    print(
                        f"{locale:<8} {RED}{status:<8}{ENDC} {written:<6} {empty:<4} {duplicate:<7}"
                    )
                else:  # other error result
                    locale, status, error_msg = result
                    print(f"{locale:<8} {RED}{status:<8}{ENDC} {error_msg}")
        else:
            print(f"{'Locale':<8} {'Status':<14} {'Details'}")
            print("-" * 70)
            for result in check_results:
                if len(result) == 3:  # normal result
                    locale, status, details = result
                    status_color = (
                        GREEN
                        if status in ("No Changes", "Validated", "Delta Created")
                        else YELLOW
                        if status == "Warning"
                        else RED
                    )
                    print(f"{locale:<8} {status_color}{status:<14}{ENDC} {details}")
        print()


if __name__ == "__main__":
    main()
