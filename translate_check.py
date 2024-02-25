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
    ignoredirs = [".git", ".github", "venv"]
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
                                            if msgid[idx-1] != "\\":
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
    print(
        f"Read {filecount} files with {linecount} lines and found {len(id_strings_source)} entries..."
    )
    return id_strings_source, id_usage


def read_po(locale):
    id_strings = []
    localedir = "./locale"
    po_dir = localedir + "/" + locale + "/LC_MESSAGES/"
    po_files = [f for f in next(os.walk(po_dir))[2] if os.path.splitext(f)[1] == ".po"]
    linecount = 0
    for po_file in po_files:
        fname = po_dir + po_file
        with open(fname, "r", encoding="utf-8", errors="surrogateescape") as f:
            msgid_mode = False
            id_str = ""
            while True:
                linecount += 1
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line.startswith("msgid"):
                    msgid_mode = True
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
                    if msgid_mode:
                        candidate = line[1:]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            # print (f"add '{line}' -> '{candidate}'")
                            id_str += candidate
                        except IndexError:
                            print(
                                f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}"
                            )
                elif line.startswith("msgstr"):
                    msgid_mode = False
                    if id_str and id_str not in id_strings:
                        id_strings.append(id_str)
                    id_str = ""
                else:
                    pass
            if id_str and msgid_mode and id_str not in id_strings:
                id_strings.append(id_str)
    print(f"Read {linecount} lines for {locale} and found {len(id_strings)} entries...")
    return id_strings


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
                outp.write(f'msgid "{key}"\n')
                outp.write('msgstr ""\n\n')
    print(
        f"Done for {locale}: examined={counts[0]}, found={counts[1]}, new={counts[2]}"
    )


def main():
    args = sys.argv[1:]
    locale = [
        "de",
    ]
    if len(args) > 0:
        locale = args
    if locale[0].lower() == "all":
        locale = ["de", "es", "fr", "hu", "it", "ja", "nl", "pt_BR", "pt_PT", "zh"]
    print("Usage: python ./translate_check.py <locale>")
    print("<locale> one of de, es, fr, hu, it, ja, nl, pt_BR, pt_PT, zh")
    print("Reading sources...")
    id_strings_source, id_usage = read_source()
    for loc in locale:
        print(f"Checking translation strings for locale {loc}...")
        id_strings = read_po(loc)
        compare(loc, id_strings, id_strings_source, id_usage)


main()
