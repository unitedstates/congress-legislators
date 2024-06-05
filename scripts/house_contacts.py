#!/usr/bin/env python

# Update current congressmember's contact info from clerk XML feed

import requests
import lxml
import re
from datetime import datetime

from utils import load_data, save_data, parse_date

def run():
	today = datetime.now().date()

	y = load_data("legislators-current.yaml")

	# TODO use download util?
	xml = requests.get("http://clerk.house.gov/xml/lists/MemberData.xml")
	#xml = requests.get("https://clerk.house.gov/xml/lists/unofficial-118-member-elect-data.xml")
	root=lxml.etree.fromstring(xml.content)

	for moc in y:
		try:
			term = moc["terms"][-1]
		except IndexError:
			print("Member has no terms", moc)
			continue

		if term["type"] != "rep": continue

		if today < parse_date(term["start"]) or today > parse_date(term["end"]):
			print("Member's last listed term is not current", moc, term["start"])
			continue

		ssdd = "%s%02d" % (term["state"], term["district"])

		query_str = "./members/member/[statedistrict='%s']" % ssdd

		# Odd state abbreviation.
		query_str = query_str.replace("AS00", "AQ00")

		mi = root.findall(query_str)[0].find('member-info')

		# Check that the bioguide ID matches.
		bioguideid = mi.find('bioguideID').text
		if moc['id'].get('bioguide') is not None and \
		      bioguideid != moc['id']['bioguide']:
			print("Warning: Bioguide ID did not match for %s%02d (%s != %s)" % (
				term["state"], term["district"],
				bioguideid, moc['id']['bioguide']))
		elif moc['id'].get('bioguide') is None:
			# At the start of a Congress, we can import the Bioguide ID from
			# the official data since we matched on state & district.

			# To keep the field order nice, insert it at the start of the
			# IDs list.
			moc['id'] = dict([("bioguide", bioguideid)]
				           + list(moc['id'].items()))

		# for now, no automatic name updates since there is disagremeent on how to handle
		# firstname = mi.find('firstname').text
		# middlename = mi.find('middlename').text #could be empty
		# lastname = mi.find('lastname').text

		if mi.find('official-name') is None or mi.find('official-name').text is None:
			print("Warning: No official-name tag for %s" % ssdd)
			officialname = None
		else:
			officialname = re.sub("'", "’", mi.find('official-name').text)

		office_room = mi.find('office-room').text
		office_building = mi.find('office-building').text

		office_building_full = office_building.replace("RHOB", "Rayburn House Office Building")
		office_building_full = office_building_full.replace("CHOB", "Cannon House Office Building")
		office_building_full = office_building_full.replace("LHOB", "Longworth House Office Building")

		office_zip = mi.find('office-zip').text
		office_zip_suffix = mi.find('office-zip-suffix').text

		office = "{} {}".format(office_room, office_building_full)
		address = "{} {} Washington DC {}-{}".format(office_room, office_building_full, office_zip, office_zip_suffix)

		phone = mi.find('phone').text
		phone_parsed = re.sub(r"^\((\d\d\d)\) ", lambda m : m.group(1) + "-", phone) # replace (XXX) area code with XXX- for compatibility w/ existing format

		#for now, no automatic name updates since there is disagremeent on how to handle
		# moc["name"]["first"] = firstname
		# if (middlename):
		# 	moc["name"]["middle"] = middlename
		# else:
		# 	if ("middle" in moc["name"]):
		# 		del moc["name"]["middle"]
		# moc["name"]["last"] = lastname

		# TODO: leave if none?
		if (officialname):
			moc["name"]["official_full"] = officialname
		term["address"] = address
		term["office"] = office
		term["phone"] = phone_parsed

	save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
