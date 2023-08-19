import os
import re

id_strings = []
id_strings_source = []

def read_source():
    global id_strings_source
    msgid_mode = False
    msgid = ""

    id_strings_source = []
    sourcedir = "./meerk40t"
    linecount = 0
    filecount = 0
    for root, dirs, files in os.walk(sourcedir):
        for filename in files:
            fname = os.path.join(root, filename)
            if not fname.endswith(".py"):
                continue
            with open(fname, mode="r", encoding="utf8", errors="surrogateescape") as f:
                filecount += 1
                msgid_mode = False
                msgid = ""
                while True:
                    linecount += 1
                    line = f.readline()
                    if not line:
                        break
                    orgline = line
                    while line:
                        line = line.strip()
                        if not line:
                            break
                        if msgid_mode:
                            if line.startswith(")"):
                                if msgid:
                                    if msgid not in id_strings_source:
                                        id_strings_source.append(msgid)
                                    # print (f"'{orgline}' -> '{msgid}'")
                                msgid_mode = False
                                msgid = ""
                                idx = 0
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1:]
                                continue
                            elif line.startswith("+"):
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1:]
                                continue
                            elif line.startswith("'"):
                                quote= "'"
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        # strange
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\": # escape character
                                        startidx = idx + 1
                                    else:
                                        # All good
                                        break
                                msgid += line[1:idx]
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1:]
                                continue
                            elif line.startswith('"'):
                                quote= '"'
                                startidx = 1
                                while True:
                                    idx = line.find(quote, startidx)
                                    if idx < 0:
                                        # strange
                                        msgid_mode = False
                                        line = ""
                                        break
                                    if line[idx - 1] == "\\": # escape character
                                        startidx = idx + 1
                                    else:
                                        # All good
                                        break
                                msgid += line[1:idx]
                                if idx + 1 >= len(line):
                                    line = ""
                                else:
                                    line = line[idx + 1:]
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
                                line = line[idx+2:]
                            else:
                                # Nothing to be done here in this line
                                line = ""
                                break

        # for dirname in dirs:
        #     dname = os.path.join(root, dirname))
    print (f"Read {filecount} files with {linecount} lines and found {len(id_strings_source)} entries...")

def read_po(locale):
    global id_strings
    id_strings = []
    localedir = "./locale"
    po_dir = localedir + "/" + locale + "/LC_MESSAGES/"
    po_files = [f for f in next(os.walk(po_dir))[2] if os.path.splitext(f)[1] == ".po"]
    linecount = 0
    for po_file in po_files:
        fname = po_dir + po_file
        with open(fname, "r") as f:
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
                        candidate = line[idx + 1:]
                        try:
                            idx = -1
                            while candidate[idx] != '"':
                                idx -= 1
                            candidate = candidate[:idx]
                            id_str += candidate
                        except IndexError:
                            print (f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}")

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
                            print (f"Stumbled across: '{line}', candidate:'{candidate}', idx={idx}")
                elif line.startswith("msgstr"):
                    msgid_mode = False
                    if id_str and id_str not in id_strings:
                        id_strings.append(id_str)
                    id_str = ""
                else:
                    pass
            if id_str and msgid_mode and id_str not in id_strings:
                id_strings.append(id_str)
    print (f"Read {linecount} lines and found {len(id_strings)} entries...")

def compare():
    global id_strings
    global id_strings_source
    counts = [0, 0, 0]
    with open("./delta.po", "w") as outp:
        for key in id_strings_source:
            counts[0] += 1
            if key in id_strings:
                counts[1] += 1
            else:
                counts[2] += 1
                outp.write(f'msgid "{key}"\n')
                outp.write('msgstr ""\n\n')
    print (f"Done: examined={counts[0]}, found={counts[1]}, new={counts[2]}")


read_source()
read_po("de")
compare()