import os, polib

def create_mo_files():
	data_files = []
	localedir = './locale'
	po_dirs = [localedir + '/' + l + '/LC_MESSAGES/'
	for l in next(os.walk(localedir))[1]]
	for d in po_dirs:
		mo_files = []
		po_files = [f
					for f in next(os.walk(d))[2]
					if os.path.splitext(f)[1] == '.po']
		for po_file in po_files:
			filename, extension = os.path.splitext(po_file)
			mo_file = filename + '.mo'
			po = polib.pofile(d + po_file)
			po.save_as_mofile(d + mo_file)
			mo_files.append(d + mo_file)
		data_files.append((d, mo_files))
	return data_files
	
data_files=create_mo_files()
