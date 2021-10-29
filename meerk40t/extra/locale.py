import re
import sys
import glob

"""
Locale is an internal standalone plugin to facilitate translations. This works by scanning the source files for 
translatable strings and the .po files for translations, and providing differences.
"""


def plugin(kernel, lifecycle):
    if getattr(sys, "frozen", False):
        # This plugin is source only.
        return
    if lifecycle == "register":
        context = kernel.root
        _ = kernel.translation

        @context.console_command(
            "locale", output_type="locale", hidden=True
        )
        def locale(channel, _, **kwargs):
            return "locale", "en"

        @context.console_command(
            "generate", input_type="locale", output_type="locale", hidden=True
        )
        def generate_locale(channel, _, data=None, **kwargs):
            translate = _
            for python_file in glob.glob("meerk40t/**/*.py", recursive=True):
                channel(python_file)
                file = open(python_file, "r", encoding="utf-8").read()
                search = re.compile("_\([\"\']([^\"\']*)[\"\']\)")
                # TODO: Will not find multilined.
                for m in search.findall(file):
                    translation = translate(m)
                    if m == translation:
                        channel("No Translation: %s" % m)
                    else:
                        channel("%s -> %s" % (m, translation))

            return "locale", data

        @context.console_argument("locale", help="locale use for these opeations")
        @context.console_command(
            "change", input_type="locale", output_type="locale", hidden=True
        )
        def change_locale(channel, _, data=None, locale=None, **kwargs):
            if locale is None:
                raise SyntaxError
            channel("locale changed from %s to %s" % (data, locale))
            return "locale", locale

        @context.console_command(
            "update", input_type="locale", hidden=True
        )
        def update_locale(channel, _, data=None, **kwargs):
            """
            This script updates the message.po structure with the original translation information.

            @param channel:
            @param _:
            @param data:
            @param kwargs:
            @return:
            """
            if data == "en":
                channel("Cannot update English since it is the default language and has no file")
            keys = dict()
            translations = open("./locale/%s/LC_MESSAGES/meerk40t.po" % data, "r", encoding="utf-8")

            file_lines = translations.readlines()
            key = None
            index = 0
            translation_header = []
            while index < len(file_lines):
                # Header is defined as the first batch of uninterrupted lines in the file.
                try:
                    if file_lines[index]:
                        translation_header.append(file_lines[index])
                    else:
                        break
                    index += 1
                except IndexError:
                    break

            while index < len(file_lines):
                try:
                    # Find msgid and all multi-lined message ids
                    if re.match("msgid \"(.*)\"", file_lines[index]):
                        m = re.match("msgid \"(.*)\"", file_lines[index])
                        key = m.group(1)
                        index += 1
                        if index >= len(file_lines):
                            break
                        while re.match("^\"(.*)\"$", file_lines[index]):
                            m = re.match("^\"(.*)\"$", file_lines[index])
                            key += m.group(1)
                            index += 1

                    # find all message strings and all multi-line message strings
                    if re.match("msgstr \"(.*)\"", file_lines[index]):
                        m = re.match("msgstr \"(.*)\"", file_lines[index])
                        value = [file_lines[index]]
                        if len(key) > 0:
                            keys[key] = value
                        index += 1
                        while re.match("^\"(.*)\"$", file_lines[index]):
                            value.append(file_lines[index])
                            if len(key) > 0:
                                keys[key] = value
                            index += 1
                    index += 1
                except IndexError:
                    break

            template = open("./locale/messages.po", "r", encoding="utf-8")
            lines = []

            file_lines = list(template.readlines())
            index = 0
            template_header = []
            while index < len(file_lines):
                # Header is defined as the first batch of uninterrupted lines in the file.
                # We read the template header but do not use them.
                try:
                    if file_lines[index]:
                        template_header.append(file_lines[index])
                    else:
                        break
                    index += 1
                except IndexError:
                    break

            # Lines begins with the translation's header information.
            lines.extend(translation_header)
            while index < len(file_lines):
                try:
                    # Attempt to locate message id
                    if re.match("msgid \"(.*)\"", file_lines[index]):
                        lines.append(file_lines[index])
                        m = re.match("msgid \"(.*)\"", file_lines[index])
                        key = m.group(1)
                        index += 1
                        while re.match("^\"(.*)\"$", file_lines[index]):
                            lines.append(file_lines[index])
                            key += m.group(1)
                            index += 1
                except IndexError:
                    pass
                try:
                    # Attempt to locate message string
                    if re.match("msgstr \"(.*)\"", file_lines[index]):
                        if key in keys:
                            lines.extend(keys[key])
                            index += 1
                            while re.match("^\"(.*)\"$", file_lines[index]):
                                index += 1
                        else:
                            lines.append(file_lines[index])
                            index += 1
                            while re.match("^\"(.*)\"$", file_lines[index]):
                                lines.append(file_lines[index])
                                index += 1
                except IndexError:
                    pass
                try:
                    # We append any line if it wasn't fully read by msgid and msgstr readers.
                    lines.append(file_lines[index])
                    index += 1
                except IndexError:
                    break

            filename = "meerk40t.update"
            channel("writing %s" % filename)
            import codecs
            template = codecs.open(filename, "w", "utf8")
            template.writelines(lines)
