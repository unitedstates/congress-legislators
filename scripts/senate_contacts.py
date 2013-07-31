#!/usr/bin/env python

# Update current senator's website and address from www.senate.gov. 

import lxml.etree, StringIO
import urllib
import string, re
from datetime import date, datetime
import utils
from utils import download, load_data, save_data, parse_date

today = datetime.now().date()

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

y = load_data("legislators-current.yaml")

# Map bioguide IDs to dicts. Reference the same dicts
# in y so we are updating y when we update biogiude.
bioguide = { }
by_name = { }
for m in y:
	if m["id"].has_key("bioguide"):
		bioguide[m["id"]["bioguide"]] = m
	party = m["terms"][-1]["party"][0]
	state = m["terms"][-1]["state"]
	last_name = m["name"]["last"]
	member_full = "%s (%s-%s)" % (last_name, party, state)
	by_name[member_full] = m


print "Fetching general Senate information from senators_cfm.xml..."

url = "http://www.senate.gov/general/contact_information/senators_cfm.xml"
body = download(url, "legislators/senate.xml", force)
dom = lxml.etree.parse(StringIO.StringIO(body))
for node in dom.xpath("member"):
	bioguide_id = str(node.xpath("string(bioguide_id)")).strip()
	member_full = node.xpath("string(member_full)")

	print "[%s] Processing Senator %s..." % (bioguide_id, member_full)
	
	# find member record in our YAML, either by bioguide_id or member_full
	if bioguide.has_key(bioguide_id):
		member = bioguide[bioguide_id]
	else:
		if by_name.has_key(member_full):
			member = by_name[member_full]
		else:
			print "Bioguide ID '%s' and full name '%s' not recognized." % (bioguide_id, member_full)
			exit(0)

	try:
		term = member["terms"][-1]
	except IndexError:
		print "Member has no terms", bioguide_id, member_full
		continue
		
	if today < parse_date(term["start"]) or today > parse_date(term["end"]):
		print "Member's last listed term is not current", bioguide_id, member_full, term["start"]
		continue
		
	if term["type"] != "sen":
		print "Member's last listed term is not a Senate term", bioguide_id, member_full
		continue
		
		
	if term["state"] != str(node.xpath("string(state)")):
		print "Member's last listed term has the wrong state", bioguide_id, member_full
		continue
		
	if "district" in term: del term["district"]

	full_name = unicode(node.xpath("string(first_name)"))
	suffix = None
	if ", " in full_name: full_name, suffix = full_name.split(", ")
	full_name += " " + unicode(node.xpath("string(last_name)"))
	if suffix: full_name += ", " + suffix
	member["name"]["official_full"] = full_name

	member["id"]["bioguide"] = bioguide_id

	term["class"] = { "Class I": 1, "Class II": 2, "Class III": 3}[ node.xpath("string(class)") ]
	term["party"] = { "D": "Democrat", "R": "Republican", "I": "Independent", "ID": "Independent"}[ node.xpath("string(party)") ]
	
	url = str(node.xpath("string(website)")).strip()
	
	# kill trailing slashes
	url = re.sub("/$", "", url)

	if not url.startswith("/"): term["url"] = url # temporary home pages for new senators
	term["address"] = str(node.xpath("string(address)")).strip()
	term["office"] = string.capwords(term["address"].split(" WASHINGTON ")[0])

	phone = str(node.xpath("string(phone)")).strip()
	term["phone"] = phone.replace("(", "").replace(")", "").replace(" ", "-")
	
	contact_form = str(node.xpath("string(email)")).strip()
	if contact_form: # can be blank
		term["contact_form"] = contact_form



print "\n\nUpdating Senate stateRank and LIS ID from cvc_member_data.xml..."

url = "http://www.senate.gov/legislative/LIS_MEMBER/cvc_member_data.xml"
body = download(url, "legislators/senate_cvc.xml", force)
dom = lxml.etree.parse(StringIO.StringIO(body))
for node in dom.getroot():
	if node.tag == "lastUpdate":
		date, time = node.getchildren()
		print "Last updated: %s, %s" % (date.text, time.text)
		continue

	bioguide_id = str(node.xpath("string(bioguideId)")).strip()
	last_name = node.xpath("string(name/last)")
	party = node.xpath("string(party)")
	state = node.xpath("string(state)")
	member_full = "%s (%s-%s)" % (last_name, party, state)

	print "[%s] Processing Senator %s..." % (bioguide_id, member_full)
	
	# find member record in our YAML, either by bioguide_id or member_full
	if bioguide.has_key(bioguide_id):
		member = bioguide[bioguide_id]
	else:
		if by_name.has_key(member_full):
			member = by_name[member_full]
		else:
			print "Bioguide ID '%s' and synthesized official name '%s' not recognized." % (bioguide_id, member_full)
			exit(0)

	try:
		term = member["terms"][-1]
	except IndexError:
		print "Member has no terms", bioguide_id, member_full
		continue

	if not member.has_key("id"):
		member["id"] = {}

	member["id"]["lis"] = node.attrib["lis_member_id"]
	state_rank = node.xpath("string(stateRank)")
	if state_rank == '1':
		term["state_rank"] = "senior"
	elif state_rank == '2':
		term["state_rank"] = "junior"


print "Saving data..."
save_data(y, "legislators-current.yaml")
