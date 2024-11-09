import os
import re


def are_curly_brackets_matched(input_str):
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


def find_erroneous_translations(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
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
                if re.match('msgid \s*"(.*)"', file_lines[index]):
                    m = re.match('msgid \s*"(.*)"', file_lines[index])
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
        print (f"{erct} empty pair{'s' if erct==0 else ''} msgid '' + msgstr '' found in {file_path}\n{','.join(er_s)}")
        found_error = True
    return found_error


def find_po_files(directory="."):
    found_error = False
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".po") and not file.startswith("delta"):
                file_path = os.path.join(root, file)
                if find_erroneous_translations(file_path):
                    found_error = True
    if found_error:
        exit(1)


if __name__ == "__main__":
    find_po_files()
    print("No erroneous translations found.")
