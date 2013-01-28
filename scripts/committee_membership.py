#!/usr/bin/env python

# Scrape house.gov and senate.gov for current committee membership,
# and updates the committees-current.yaml file with metadata including
# name, url, address, and phone number.

import re, lxml.html, lxml.etree, StringIO, datetime
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, parse_date, CURRENT_CONGRESS


committee_membership = { }
committees_current = load_data("committees-current.yaml")


# default to not caching
cache = utils.flags().get('cache', False)
force = not cache


# map house/senate committee IDs to their dicts
house_ref = { }
for cx in committees_current:
  if "house_committee_id" in cx:
    house_ref[cx["house_committee_id"]] = cx
senate_ref = { }
for cx in committees_current:
  if "senate_committee_id" in cx:
    senate_ref[cx["senate_committee_id"]] = cx



# map state/district to current representatives and state/lastname to current senators
# since the House/Senate pages do not provide IDs for Members of Congress
today = datetime.datetime.now().date()
legislators_current = load_data("legislators-current.yaml")
congressmen = { }
senators = { }
for moc in legislators_current:
  term = moc["terms"][-1]
  if today < parse_date(term["start"]) or today > parse_date(term["end"]):
    raise ValueError("Member's last listed term is not current: " + repr(moc) + " / " + term["start"])
  if term["type"] == "rep":
    congressmen["%s%02d" % (term["state"], term["district"])] = moc
  elif term["type"] == "sen":  
    for n in [moc["name"]] + moc.get("other_names", []):
      senators[(term["state"], n["last"])] = moc


# Scrape clerk.house.gov...
def scrape_house():
  url = "http://clerk.house.gov/committee_info/index.aspx"
  body = download(url, "committees/membership/house.html", force)

  for id, name in re.findall(r'<a href="/committee_info/index.aspx\?comcode=(..)00">(.*)</a>', body, re.I):
    if id not in house_ref:
      print "Unrecognized committee:", id, name
      continue
    
    cx = house_ref[id]
    scrape_house_committee(cx, cx["thomas_id"], id + "00")
    
def scrape_house_committee(cx, output_code, house_code):
  # load the House Clerk's committee membership page for the committee
  # (it is encoded in utf-8 even though the page indicates otherwise, and
  # while we don't really care, it helps our sanity check that compares
  # names)
  url = "http://clerk.house.gov/committee_info/index.aspx?%s=%s" % ('comcode' if house_code[-2:] == '00' else 'subcomcode', house_code)
  body = download(url, "committees/membership/house/%s.html" % house_code, force)
  dom = lxml.html.parse(StringIO.StringIO(body.decode('utf-8'))).getroot()
  
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
      if not m.group(1) in congressmen: 
        print "Vacancy discrepancy? " + m.group(1)
        continue
      moc = congressmen[m.group(1)]
      if node.cssselect('a')[0].text_content().replace(", ", "") != moc['name']['official_full']:
        print "Name mismatch: %s (in our file) vs %s (on the Clerk page)" % (moc['name']['official_full'], node.cssselect('a')[0].text_content())
      
      entry = OrderedDict()
      entry["name"] = moc['name']['official_full']
      entry["party"] = party
      entry["rank"] = rank+1
      if rank == 0:
        entry["title"] = "Chair" if entry["party"] == "majority" else "Ranking Member" # not explicit, frown
      entry.update(ids_from(moc["id"]))
      
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
        break
    else:
      print "Subcommittee not found, creating it", output_code, m.group(1)
      sx = OrderedDict()
      sx['name'] = "[not initialized]" # will be set inside of scrape_house_committee
      sx['thomas_id'] = m.group(2)
      cx['subcommittees'].append(sx)
    scrape_house_committee(sx, cx["thomas_id"] + sx["thomas_id"], m.group(1))

