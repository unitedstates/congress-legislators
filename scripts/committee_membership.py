#!/usr/bin/env python

# Scrape house.gov and senate.gov for current committee membership,
# and updates the committees-current.yaml file with metadata including
# name, url, address, and phone number. While the Senate has XML for
# full committee membership, we're still scraping the old way in
# order to get subcommittee membership.

import re, lxml.html, StringIO, datetime
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

# track which committees we've seen so we can check that we saw them all
seen_committees = set()

# Scrape clerk.house.gov...
def scrape_house():
  url = "http://clerk.house.gov/committee_info/index.aspx"
  body = download(url, "committees/membership/house.html", force)

  for id, name in re.findall(r'<a href="/committee_info/index.aspx\?comcode=(..)00">(.*)</a>', body, re.I):
    if id not in house_ref:
      print "Unrecognized committee:", id, name
      continue
    
    cx = house_ref[id]
    seen_committees.add(cx["thomas_id"])
    scrape_house_committee(cx, cx["thomas_id"], id + "00")
    
def scrape_house_committee(cx, output_code, house_code):
  ## make the committee metadata file indicate this committee is current if it doesn't already
  #if "congresses" in cx:
  #  if str(CURRENT_CONGRESS) not in cx["congresses"].split(","):
  #    cx["congresses"] += "," + str(CURRENT_CONGRESS)
  #else:
  #  cx["congresses"] = str(CURRENT_CONGRESS)
  
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

# Scrape senate.gov....
def scrape_senate():
  url = "http://www.senate.gov/pagelayout/committees/b_three_sections_with_teasers/membership.htm"
  body = download(url, "committees/membership/senate.html", force)

  for id, name in re.findall(r'value="/general/committee_membership/committee_memberships_(....).htm">(.*?)</option>', body, re.I |  re.S):
    if id not in senate_ref:
      print "Unrecognized committee:", id, name
      continue
      
    cx = senate_ref[id]
    seen_committees.add(cx["thomas_id"])
    #scrape_senate_committee(cx, cx["thomas_id"], id)

    committee_url = "http://www.senate.gov/general/committee_membership/committee_memberships_%s.htm" % id
    body2 = download(committee_url, "committees/membership/senate/%s.html" % id, force)
    
    if body2:
      m = re.search(r"<committee_name>(.*)</committee_name>", body2)
      
    if not body2 or not m:
      print "\tcommittee page not good:", committee_url
      continue
     
    cx["name"] = m.group(1)
    if id[0] != "J" and id[0:2] != 'SC':
      cx["name"] = "Senate " + cx["name"]
 
    m = re.search(r'<span class="contenttext"><a href="(http://(.*?).senate.gov/)">', body2, re.I)
    if m:
      cx["url"] = m.group(1)
      
    # scan subcommittee links
    for scid, name in re.findall(r'<a href="#' + id + '(\d\d)">Subcommittee on (.*?)</a></span>', body2):
      for sx in cx['subcommittees']:
        if sx["thomas_id"] == scid:
          break
      else:
        print "Subcommittee not found, creating it", scid, name
        sx = OrderedDict()
        sx['thomas_id'] = scid
        cx['subcommittees'].append(sx)
        
      # update metadata
      sx["name"] = name.strip()
      sx["name"] = re.sub(r"^\s*Subcommittee on\s*", "", sx["name"])
      sx["name"] = re.sub(r"\s+", " ", sx["name"])

      ## make the committee metadata file indicate this committee is current if it doesn't already
      #if "congresses" in sx:
      #  if str(CURRENT_CONGRESS) not in sx["congresses"].split(","):
      #    sx["congresses"] += "," + str(CURRENT_CONGRESS)
      #else:
      #  sx["congresses"] = str(CURRENT_CONGRESS)
        
    # scan membership
    for issubcom, subcom, members_majority, members_minority in re.findall(r"""(<a NAME="(....\d\d)">.*?)?<td valign="top" nowrap>(.*?)</td><td valign="top" nowrap>(.*?)</td>""", body2, re.I | re.S):
      output_code = id
      if subcom: output_code = subcom
        
      for party, members in (('majority', members_majority), ('minority', members_minority)):
        for rank, member in enumerate(members.split("<br>")):
          # majority party members in the full committee have weird formatting (XML showing through)
          member = re.sub(r"</?[a-z_]+>", "", member)
          member = re.sub(r"\s+", " ", member).strip()
          if member == "": continue
          
          m = re.match(r"(.*), .* \((..)\)(?:\s*,\s*([\w\s]+))?$", member, re.I)
          if not m:
            print "Failed to parse line:", member
            continue
            
          last_name, state, title = m.groups()
          
          # look up senator by state and last name
          moc = senators[(state, last_name)]
          
          entry = OrderedDict()
          entry["name"] = moc['name']['official_full']
          entry["party"] = party
          entry["rank"] = rank+1
          if title: entry["title"] = title
          entry.update(ids_from(moc["id"]))
            
          committee_membership.setdefault(output_code, []).append(entry)
      

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

scrape_house()
scrape_senate()

# Check that we got data for all committees.
# TODO: Make sure we have data from both chambers for the joint committees,
# but unfortunately the House did not publish joint committee membership in
# the 112th Congress!
for cx in committees_current:
  if not cx["thomas_id"] in seen_committees:
    print "Missing data for", cx["name"]

save_data(committee_membership, "committee-membership-current.yaml")
save_data(committees_current, "committees-current.yaml")
