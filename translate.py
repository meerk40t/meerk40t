import os
import sys
import polib


# Simple tool to recursively translate all .po-files into their .mo-equivalents under ./locale/LC_MESSAGES
def create_mo_files(force:bool, locales:list):
    data_files = []
    localedir = "./locale"
    po_dirs = []
    po_locales = []
    for l in next(os.walk(localedir))[1]:
        po_dirs.append(localedir + "/" + l + "/LC_MESSAGES/")
        po_locales.append(l)
    counts = [0, 0, 0]
    for d_local, d in zip(po_locales, po_dirs):
        if len(locales) > 0 and d_local not in locales:
            print (f"Skip locale {d_local}")
            continue
        mo_files = []
        po_files = [f for f in next(os.walk(d))[2] if os.path.splitext(f)[1] == ".po"]
        for po_file in po_files:
            filename, extension = os.path.splitext(po_file)
            mo_file = filename + ".mo"
            doit = True
            if os.path.exists(d + mo_file):
                res = polib.detect_encoding(d + mo_file)
                po_date = os.path.getmtime(d + po_file)
                mo_date = os.path.getmtime(d + mo_file)
                if mo_date > po_date:
                    print(f"mo-File for {d}{po_file} is newer (enoded: {res})...")
                    doit = False
            if doit or force:
                if doit:
                    action = "Translate"
                else:
                    action = "Forced translate"
                res = polib.detect_encoding(d + po_file)
                print(f"{action} {d}{po_file} (encoded={res})")
                try:
                    po = polib.pofile(d + po_file)
                    po.save_as_mofile(d + mo_file)
                except OSError as err:
                    print(f"Unexpected {err=}")
                    counts[2] += 1
                    continue

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
    force = False
    args = sys.argv[1:]
    locales = []
    if len(args) > 0:
        locales = list(a for a in args)
        if locales[0].lower() == "force":
            force = True
            locales.pop(0)
    print("Usage: python ./translate.py <locales>")
    if len(locales):
        print(f"Will compile po-files for {','.join(locales)}")
    else:
        print("Will compile all po-files")
    create_mo_files(force, locales)

main()