# Scrape senate.gov....
def scrape_senate():
  url = "http://www.senate.gov/pagelayout/committees/b_three_sections_with_teasers/membership.htm"
  body = download(url, "committees/membership/senate.html", force)

  for id, name in re.findall(r'value="/general/committee_membership/committee_memberships_(....).htm">(.*?)</option>', body, re.I |  re.S):
    if id not in senate_ref:
      print "Unrecognized committee:", id, name
      continue
    
    print "[%s] Fetching members for %s" % (id, name)

    cx = senate_ref[id]
    
    # Scrape some metadata on the HTML page first.
    
    print "\tDownloading HTML..."
    committee_url = "http://www.senate.gov/general/committee_membership/committee_memberships_%s.htm" % id
    body2 = download(committee_url, "committees/membership/senate/%s.html" % id, force)
    
    if not body2:
      print "\tcommittee page not good:", committee_url
      continue
      
    m = re.search(r'<span class="contenttext"><a href="(http://(.*?).senate.gov/)">', body2, re.I)
    if m:
      cx["url"] = m.group(1)
      
    m = re.search(r"<committee_name>(.*)</committee_name>", body2)
    cx["name"] = m.group(1)
    if id[0] != "J" and id[0:2] != 'SC':
      cx["name"] = "Senate " + cx["name"]
 
    
    # Use the XML for the rest.

    print "\tDownloading XML..."
    committee_url = "http://www.senate.gov/general/committee_membership/committee_memberships_%s.xml" % id

    body3 = download(committee_url, "committees/membership/senate/%s.xml" % id, force)
    dom = lxml.etree.fromstring(body3)
    majority_party = dom.xpath("committees/majority_party")[0].text
    
    # update full committee members
    committee_membership[id] = []
    for member in dom.xpath("committees/members/member"):
      scrape_senate_member(committee_membership[id], member, majority_party)
    
    # update subcommittees
    for subcom in dom.xpath("committees/subcommittee"):
      scid = subcom.xpath("committee_code")[0].text[4:]
      for sx in cx.get('subcommittees', []):
        if sx["thomas_id"] == scid:
          break
      else:
        print "Subcommittee not found, creating it", scid, name
        sx = OrderedDict()
        sx['thomas_id'] = scid
        cx.setdefault('subcommittees', []).append(sx)
        
      # update metadata
      name = subcom.xpath("subcommittee_name")[0].text
      sx["name"] = name.strip()
      sx["name"] = re.sub(r"^\s*Subcommittee on\s*", "", sx["name"])
      sx["name"] = re.sub(r"\s+", " ", sx["name"])
      
      committee_membership[id + scid] = []
      for member in subcom.xpath("members/member"):
        scrape_senate_member(committee_membership[id + scid], member, majority_party)

def scrape_senate_member(output_list, membernode, majority_party):
  last_name = membernode.xpath("name/last")[0].text
  state = membernode.xpath("state")[0].text
  party = "majority" if membernode.xpath("party")[0].text == majority_party else "minority"
  title = membernode.xpath("position")[0].text
  if title == "Member": title = None
  if title == "Ranking": title = "Ranking Member"
          
  # look up senator by state and last name
  if not senators.has_key((state, last_name)):
    print "\t[%s] Unknown member: %s" % (state, last_name)
    return None

  moc = senators[(state, last_name)]
  
  entry = OrderedDict()
  entry["name"] = moc['name']['official_full']
  entry["party"] = party
  entry["rank"] = len([e for e in output_list if e["party"] == entry["party"]]) + 1 # how many have we seen so far in this party, +1
  if title: entry["title"] = title
  entry.update(ids_from(moc["id"]))
    
  output_list.append(entry)
  
  # sort by party, then by rank, since we get the nodes in the XML in a rough seniority order that ignores party
  # should be done once at the end, but cleaner to do it here
  output_list.sort(key = lambda e : (e["party"] != "majority", e["rank"]))

# stick to a specific small set of official IDs to cross-link members
# this limits the IDs from going out of control in this file, while
# preserving us flexibility to be inclusive of IDs in the main leg files
def ids_from(moc):
  ids = {}
  for id in ["bioguide", "thomas"]:
    if moc.has_key(id):
      ids[id] = moc[id]
  if len(ids) == 0:
    raise ValueError("Missing an official ID for this legislator, won't be able to link back")
  return ids


# MAIN

# scrape_house()
scrape_senate()

save_data(committee_membership, "committee-membership-current.yaml")
save_data(committees_current, "committees-current.yaml")
