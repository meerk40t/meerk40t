"""
This module scans the complete source tree and looks for candidates
to be translated and compares this with the existing translation of
a given locale. It creates then a delta_{locale}.po file for review
and integration into the translation file.

poboy does something similar (and even better when recognising
strings), but that comes at a cost, as it will at the same time
discard translated but non-used msgid/msgstr pairs. This is not
always the intended behaviour.

You are supposed to call this tool from the command line
specifying the locale as a parameter, e.g.:
    python ./translate_check.py zh
"""

import os
import sys

# def testroutine():
#     _ = print
#     msg = _("Test for a '") + "-" + _('another test for "')
#     msg = _(
#         "part 1" +
#         "part2"
#         + "part3"
#     )


def read_source():
    id_strings_source = []
    id_usage = []
    # sourcedir = "./meerk40t"
    sourcedir = "./"
    linecount = 0
    filecount = 0
    # debugit = False
    ignoredirs = [".git", ".github", "venv", ".venv"]
    for root, dirs, files in os.walk(sourcedir):
        mayignore = False
        for s in ignoredirs:
            if root.startswith(s) or root.startswith("./" + s):
                mayignore = True
                break
        if mayignore:
            continue
        for filename in files:
            fname = os.path.join(root, filename)
            if not fname.endswith(".py"):
                continue
            # debugit = fname.endswith("translate_check.py")
            with open(fname, mode="r", encoding="utf-8", errors="surrogateescape") as f:
                pfname = os.path.normpath(fname).replace("\\", "/")
                filecount += 1
                localline = 0
                msgid_mode = False
                msgid = ""
                while True:
                    linecount += 1
                    localline += 1
                    line = f.readline()
                    if not line:
                        break
                    while line:
                        line = line.strip()
                        # if debugit:
                        #     print (f"[{msgid_mode}, '{msgid}']: '{line}'")
                        if not line:
                            break
                        if msgid_mode:
                            if line.startswith(")"):
                                if msgid:
                                    #
                                    idx = 0
                                    while True:
                                        idx = msgid.find('"', idx)
                                        if idx == 0:
                                            # Starts with a '"'
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
                                        id_usage[
                                            found_index
                                        ] += f" {pfname}:{localline}"
                                    # print (f"'{orgline}' -> '{msgid}'")
                                msgid_mode = False
                                msgid = ""
                                idx = 0
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1 :]
                                continue
                            elif line.startswith("+"):
                                idx = 0
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1 :]
                                continue
                            elif line.startswith("'"):
                                quote = "'"
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        # strange
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\":  # escape character
                                        startidx = idx + 1
                                    else:
                                        # All good
                                        break
                                msgid += line[1:idx]
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1 :]
                                continue
                            elif line.startswith('"'):
                                quote = '"'
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        # strange
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\":  # escape character
                                        startidx = idx + 1
                                    else:
                                        # All good
                                        break
                                msgid += line[1:idx]
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1 :]
                                continue
                            else:
                                # strange
                                msgid_mode = False
                                line = ""
                                break
                        else:
                            # Fine so we need to look for '_('
                            idx = line.find("_(")
                            if idx >= 0:
                                msgid_mode = True
                                msgid = ""
                                line = line[idx + 2 :]
                            else:
                                # Nothing to be done here in this line
                                line = ""
                                break

        # for dirname in dirs:
        #     dname = os.path.join(root, dirname))
    if os.path.exists("additional_strings.txt"):
        additional_new = 0
        additional_existing = 0

        with open("additional_strings.txt", "r", encoding="utf-8") as f:
            last_usage = ""
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#: "):
                    last_usage = line[3:].strip()
                    continue
                if line.startswith("msgid "):
                    id_str = ""
                    idx = line.find('"')
                    if idx >= 0:
                        candidate = line[idx + 1 :]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            id_str += candidate
                        except IndexError:
                            print(
                                f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}"
                            )

                        # print (f"start '{line}' -> '{candidate}'")
                    if not id_str:
                        print(
                            f"Stumbled across: '{line}', no id_str found, skipping this line."
                        )
                        continue
                    print(f"Checking additional string: '{id_str}'")
                    if id_str not in id_strings_source:
                        id_strings_source.append(id_str)
                        id_usage.append(last_usage)
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


