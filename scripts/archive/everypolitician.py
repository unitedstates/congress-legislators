# Converts our data into CSV files for everypolitician.org,
# one file for the House and one file for the Senate.
#
# Usage:
# python everypolitician.py outputbasename/
#
# Which will write:
# outputbasename/house.csv
# outputbasename/senate.csv

import sys, csv

from utils import yaml_load, CURRENT_CONGRESS, states

def run():
	if len(sys.argv) < 2:
		print("Usage: python everypolitician.py outputbasename/")
		sys.exit(0)

	# Load current legislators.
	data = yaml_load("../legislators-current.yaml")
	data_social_media = { }
	for legislator in yaml_load("../legislators-social-media.yaml"):
		data_social_media[legislator['id']['bioguide']] = legislator

	# Create output files.
	writers = {
		"rep": csv.writer(open(sys.argv[1] + "house.csv", "w")),
		"sen": csv.writer(open(sys.argv[1] + "senate.csv", "w")),
	}
	for w in writers.values():
		w.writerow([
			"id",
			"name",
			"area",
			"group",
			"term",
			"start_date",
			"end_date",
			"given_name",
			"family_name",
			"honorific_suffix",
			"sort_name",
			"phone",
			"gender",
			"birth_date",
			"image",
			"twitter",
			"facebook",
			"instagram",
			"wikipedia",
			"website",
		])

	# Write out one row per legislator for their current term.
	for legislator in data:
		term = legislator['terms'][-1]

		# TODO: "If someone changed party/faction affilation in the middle of the term, you should include two entries, with the relevant start/end dates set."

		w = writers[term['type']]
		w.writerow([
			legislator['id']['bioguide'],
			build_name(legislator, term, 'full'),
			build_area(term),
			term['party'],
			CURRENT_CONGRESS,
			term['start'],
			term['end'],
			legislator['name'].get('first'),
			legislator['name'].get('last'),
			legislator['name'].get('suffix'),
			build_name(legislator, term, 'sort'),
			term.get('phone'),
			legislator['bio'].get('gender'),
			legislator['bio'].get('birthday'),
			"https://theunitedstates.io/images/congress/original/%s.jpg" % legislator['id']['bioguide'],
			data_social_media.get(legislator['id']['bioguide'], {}).get("social", {}).get("twitter"),
			data_social_media.get(legislator['id']['bioguide'], {}).get("social", {}).get("facebook"),
			data_social_media.get(legislator['id']['bioguide'], {}).get("social", {}).get("instagram"),
			legislator['id'].get('wikipedia', '').replace(" ", "_"),
			term['url'],
		])

ordinal_strings = { 1: "st", 2: "nd", 3: "rd", 11: 'th', 12: 'th', 13: 'th' }
def ordinal(num):
	return str(num) + ordinal_strings.get(num % 100, ordinal_strings.get(num % 10, "th"))

def build_area(term):
	# Builds the string for the "area" column, which is a human-readable
	# description of the legislator's state or district.
	ret = states[term['state']]
	if term['type'] == 'rep':
		ret += "’s "
		if term['district'] == 0:
			ret += "At-Large"
		else:
			ret += ordinal(term['district'])
		ret += " Congressional District"
	return ret

def build_name(p, t, mode):
	# Based on:
	# https://github.com/govtrack/govtrack.us-web/blob/master/person/name.py

	# First name.
	firstname = p['name']['first']
	if firstname.endswith('.'):
		firstname = p['name']['middle']
	if p['name'].get('nickname') and len(p['name']['nickname']) < len(firstname):
			firstname = p['name']['nickname']

	# Last name.
	lastname = p['name']['last']
	if p['name'].get('suffix'):
		lastname += ', ' + p['name']['suffix']

	if mode == "full":
		return firstname + ' ' + lastname
	elif mode == "sort":
		return lastname + ', ' + firstname
	else:
		raise ValueError(mode)

if __name__ == '__main__':
  run()
