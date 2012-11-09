# Update current congressmen's mailing address from clerk.house.gov. 

import lxml.html, StringIO
import urllib
import re
from datetime import date, datetime
from utils import yaml_load, yaml_dump, parse_date

today = datetime.now().date()

y = yaml_load(open("../legislators-current.yaml"))

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
	
	if "class" in term: del term["class"]

	url = "http://clerk.house.gov/member_info/mem_contact_info.aspx?statdis=%s%02d" % (term["state"], term["district"])
	try:
		# the meta tag say it's iso-8859-1, but... names are actually in utf8...
		dom = lxml.html.parse(StringIO.StringIO(urllib.urlopen(url).read().decode("utf-8"))).getroot()
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
	phone = m.group(5)
	
	moc["name"]["official_full"] = name
	term["address"] = address

yaml_dump(y, open("../legislators-current.yaml", "w"))