def read_po(locale):
    id_strings = []
    pairs = []
    localedir = "./locale"
    po_dir = localedir + "/" + locale + "/LC_MESSAGES/"
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
    linecount = 0
    for po_file in po_files:
        fname = po_dir + po_file
        with open(fname, "r", encoding="utf-8", errors="surrogateescape") as f:
            msgid_mode = False
            msgstr_mode = False
            id_str = ""
            msg_str = ""
            while True:
                linecount += 1
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("msgid"):
                    if msg_str:
                        if pairs:
                            pairs[-1] = (pairs[-1][0], msg_str)
                        msg_str = ""
                    msgid_mode = True
                    msgstr_mode = False
                    id_str = ""
                    idx = line.find('"')
                    if idx >= 0:
                        candidate = line[idx + 1 :]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            id_str += candidate
                        except IndexError:
                            print(
                                f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}"
                            )

                        # print (f"start '{line}' -> '{candidate}'")
                elif line.startswith('"'):
                    if msgid_mode or msgstr_mode:
                        candidate = line[1:]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            # print (f"add '{line}' -> '{candidate}'")
                            if msgid_mode:
                                id_str += candidate
                            elif msgstr_mode:
                                msg_str += candidate
                        except IndexError:
                            print(
                                f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}"
                            )
                elif line.startswith("msgstr"):
                    if id_str:
                        if id_str not in id_strings:
                            id_strings.append(id_str)
                        pairs.append((id_str, ""))
                    id_str = ""
                    msgid_mode = False
                    msgstr_mode = True
                    msg_str = ""
                    idx = line.find('"')
                    if idx >= 0:
                        candidate = line[idx + 1 :]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            msg_str += candidate
                        except IndexError:
                            print(
                                f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}"
                            )

                else:
                    pass
            if id_str:
                if id_str not in id_strings:
                    id_strings.append(id_str)
                pairs.append((id_str, msg_str))
                id_str = ""
            elif msg_str:
                if pairs:
                    pairs[-1] = (pairs[-1][0], msg_str)
                msg_str = ""
    print(
        f"Read {linecount} lines for {locale} and found {len(id_strings)} entries... (pairs: {len(pairs)})"
    )
    return id_strings, pairs


def compare(locale, id_strings, id_strings_source, id_usage):
    counts = [0, 0, 0]
    with open(f"./delta_{locale}.po", "w", encoding="utf-8") as outp:
        for idx, key in enumerate(id_strings_source):
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
                outp.write('msgstr ""\n\n')
    print(
        f"Done for {locale}: examined={counts[0]}, found={counts[1]}, new={counts[2]}"
    )


def validate_po(locale, id_strings_source, id_usage, id_pairs):
    def write_proper_po_header(outp, locale):
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
        outp.write(
            f"# {LOCALE_LONG_NAMES.get(locale, 'Unknown')} translation for Meerk40t\n"
        )
        outp.write("# Project-Homepage: https://github.com/meerk40t/meerk40t\n")
        outp.write('msgid ""\n')
        outp.write('msgstr ""\n')
        outp.write('"Project-Id-Version: Meerk40t"\n')
        outp.write('"Content-Type: text/plain; charset=UTF-8"\n')
        outp.write('"Content-Transfer-Encoding: 8bit"\n')
        outp.write('"Language-Team: Meerk40t Translation Team"\n')
        outp.write(f'"Language: {locale}"\n')
        outp.write('"X-Generator: translate_check.py"\n')
        plur = GETTEXT_PLURAL_FORMS.get(locale, "")
        if plur:
            outp.write(f'"Plural-Forms: {plur}"\n')
        outp.write("\n")

    # Write a new file with the same name as the locale
    written = 0
    ignored_empty = 0
    ignored_duplicate = 0
    ignored_unused = 0
    pairs = {}
    for msgid, msgstr in id_pairs:
        if msgid not in pairs:
            pairs[msgid] = []
        pairs[msgid].append(msgstr)
    with open(f"./fixed_{locale}_meerk40t.po", "w", encoding="utf-8") as outp:
        write_proper_po_header(outp, locale)
        for msgid, msgstr_list in pairs.items():
            msgstr = ""
            for m in msgstr_list:
                if m:
                    msgstr = m
                    break
            to_write = True
            if len(msgstr_list) > 1:
                ignored_duplicate += len(msgstr_list) - 1
            if msgstr == "":
                ignored_empty += 1
                to_write = False
            if msgid not in id_strings_source:
                ignored_unused += 1
                to_write = False
            if to_write:
                orgidx = id_strings_source.index(msgid)
                if orgidx < 0:
                    ignored_unused += 1
                    continue

                outp.write(f"{id_usage[orgidx]}\n")
                outp.write(f'msgid "{msgid}"\n')
                outp.write(f'msgstr "{msgstr}"\n\n')
                written += 1
    print(
        f"Validation for {locale} done: written={written}, ignored_empty={ignored_empty}, ignored_duplicate={ignored_duplicate}, ignored_unused={ignored_unused}"
    )


def main():
    args = sys.argv[1:]
    locale = [
        "de",
    ]
    if len(args) > 0:
        locale = args
    if locale[0].lower() == "all":
        locale = [
            "de",
            "es",
            "fr",
            "hu",
            "it",
            "ja",
            "nl",
            "pt_BR",
            "pt_PT",
            "ru",
            "zh",
        ]
    validate = False
    if "-v" in args or "--validate" in args:
        validate = True
        idx = locale.index("-v") if "-v" in locale else locale.index("--validate")
        locale.pop(idx)

    print("Usage: python ./translate_check.py <locale>")
    print("<locale> one of de, es, fr, hu, it, ja, nl, pt_BR, pt_PT, ru, zh")
    print("Reading sources...")
    id_strings_source, id_usage = read_source()
    for loc in locale:
        id_strings, pairs = read_po(loc)
        if validate:
            print(f"Validating locale {loc}...")
            validate_po(loc, id_strings_source, id_usage, pairs)
        else:
            print(f"Checking for new translation strings for locale {loc}...")
            compare(loc, id_strings, id_strings_source, id_usage)


main()
