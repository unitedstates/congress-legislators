# Temporary script to help us get the data in shape
# for the 114th Congress.

# Get: (thanks Derek!)
#   https://docs.google.com/spreadsheets/d/1H8z7Ah4jSlXiuIol3oXoWBR8s6h0OtA62dNlU-kiIlU/edit#gid=1419747559
# and download as 'election_results_2014.csv'.

# TODO:
# * What is the expected first day of the Congress? (Closest guess of swearing-in dates.)
# * Am adding "TODO: TODO" to new terms that weren't copied from older terms. Needs checking, possibly additional details like url, contact form.

from collections import OrderedDict
import copy
import csv
import rtyaml

import utils

# Which members were up for relection, won in their office, or were
# a winner in another office?
won_row = { }
incumbents = set()
winners = set()
incumbent_winners = set()
for row in csv.DictReader(open("election_results_2014.csv")):
	if row.get("new_member") == "":
		print("not decided yet...", row)
		continue
	incumbents.add(row.get("member_id"))
	winners.add(row.get("new_id"))
	won_row[row.get("new_id")] = row
	if row.get("member_id") == row.get("new_id"):
		incumbent_winners.add(row.get("new_id"))

# Make a stub term based on a row in Derek's spreadsheet.
def build_term(row, mark):
	if row['chamber'] == 'House':
		end_date = '2017-01-03'
	elif row['district'] == 'Class II':
		end_date = '2021-01-03'
	elif row['district'] == 'Class III':
		end_date = '2017-01-03'
	else:
		raise ValueError()

	ret = OrderedDict([
		("type", "rep" if row['chamber'] == 'House' else 'sen'),
		("start", '2015-01-03'),
		("end", end_date),
		("state", row['state_abbrev']),
	])

	if ret["type"] == "rep":
		ret["district"] = int(row['district']) if row['district'] != "AL" else 0
	else:
		if row["district"] == "Class II":
			ret["class"] = 2
		elif row["district"] == "Class III":
			ret["class"] = 3
		else:
			raise ValueError()
		if mark:
			ret["state_rank"] = "junior"

	if row["winner_party"] == "D":
		ret["party"] = "Democrat"
	elif row["winner_party"] == "R":
		ret["party"] = "Republican"
	else:
		raise ValueError()

	if mark:
		ret["TODO"] = "TODO"

	return ret

# Load legislators.
legislators_current = utils.load_data("legislators-current.yaml")
legislators_historical = utils.load_data("legislators-historical.yaml")

# Sweep current members.
to_retire = []
for p in legislators_current:
	id = p['id']['bioguide']
	if id in incumbents:
		# This legislator was up for reelection.
		if id in incumbent_winners:
			# And won. Extend the term.
			t = copy.deepcopy(p['terms'][-1])
			if 'fax' in t: del t['fax'] # we're dropping this field going forward
			p['terms'].append(t)
			t.update(build_term(won_row[id], False))
			
		elif id in winners:
			# Incumbent won something else. Start
			# a fresh term.
			p['terms'].append(build_term(won_row[id], True))

		else:
			# Incumbent lost.
			to_retire.append(p)

# Any legislators to bring forward?
to_return = []
for p in legislators_historical:
	id = p['id']['bioguide']
	if id in winners:
		p['terms'].append(build_term(won_row[id], True))
		to_return.append(p)

# Now that we're outside of the iterator, modify lists.
for p in to_retire:
	legislators_current.remove(p)
	legislators_historical.append(p)
for p in to_return:
	legislators_current.append(p)
	legislators_historical.remove(p)

# Save.
utils.save_data(legislators_current, "legislators-current.yaml")
utils.save_data(legislators_historical, "legislators-historical.yaml")

