#!/usr/bin/env python

# Retire a Member of Congress. Updates the end date of the
# Member's most recent term and moves him/her from the
# current file to the historical file.
#
# python retire.py bioguideID termEndDate

import sys

from utils import load_data, save_data, parse_date, pprint

def run():
	if len(sys.argv) != 3:
		print("Usage:")
		print("python retire.py bioguideID termEndDate")
		sys.exit()

	try:
		parse_date(sys.argv[2])
	except:
		print("Invalid date: ", sys.argv[2])
		sys.exit()

	print("Loading current YAML...")
	y = load_data("legislators-current.yaml")
	print("Loading historical YAML...")
	y1 = load_data("legislators-historical.yaml")

	for moc in y:
		if moc["id"].get("bioguide", None) != sys.argv[1]: continue

		print("Updating:")
		pprint(moc["id"])
		print()
		pprint(moc["name"])
		print()
		pprint(moc["terms"][-1])

		moc["terms"][-1]["end"] = sys.argv[2]

		y.remove(moc)
		y1.append(moc)

		break

	print("Saving changes...")
	save_data(y, "legislators-current.yaml")
	save_data(y1, "legislators-historical.yaml")

if __name__ == '__main__':
  run()