# Converts the specified YAML file to an equivalent-ish CSV file
# (on standard output).
#
# python export_csv.py ../legislators-current.yaml

import sys, csv

from utils import yaml_load

if len(sys.argv) < 2:
	print "Usage: python export_csv.py ../legislators-current.yaml > legislators-current.csv"
	sys.exit(0)

data = yaml_load(sys.argv[1])

###############################################

def flatten_object(obj, path, ret):
	"""Takes an object obj and flattens it into a dictionary ret.

	For instance { "x": { "y": 123 } } is turned into { "x__y": 123 }.
	"""
	for k, v in obj.items():
		if isinstance(v, dict):
			flatten_object(v, (path + "__" if path else "") + k + "__", ret)
		elif isinstance(v, list):
			# don't peek inside lists
			pass
		else:
			ret[path + k] = v
	return ret

# Scan through the records recursively to get a list of column names.
fields = set()
for record in data:
	for key in flatten_object(record, "", {}):
		fields.add(key)

# Map column indexes to key names.
fields = sorted(fields)

# Write CSV header.
w = csv.writer(sys.stdout)
w.writerow(fields)

# Write the objects.
for record in data:
	obj = flatten_object(record, "", {})
	w.writerow([
		unicode(obj.get(f, "")).encode("utf8")
		for f in fields
		])