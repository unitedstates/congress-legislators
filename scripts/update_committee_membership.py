# Scrape house.gov and senate.gov for current committee membership,
# and updates the committees-current.yaml file with metadata including
# name, address, and phone number.

import re, urllib, lxml.html, StringIO, datetime
from collections import OrderedDict
from utils import yaml_load, yaml_dump, CURRENT_CONGRESS, parse_date

committee_membership = { }
committees_current = yaml_load(open("../committees-current.yaml"))

# map house/senate's to their dicts
house_ref = { }
for cx in committees_current:
  if "house_committee_id" in cx:
    house_ref[cx["house_committee_id"]] = cx
senate_ref = { }
for cx in committees_current:
  if "senate_committee_id" in cx:
    senate_ref[cx["senate_committee_id"]] = cx

# map state/district to current congressmen
today = datetime.datetime.now().date()
legislators_current = yaml_load(open("../legislators-current.yaml"))
congressmen = { }
for moc in legislators_current:
  term = moc["terms"][-1]
  if term["type"] != "rep": continue
  if today < parse_date(term["start"]) or today > parse_date(term["end"]):
    raise ValueError("Member's last listed term is not current: " + repr(moc) + " / " + term["start"])
  congressmen["%s%02d" % (term["state"], term["district"])] = moc

# track which committees we've seen so we can check that we saw them all
seen_committees = set()

# Scrape clerk.house.gov...
def scrape_house():
  body = urllib.urlopen("http://clerk.house.gov/committee_info/index.aspx").read()

  for id, name in re.findall(r'<a href="/committee_info/index.aspx\?comcode=(..)00">(.*)</a>', body, re.I):
    if id not in house_ref:
      print "Unrecognized committee:", id, name
      continue
    
    cx = house_ref[id]
    seen_committees.add(cx["thomas_id"])
    scrape_house_committee(cx, cx["thomas_id"], id + "00")
    
def scrape_house_committee(cx, output_code, house_code):
  print house_code, "..."
  
  # make the committee metadata file indicate this committee is current if it doesn't already
  if "congresses" in cx:
    if str(CURRENT_CONGRESS) not in cx["congresses"].split(","):
      cx["congresses"] += "," + str(CURRENT_CONGRESS)
  else:
    cx["congresses"] = str(CURRENT_CONGRESS)
  
  # load the House Clerk's committee membership page for the committee
  # (it is encoded in utf-8 even though the page indicates otherwise, and
  # while we don't really care, it helps our sanity check that compares
  # names)
  url = "http://clerk.house.gov/committee_info/index.aspx?%s=%s" % ('comcode' if house_code[-2:] == '00' else 'subcomcode', house_code)
  dom = lxml.html.parse(StringIO.StringIO(urllib.urlopen(url).read().decode("utf-8"))).getroot()
  
  # update official name metadata
  if house_code[-2:] == "00":
    cx["name"] = "House " + str(dom.cssselect("#com_display h3")[0].text_content())
  else:
    cx["name"] = str(dom.cssselect("#subcom_title h4")[0].text_content())
    
  # update address/phone metadata
  address_info = re.search(r"""Mailing Address:\s*(.*\S)\s*Telephone:\s*(\(202\) .*\S)""", dom.cssselect("#address")[0].text_content(), re.I | re.S)
  if not address_info: raise Exception("Failed to parse address info in %s." % house_code)
  cx["address"] = address_info.group(1)
  cx["address"] = re.sub(r"\s+", " ", cx["address"])
  cx["address"] = re.sub(r"(.*\S)(Washington, DC \d+)\s*(-\d+)?", lambda m : m.group(1) + "; " + m.group(2) + (m.group(3) if m.group(3) else ""), cx["address"])
  cx["phone"] = address_info.group(2)
  
  # get the ratio line to use in a sanity check later
  ratio = dom.cssselect("#ratio")
  if len(ratio): # some committees are missing
    ratio = re.search(r"Ratio (\d+)/(\d+)", ratio[0].text_content())
  else:
    ratio = None
  
  # scan the membership, which is listed by party
  for i, party, nodename in ((1, 'majority', 'primary'), (2, 'minority', 'secondary')):
    ctr = 0
    for rank, node in enumerate(dom.cssselect("#%s_group li" % nodename)):
      ctr += 1
      lnk = node.cssselect('a')
      if len(lnk) == 0:
        if node.text_content() == "Vacancy": continue
        raise ValueError("Failed to parse a <li> node.")
      moc = lnk[0].get('href')
      m = re.search(r"statdis=([A-Z][A-Z]\d\d)", moc)
      if not m: raise ValueError("Failed to parse member link: " + moc)
      if not m.group(1) in congressmen: raise ValueError("Vacancy discrepancy? " + m.group(1))
      moc = congressmen[m.group(1)]
      if node.cssselect('a')[0].text_content().replace(", ", "") != moc['name']['official_full']:
        print "Name mismatch: %s (in our file) vs %s (on the Clerk page)" % (moc['name']['official_full'], node.cssselect('a')[0].text_content())
      
      entry = OrderedDict()
      entry["party"] = party
      entry["rank"] = rank+1
      if rank == 0:
        entry["title"] = "Chair" if entry["party"] == "majority" else "Ranking Member" # not explicit, frown
      entry.update(moc["id"])
      entry["name"] = moc['name']['official_full']
      
      committee_membership.setdefault(output_code, []).append(entry)
      
      # the .tail attribute has the text to the right of the link
      m = re.match(r", [A-Z][A-Z](,\s*)?(.*\S)?", lnk[0].tail)
      if m.group(2):
        if m.group(2) == "Ex Officio":
          entry["title"] = m.group(2)
        else:
          raise ValueError("Unrecognized title information: " + m.group(2))
      
    # sanity check we got the right number of nodes
    if ratio and ctr != int(ratio.group(i)): raise ValueError("Parsing didn't get the right count of members.")
    
  # scan for subcommittees
  for subcom in dom.cssselect("#subcom_list li a"):
    m = re.search("subcomcode=(..(\d\d))", subcom.get('href'))
    if not m: raise ValueError("Failed to parse subcommittee link.")
    
    for sx in cx['subcommittees']:
      if sx["thomas_id"] == m.group(2):
        sx["name"] = subcom.text_content()
        sx["name"] = re.sub(r"\s+Subcommittee$", "", sx["name"])
        break
    else:
      print "Subcommittee not found, creating it", output_code, m.group(1)
      sx = OrderedDict()
      sx['name'] = "[not initialized]" # will be set inside of scrape_house_committee
      sx['thomas_id'] = m.group(2)
      cx['subcommittees'].append(sx)
    scrape_house_committee(sx, cx["thomas_id"] + sx["thomas_id"], m.group(1))
  
scrape_house()

for cx in committees_current:
  if not cx["thomas_id"] in seen_committees:
    print "Missing data for", cx["name"]

yaml_dump(committee_membership, open("../committee-membership-current.yaml", "w"))
yaml_dump(committees_current, open("../committees-current.yaml", "w"))

