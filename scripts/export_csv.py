# Converts the specified YAML file to an equivalent-ish CSV file
# (on standard output).
#
# python export_csv.py ../legislators-current.yaml

import sys, csv
from collections import OrderedDict

from utils import yaml_load

def run():

	if len(sys.argv) < 2:
		print("Usage: python export_csv.py ../legislators-current.yaml > legislators-current.csv")
		sys.exit(0)

	data = yaml_load(sys.argv[1])

	###############################################

	def flatten_object(obj, path, ret):
		"""Takes an object obj and flattens it into a dictionary ret.

		For instance { "x": { "y": 123 } } is turned into { "x__y": 123 }.
		"""
		for k, v in list(obj.items()):
			if isinstance(v, dict):
				flatten_object(v, (path + "__" if path else "") + k + "__", ret)
			elif isinstance(v, list):
				# don't peek inside lists
				pass
			else:
				ret[path + k] = v
		return ret

	# Scan through the records recursively to get a list of column names.
	# Attempt to preserve the field order as found in the YAML file. Since
	# any field may be absent, no one record can provide the complete field
	# order. Build the best field order by looking at what each field tends
	# to be preceded by.
	fields = set()
	preceding_keys = dict() # maps keys to a dict of *previous* keys and how often they occurred
	for record in data:
		prev_key = None
		for key in flatten_object(record, "", OrderedDict()):
			fields.add(key)

			preceding_keys.setdefault(key, {}).setdefault(prev_key, 0)
			preceding_keys[key][prev_key] += 1
			prev_key = key

	# Convert to relative frequencies.
	for k, v in list(preceding_keys.items()):
		s = float(sum(v.values()))
		for k2 in v:
			v[k2] /= s

	# Get a good order for the fields. Greedily add keys from left to right
	# maximizing the conditional probability that the preceding key would
	# precede the key on the right.
	field_order = [None]
	prev_key = None
	while len(field_order) < len(fields):
		# Which key is such that prev_key is its most likely precedessor?
		# We do it this way (and not what is prev_key's most likely follower)
		# because we should be using a probability (of sorts) that is
		# conditional on the key being present. Otherwise we lost infrequent
		# keys.
		next_key = max([f for f in fields if f not in field_order], key =
			lambda k :
				max(preceding_keys[k].get(pk, 0) for pk in field_order))
		field_order.append(next_key)
		prev_key = next_key
	field_order = field_order[1:] # remove the None at the start

	# Write CSV header.
	w = csv.writer(sys.stdout)
	w.writerow(field_order)

	# Write the objects.
	for record in data:
		obj = flatten_object(record, "", {})
		w.writerow([
			obj.get(f, "")
			for f in field_order
			])

if __name__ == '__main__':
  run()