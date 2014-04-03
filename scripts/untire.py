#!/usr/bin/env python

# "Un-retire" a Member of Congress: Move a Member of Congress
# from the legislators-historical file to the legislators-current file
# and give the Member a new term.
#
# python unretire.py bioguideID

import sys

from utils import load_data, save_data, pprint
from collections import OrderedDict

def run():

	if len(sys.argv) != 2:
		print("Usage:")
		print("python untire.py bioguideID")
		sys.exit()

	print("Loading current YAML...")
	y = load_data("legislators-current.yaml")
	print("Loading historical YAML...")
	y1 = load_data("legislators-historical.yaml")

	for moc in y1:
		if moc["id"].get("bioguide", None) != sys.argv[1]: continue

		print("Updating:")
		pprint(moc["id"])
		print()
		pprint(moc["name"])

		moc["terms"].append(OrderedDict([
			("type", moc["terms"][-1]["type"]),
			("start", None),
			("end", None),
			("state", moc["terms"][-1]["state"]),
			("party", moc["terms"][-1]["party"]),
		]))

		y1.remove(moc)
		y.append(moc)

		break

	print("Saving changes...")
	save_data(y, "legislators-current.yaml")
	save_data(y1, "legislators-historical.yaml")

if __name__ == '__main__':
  run()