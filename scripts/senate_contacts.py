#!/usr/bin/env python

# Update current senator's website and address from www.senate.gov. 

import lxml.etree, StringIO
import urllib
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
for m in y:
	bioguide[m["id"]["bioguide"]] = m

url = "http://www.senate.gov/general/contact_information/senators_cfm.xml"
body = download(url, "legislators/senate.xml", force)
dom = lxml.etree.parse(StringIO.StringIO(body))
for node in dom.getroot():
	bioguide_id = str(node.xpath("string(bioguide_id)")).strip()
	print "[%s] Processing Senator..." % bioguide_id
	
	if not bioguide_id in bioguide:
		print "Missing member", bioguide_id
		continue
		
	try:
		term = bioguide[bioguide_id]["terms"][-1]
	except IndexError:
		print "Member has no terms", bioguide_id
		continue
		
	if today < parse_date(term["start"]) or today > parse_date(term["end"]):
		print "Member's last listed term is not current", bioguide_id, term["start"]
		continue
		
	if term["type"] != "sen":
		print "Member's last listed term is not a Senate term", bioguide_id
		continue
		
		
	if term["state"] != str(node.xpath("string(state)")):
		print "Member's last listed term has the wrong state", bioguide_id
		continue
		
	if "district" in term: del term["district"]

	full_name = unicode(node.xpath("string(first_name)"))
	suffix = None
	if ", " in full_name: full_name, suffix = full_name.split(", ")
	full_name += " " + unicode(node.xpath("string(last_name)"))
	if suffix: full_name += ", " + suffix
	bioguide[bioguide_id]["name"]["official_full"] = full_name

	term["class"] = { "Class I": 1, "Class II": 2, "Class III": 3}[ node.xpath("string(class)") ]
	term["party"] = { "D": "Democrat", "R": "Republican", "I": "Independent", "ID": "Independent"}[ node.xpath("string(party)") ]
	
	url = str(node.xpath("string(website)")).strip().replace("http://www.", "http://")
	term["url"] = url
	term["address"] = str(node.xpath("string(address)")).strip()
	
	# TODO there is also an "email" field with a URL to a contact form (is it always a URL?)

save_data(y, "legislators-current.yaml")