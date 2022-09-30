import os

import polib


# Simple tool to recursively translate all .po-files into their .mo-equivalents under ./locale/LC_MESSAGES
def create_mo_files():
    data_files = []
    localedir = "./locale"
    po_dirs = [
        localedir + "/" + l + "/LC_MESSAGES/" for l in next(os.walk(localedir))[1]
    ]
    counts = [0, 0, 0]
    for d in po_dirs:
        mo_files = []
        po_files = [f for f in next(os.walk(d))[2] if os.path.splitext(f)[1] == ".po"]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            mo_file = filename + ".mo"
            doit = True
            if os.path.exists(d + mo_file):
                po_date = os.path.getmtime(d + po_file)
                mo_date = os.path.getmtime(d + mo_file)
                if mo_date > po_date:
                    print("mo-File for " + d + po_file + " is newer, so skip it...")
                    doit = False
            if doit:
                print("Translate " + d + po_file)
                try:
                    po = polib.pofile(d + po_file)
                    po.save_as_mofile(d + mo_file)
                except IOError as err:
                    print(f"Unexpected {err=}")
                    counts[2] += 1
                    continue

                mo_files.append(d + mo_file)
                counts[0] += 1
            else:
                counts[1] += 1
        data_files.append((d, mo_files))
    print (f"Total: {counts[0] + counts[1]}, Translated: {counts[0]}, Ignored: {counts[1]}, Errors: {counts[2]}")
    return data_files


create_mo_files()
