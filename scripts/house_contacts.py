#!/usr/bin/env python

# Update current congressmen's mailing address from clerk.house.gov.
#
# Specify districts e.g. WA-02 on the command line to only update those.

import lxml.html, StringIO
import re, sys
from datetime import date, datetime
import utils
from utils import download, load_data, save_data, parse_date

today = datetime.now().date()


# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

y = load_data("legislators-current.yaml")

for moc in y:
	try:
		term = moc["terms"][-1]
	except IndexError:
		print "Member has no terms", moc
		continue
		
	if term["type"] != "rep": continue
	
	if today < parse_date(term["start"]) or today > parse_date(term["end"]):
		print "Member's last listed term is not current", moc, term["start"]
		continue

	#if len(sys.argv) > 1 and ("%s-%02d" % (term["state"], term["district"])) not in sys.argv: continue

	if "class" in term: del term["class"]

	url = "http://clerk.house.gov/member_info/mem_contact_info.aspx?statdis=%s%02d" % (term["state"], term["district"])
	cache = "legislators/house/%s%02d.html" % (term["state"], term["district"])
	try:
		# the meta tag say it's iso-8859-1, but... names are actually in utf8...
		body = download(url, cache, force)
		dom = lxml.html.parse(StringIO.StringIO(body.decode("utf-8"))).getroot()
	except lxml.etree.XMLSyntaxError:
		print "Error parsing: ", url
		continue
	
	name = unicode(dom.cssselect("#results h3")[0].text_content())
	addressinfo = unicode(dom.cssselect("#results p")[0].text_content())
	
	# Sanity check that the name is similar.
	if name != moc["name"].get("official_full", ""):
		cfname = moc["name"]["first"] + " " + moc["name"]["last"]
		print "Warning: Are these the same people?", name.encode("utf8"), "|", cfname.encode("utf8")
	
	# Parse the address out of the address p tag.
	addressinfo = "; ".join(line.strip() for line in addressinfo.split("\n") if line.strip() != "")
	m = re.match(r"[\w\s]+-(\d+(st|nd|rd|th)|At Large|Delegate|Resident Commissioner), ([A-Za-z]*)(.+); Phone: (.*)", addressinfo, re.DOTALL)
	if not m:
		print "Error parsing address info: ", name.encode("utf8"), ":", addressinfo.encode("utf8")
		continue
	
	address = m.group(4)
	phone = re.sub("^\((\d\d\d)\) ", lambda m : m.group(1) + "-", m.group(5)) # replace (XXX) area code with XXX- for compatibility w/ existing format

	office = address.split(";")[0].replace("HOB", "House Office Building")
	
	moc["name"]["official_full"] = name
	term["address"] = address
	term["office"] = office
	term["phone"] = phone

save_data(y, "legislators-current.yaml")