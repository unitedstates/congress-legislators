#!/usr/bin/env python

# Data Sources:
#   House:
#     http://clerk.house.gov/xml/lists/MemberData.xml
#   Senate:
#     https://www.senate.gov/general/committee_membership/committee_memberships_{thomas_id}.xml

# Data Files Updated:
#   committee-membership-current.yaml:
#     All entries are overwritten except for house members of joint committees
#     which have to be manually entered since there is no source of this data
#   committees-current.yaml:
#     Fro House committees, updates name, address, and phone
#     For Senate committees, updates name and url


import requests
import re, lxml.html, lxml.etree, datetime
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, parse_date


def run():
  committee_membership = load_data("committee-membership-current.yaml")
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
  congressmen_by_bioguide = {}
  senators = { }
  for moc in legislators_current:
    term = moc["terms"][-1]
    if today < parse_date(term["start"]) or today > parse_date(term["end"]):
      raise ValueError("Member's last listed term is not current: " + repr(moc) + " / " + term["start"])
    if term["type"] == "rep":
      congressmen_by_bioguide[moc["id"]["bioguide"]] = moc
    elif term["type"] == "sen":
      for n in [moc["name"]] + moc.get("other_names", []):
        senators[(term["state"], n["last"])] = moc


  # Scrape clerk.house.gov...
  def scrape_house():
    # r = download("http://clerk.house.gov/xml/lists/MemberData.xml", "clerk_xml")
    # dom = lxml.etree.fromstring(r.encode("utf8")) # must be bytes to parse if there is an encoding declaration inside the string
    
    #for some reason using the download method creates encoding issues?
    r = requests.get("http://clerk.house.gov/xml/lists/MemberData.xml")
    dom = lxml.etree.fromstring(r.content)

    committees = dom.xpath("/MemberData/committees")[0]
    for xml_cx in committees.findall("committee"):
      house_committee_id = xml_cx.attrib["comcode"][:2]
      #if this throws an error, make sure house_committee_id is set in committees-current.yaml for the committee
      cx = house_ref[house_committee_id]
      cx["name"] = "House " + xml_cx.find("committee-fullname").text
      
      building = xml_cx.attrib["com-building-code"]
      if building == "C":
        building = "CAPITOL"
      #address format: 1301 LHOB; Washington, DC 20515-6001
      cx["address"] = xml_cx.attrib["com-room"] + " " + building \
         + "; Washington, DC " + xml_cx.attrib["com-zip"] + "-" + xml_cx.attrib["com-zip-suffix"]
      cx["phone"] = "(202) " + xml_cx.attrib["com-phone"]
    
    members = dom.xpath("/MemberData/members")[0]
    for xml_member in members.findall("member"):
      bioguide_id = xml_member.xpath("member-info/bioguideID")[0].text
      if not bioguide_id: #sometimes the xml has vacancies as blanks
        continue

      official_name = xml_member.xpath("member-info/official-name")[0].text
      if bioguide_id not in congressmen_by_bioguide:
        print("{} ({}) was skiped because not found in current".format(official_name, bioguide_id))
        continue
      
      #is using caucus better than using party?
      caucus = xml_member.xpath("member-info/caucus")[0].text
      party = "majority"
      if caucus != "R":
        party = "minority"
            
      #for each committee or subcommittee membership
      for cm in xml_member.xpath("committee-assignments/committee|committee-assignments/subcommittee"):
        if "comcode" in cm.attrib:
          type = "committee"
        elif "subcomcode" in cm.attrib:
          type = "subcommittee"
        else:
          continue #some are blank?
        if type == "committee":
          house_committee_id = cm.attrib["comcode"][:2]
        else:
          house_committee_id = cm.attrib["subcomcode"][:2]

        if type == "committee":
          thomas_committee_id = house_ref[house_committee_id]["thomas_id"]
        else:
          thomas_committee_id = house_ref[house_committee_id]["thomas_id"] + cm.attrib["subcomcode"][2:]

        membership = OrderedDict()
        membership["name"] = official_name
        membership["party"] = party
        membership["rank"] = int(cm.attrib["rank"])

        if "leadership" in cm.attrib:
          #gender neutral
          membership["title"] = cm.attrib["leadership"].replace("woman", "").replace("man", "")
        elif membership["rank"] == 1:
          #xml doesn't contain ranking member titles
          if membership["party"] == "majority":
            membership["title"] = "Chair"
          else:
            membership["title"] = "Ranking Member"
        membership["bioguide"] = bioguide_id
        if house_ref[house_committee_id]["type"] == "joint":
          membership["chamber"] = "house"

        committee_membership.setdefault(thomas_committee_id, []).append(membership)

  # Scrape senate.gov....
  def scrape_senate():
    url = "https://www.senate.gov/pagelayout/committees/b_three_sections_with_teasers/membership.htm"
    body = download(url, "committees/membership/senate.html", force)

    for id, name in re.findall(r'value="/general/committee_membership/committee_memberships_(....).htm">(.*?)</option>', body, re.I |  re.S):
      if id not in senate_ref:
        print("Unrecognized committee:", id, name)
        continue

      cx = senate_ref[id]
      is_joint = (id[0] == "J")

      # Scrape some metadata on the HTML page first.

      committee_url = "https://www.senate.gov/general/committee_membership/committee_memberships_%s.htm" % id
      print("[%s] Fetching members for %s (%s)" % (id, name, committee_url))
      body2 = download(committee_url, "committees/membership/senate/%s.html" % id, force)

      if not body2:
        print("\tcommittee page not good:", committee_url)
        continue

      m = re.search(r'<span class="contenttext"><a href="(http://(.*?).senate.gov/)">', body2, re.I)
      if m:
        cx["url"] = m.group(1)

      # Use the XML for the rest.

      print("\tDownloading XML...")
      committee_url = "https://www.senate.gov/general/committee_membership/committee_memberships_%s.xml" % id

      body3 = download(committee_url, "committees/membership/senate/%s.xml" % id, force)
      dom = lxml.etree.fromstring(body3.encode("utf8")) # must be bytes to parse if there is an encoding declaration inside the string

      cx["name"] = dom.xpath("committees/committee_name")[0].text
      if id[0] != "J" and id[0:2] != 'SC':
        cx["name"] = "Senate " + cx["name"]

      majority_party = dom.xpath("committees/majority_party")[0].text

      # update full committee members
      scrape_senate_members(
        dom.xpath("committees/members/member"),
        committee_membership.setdefault(id, []),
        majority_party, is_joint)

      # update subcommittees
      for subcom in dom.xpath("committees/subcommittee"):
        scid = subcom.xpath("committee_code")[0].text[4:]
        for sx in cx.get('subcommittees', []):
          if sx["thomas_id"] == scid:
            break
        else:
          print("Subcommittee not found, creating it", scid, name)
          sx = OrderedDict()
          sx['thomas_id'] = scid
          cx.setdefault('subcommittees', []).append(sx)

        # update metadata
        name = subcom.xpath("subcommittee_name")[0].text
        sx["name"] = name.strip()
        sx["name"] = re.sub(r"^\s*Subcommittee on\s*", "", sx["name"])
        sx["name"] = re.sub(r"\s+", " ", sx["name"])

        scrape_senate_members(
          subcom.xpath("members/member"),
          committee_membership.setdefault(id + scid, []),
          majority_party, is_joint)

  def scrape_senate_members(members, output_list, majority_party, is_joint):
    # Keep a copy of the previous membership.
    existing_members_data = list(output_list) # clone
    output_list.clear()

    # Update members.
    ids = set()
    count_by_party = { "majority": 0, "minority": 0 }
    for node in members:
      ids.add(scrape_senate_member(output_list, node, majority_party, is_joint, count_by_party, existing_members_data))

    # Purge non-members. Ignore House members of joint committees.
    i = 0
    while i < len(output_list):
      if output_list[i]['bioguide'] not in ids and output_list[i].get("chamber") in (None, "senate"):
        output_list[i:i+1] = []
      else:
        i += 1
    
    # sort by party, then by rank, since we get the nodes in the XML in a rough seniority order that ignores party
    output_list.sort(key = lambda e : (e["party"] != "majority", e["rank"]))

  def scrape_senate_member(output_list, membernode, majority_party, is_joint, count_by_party, existing_members_data):
    last_name = membernode.xpath("name/last")[0].text
    state = membernode.xpath("state")[0].text
    party = "majority" if membernode.xpath("party")[0].text == majority_party else "minority"
    title = membernode.xpath("position")[0].text
    if title == "Member": title = None
    if title == "Ranking": title = "Ranking Member"

    # look up senator by state and last name
    if (state, last_name) == ("NM", "Lujan"): last_name = "Luján"
    if (state, last_name) not in senators:
      print("\t[%s] Unknown member: %s" % (state, last_name))
      return None

    moc = senators[(state, last_name)]

    entry = OrderedDict()
    if 'official_full' in moc['name']:
      entry["name"] = moc['name']['official_full']
    else:
      print("missing name->official_full field for", moc['id']['bioguide'])
    entry["party"] = party
    count_by_party[party] += 1
    entry["rank"] = count_by_party[party]
    if title: entry["title"] = title
    entry.update(ids_from(moc["id"]))
    if is_joint: entry["chamber"] = "senate"

    # Look for an existing entry for this member and take
    # start_date and source from it, if set.
    for item in existing_members_data:
      if item["bioguide"] == entry["bioguide"]:
        for key in ("start_date", "source"):
            if key in item:
                entry[key] = item[key]

    output_list.append(entry)

    # Return bioguide ID of member added.
    return entry["bioguide"]

  # stick to a specific small set of official IDs to cross-link members
  # this limits the IDs from going out of control in this file, while
  # preserving us flexibility to be inclusive of IDs in the main leg files
  def ids_from(moc):
    ids = {}
    if "bioguide" in moc:
      ids["bioguide"] = moc["bioguide"]
    if len(ids) == 0:
      raise ValueError("Missing an official ID for this legislator, won't be able to link back")
    return ids

  # MAIN
  scrape_house()
  scrape_senate()

  sorted_committee_membership=OrderedDict()
  for comm in sorted(committee_membership.keys()):
    if (comm[:1] == "J"): #only joint committees have thomas ids starting with J
      sorted_committee_membership[comm] = sorted(committee_membership[comm], key=lambda entry: (entry["chamber"], entry["party"], entry["rank"]))
    else:
      sorted_committee_membership[comm] = sorted(committee_membership[comm], key=lambda entry: (entry["party"], entry["rank"]))

  save_data(sorted_committee_membership, "committee-membership-current.yaml")
  save_data(committees_current, "committees-current.yaml")

if __name__ == '__main__':
  run()
