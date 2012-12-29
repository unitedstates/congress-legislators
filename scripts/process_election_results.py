#!/usr/bin/env python

# Add newly elected Members of Congress for the 113th Congress,
# and add new terms to Members of Congress that were reelected.

import csv, datetime
from collections import OrderedDict
from utils import load_data, save_data

senate_election_class = 1
at_large_districts = ['AK', 'AS', 'DC', 'DE', 'GU', 'MP', 'MT', 'ND', 'PR', 'SD', 'VI', 'VT', 'WY']

y = load_data("legislators-current.yaml")
y_historical = load_data("legislators-historical.yaml")

# Map GovTrack IDs to dicts. Track whether they are in the current or historical file.
by_id = { }
for m in y: by_id[m["id"]["govtrack"]] = (m, True)
for m in y_historical: by_id[m["id"]["govtrack"]] = (m, False)

# Process each election winner.
seen_members = set()
for rec in csv.DictReader(open("election_results_2012.csv")):
	if rec["id"].strip() != "":
		# This is the reelection of someone that has already served in Congress.
		m, is_current = by_id[int(rec["id"])]
		seen_members.add(int(rec["id"]))

		if not is_current:
			# If this person is in the historical file, move them into the current file.
			if rec["incumbent"].strip() == "1": raise ValueError("Incumbent %d is in the historical file?!" % int(rec["id"]))
			y_historical.remove(m)
			y.append(m)
			
		else:
			# This person is in the current file. They must be continuing from a term that ends at the end.
			if m["terms"][-1]["end"] != '2012-12-31':
				raise ValueError("Most recent term doesn't end on December 31 of this year: %d" % int(rec["id"]))
			
	else:
		# This is a new individual. Create a new record for them.
		
		if rec["incumbent"].strip() == "1": raise ValueError("Incumbent does not have a govtrack ID?!")
		
		m = OrderedDict([
			("id", {}),
			("name", OrderedDict([
				("first", rec["first"]),
				("last", rec["last"]),
				])),
			("bio", {}),
			("terms", []),
		])
		for k in ('suffix', 'middle'):
			if rec[k].strip() != "":
				m["name"][k] = rec[k].strip()
			
		y.append(m)
			
	# Create a new term for this individual.
	
	term =  OrderedDict([
		("type", "sen" if int(rec["seat"]) == 0 else "rep"),
		("start", "2013-01-03"),
		("end", "2018-12-31" if int(rec["seat"]) == 0 else "2014-12-31"),
		("state", rec["state"]),
		("party", rec["party"]),
	])
	
	if int(rec["seat"]) == 0:
		term["class"] = senate_election_class
	else:
		d = int(rec["seat"])
		if rec["state"] in at_large_districts: d = 0 # it's coded in the file as 1, but we code as 0
		term["district"] = d
		
	# For incumbents, assume url, address, and similar fields are not changing.
	# Pull them forward from the individual's most recent term, which is always listed last.
	if len(m["terms"]) > 0:
		for field in ("url", "address", "phone", "fax", "contact_form", "office"):
			if field in m["terms"][-1]: term[field] = m["terms"][-1][field]

	# Append the new term.
	m["terms"].append(term)
	
# Move incumbents that are not in the election results to the historical file.
for m in y:
	# skip senators not in the election class for this year
	if m["terms"][-1]["type"] == "sen" and m["terms"][-1]["class"] != senate_election_class:
		continue
	
	# skip IDs present in the seen_members set, which is re-elected incumbents
	if m.get('id', {}).get('govtrack') in seen_members:
		continue
		
	y.remove(m)
	y_historical.append(m)

save_data(y, "legislators-current.yaml")
save_data(y_historical, "legislators-historical.yaml")
