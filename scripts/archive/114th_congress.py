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

import utils

def run():

	# Which members were up for relection, won in their office, or were
	# a winner in another office?
	won_row = { }
	incumbents = set()
	winners = set()
	incumbent_winners = set()
	new_members = []
	for row in csv.DictReader(open("election_results_2014.csv")):
		if row["new_member"] == "":
			print("not decided yet...", row)
			continue

		# For NC-12, Alma Adams won the vacant seat and the 114th Congress
		# term. It's coded in the spreadsheet as if she's a new member, but
		# since we've already added her in the 113th Congress we need to
		# pretend here that she's a returning member.
		if row["new_id"] == "A000370":
			row["member_id"] = "A000370"

		incumbents.add(row["member_id"])
		winners.add(row["new_id"])
		won_row[row["new_id"]] = row
		if row["member_id"] == row["new_id"]:
			incumbent_winners.add(row["new_id"])
		if row["new_id"] == "":
			new_members.append(row)

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
			("start", '2015-01-06'),
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
	legislators_social_media = utils.load_data("legislators-social-media.yaml")

	# Sweep current members.
	to_retire = []
	for p in legislators_current:
		id = p['id']['bioguide']
		if id in incumbents:
			# This legislator was up for reelection.
			if id in incumbent_winners:
				# And won. Extend the term.
				t = copy.deepcopy(p['terms'][-1])
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

	# Delete entries in legislators-social-media for those retiring
	retiring_leg_bioguideids = [leg['id']['bioguide'] for leg in to_retire]
	for p in legislators_social_media:
		id = p['id']['bioguide']
		if id in retiring_leg_bioguideids:
			legislators_social_media.remove(p)

	# Add stubs for new members.
	def fix_date(date):
		m, d, y = date.split("/")
		return "%04d-%02d-%02d" % (int(y), int(m), int(d))
	for i, row in enumerate(new_members):
		p = OrderedDict([
			("id", OrderedDict([
			    ("bioguide", "TODO"),
			    ("thomas", "TODO"),
			    ("lis", "TODO"),
			    ("fec", row['new_fec_cand_id'].split(',')),
			    ("govtrack", 412608+i), # assigning IDs here
			    ("opensecrets", "TODO"),
			    ("votesmart", "TODO"),
			    ("icpsr", "TODO"),
			    ("cspan", "TODO"),
			    ("wikipedia", "TODO"),
			    ("ballotpedia", "TODO"),
			    ("house_history", "TODO"),
			])),
			("name", OrderedDict()),
			("bio", OrderedDict([
				("gender", row["gender"]),
				("birthday", fix_date(row["date_of_birth"]) if row["date_of_birth"] != "" else "TODO"),
			])),
			("terms", [
				build_term(row, True),
			])
		])

		if len(row["new_member"].split(" ")) == 2:
			p['name']['first'] = row["new_member"].split(" ")[0]
			p['name']['last'] = row["new_member"].split(" ")[1]
		else:
			p['name']['FULL'] = row["new_member"]
			p['name']['first'] = "TODO"
			p['name']['last'] = "TODO"

		legislators_current.append(p)


	# Save.
	utils.save_data(legislators_current, "legislators-current.yaml")
	utils.save_data(legislators_historical, "legislators-historical.yaml")
	utils.save_data(legislators_social_media, "legislators-social-media.yaml")

if __name__ == '__main__':
  run()
