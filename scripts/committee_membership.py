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


import re, lxml.html, lxml.etree
from collections import OrderedDict
import utils
from utils import download, load_data, save_data


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


  # map state/district to current senators because the Senate committee
  # membership data does not contain IDs for senators, and map to bioguide
  # IDs so we can copy forward the official_full name for House members
  legislators_current = load_data("legislators-current.yaml")
  senators = { }
  for moc in legislators_current:
    term = moc["terms"][-1]
    if term["type"] == "sen":
      for n in [moc["name"]] + moc.get("other_names", []):
        senators[(term["state"], n["last"])] = moc
  legislators_current = { moc["id"]["bioguide"]: moc for moc in legislators_current }


  # Scrape clerk.house.gov...
  def scrape_house():
    # clear out all of the existing House members of committees (i.e. all House committee membership
    # and the House part of Joint committee membership)
    for committee, members in committee_membership.items():
      for m in list(members): # must clone before editing list
        if committee[0] == "H" or m.get("chamber") == "house":
          members.remove(m)

    r = download("http://clerk.house.gov/xml/lists/MemberData.xml", "clerk_xml", force)
    dom = lxml.etree.fromstring(r.encode("latin-1")) # must be bytes to parse if there is an encoding declaration inside the string

    # Update committee metadata.
    def update_house_committee_metadata(xml_cx, cx, parentdict, is_subcommittee):
      sub_prefix = "sub" if is_subcommittee else ""

      if cx is None:
        # New committee.
        if not is_subcommittee:
          cx = {
            "type": "house",
            "thomas_id": "H" + xml_cx.attrib["type"][0].upper() + xml_cx.attrib["comcode"][0:2],
            "house_committee_id": xml_cx.attrib["comcode"][0:2]
          }
          house_ref[cx["house_committee_id"]] = cx
        else:
          cx = {
            "name": None, # placeholder so order is right
            "thomas_id": xml_cx.attrib["subcomcode"][2:]
          }
        parentdict.append(cx)

      cx["name"] = normalize_text(xml_cx.find(sub_prefix + "committee-fullname").text)
      if not is_subcommittee and not cx["name"].startswith("Joint "): cx["name"] = "House " + cx["name"]

      building = xml_cx.attrib[sub_prefix + "com-building-code"]
      if building == "C":
        building = "CAPITOL"
      #address format: 1301 LHOB; Washington, DC 20515-6001
      cx["address"] = xml_cx.attrib[sub_prefix + "com-room"] + " " + building \
         + "; Washington, DC " + xml_cx.attrib[sub_prefix + "com-zip"] \
         + (("-" + xml_cx.attrib[sub_prefix + "com-zip-suffix"]) if xml_cx.attrib[sub_prefix + "com-zip-suffix"] != "0" else "")
      cx["phone"] = "(202) " + xml_cx.attrib[sub_prefix + "com-phone"]

      if not is_subcommittee:
        for xml_sx in xml_cx.findall("subcommittee"):
          sxx = [s for s in cx["subcommittees"] if s["thomas_id"] == xml_sx.attrib["subcomcode"][2:]]
          update_house_committee_metadata(xml_sx, sxx[0] if len(sxx) > 0 else None, cx["subcommittees"], True)

    committees = dom.xpath("/MemberData/committees")[0]
    for xml_cx in committees.findall("committee"):
      house_committee_id = xml_cx.attrib["comcode"][0:2]
      update_house_committee_metadata(xml_cx, house_ref.get(house_committee_id), committees_current, False)

    # Determine which party is in the majority. Only the majority
    # party holds chair positions. At least one should have the
    # position Chair.
    house_majority_caucus = dom.xpath("string(/MemberData/members/member[committee-assignments/committee[@leadership='Chair']]/member-info/caucus)")

    for xml_member in dom.xpath("/MemberData/members/member"):
      bioguide_id = xml_member.xpath("member-info/bioguideID")[0].text
      if not bioguide_id: #sometimes the xml has vacancies as blanks
        continue

      # Although there is a name in the XML data, for consistency use the one we
      # have in legislators-current.yaml, if one is set.
      try:
        official_name = legislators_current[bioguide_id]["name"]["official_full"]
      except KeyError:
        official_name = xml_member.xpath("member-info/official-name")[0].text

      #is using caucus better than using party?
      caucus = xml_member.xpath("member-info/caucus")[0].text
      party = "majority" if caucus == house_majority_caucus else "minority"

      #for each committee or subcommittee membership
      for cm in xml_member.xpath("committee-assignments/committee|committee-assignments/subcommittee"):
        if "comcode" in cm.attrib:
          house_committee_id = cm.attrib["comcode"][:2]
          if house_committee_id == "HL": continue # this doesn't appear to be a committee and seems like a data error
          thomas_committee_id = house_ref[house_committee_id]["thomas_id"]
        elif "subcomcode" in cm.attrib:
          house_committee_id = cm.attrib["subcomcode"][:2]
          thomas_committee_id = house_ref[house_committee_id]["thomas_id"] + cm.attrib["subcomcode"][2:]
        else:
          continue # some nodes are invalid

        membership = OrderedDict()
        membership["name"] = official_name
        membership["party"] = party
        membership["rank"] = int(cm.attrib["rank"])

        if "leadership" in cm.attrib:
          membership["title"] = cm.attrib["leadership"] # TODO .replace("woman", "").replace("man", "")
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

      cx["name"] = normalize_text(dom.xpath("committees/committee_name")[0].text)
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
        sx["name"] = normalize_text(name)
        sx["name"] = re.sub(r"^\s*Subcommittee on\s*", "", sx["name"])
        sx["name"] = re.sub(r"\s+", " ", sx["name"])

        scrape_senate_members(
          subcom.xpath("members/member"),
          committee_membership.setdefault(id + scid, []),
          majority_party, is_joint)

  def scrape_senate_members(members, output_list, majority_party, is_joint):
    # Keep a copy of the previous membership, and then clear the Senate members
    # of the committee.
    existing_members_data = list(output_list) # clone
    if not is_joint:
      output_list.clear()
    else:
      for m in list(output_list): # must clone before editing list
        if m.get("chamber") == "senate":
          output_list.remove(m)

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

  # ensure each committee has members in a stable, sorted order
  for comm, mbrs in committee_membership.items():
    # joint committees also have to sort by chamber
    if comm[0] == "J":
      mbrs.sort(key=lambda entry: (entry["party"] == "minority", entry["rank"], entry["chamber"] != "senate"))

    # Senate and House committees have different sort orders to match
    # earlier data, but there's no particular reason for this
    elif comm[0] == "S":
      mbrs.sort(key=lambda entry: (entry["party"] == "minority", entry["rank"]))
    else:
      mbrs.sort(key=lambda entry: (entry["rank"], entry["party"] == "minority"))

  save_data(committee_membership, "committee-membership-current.yaml")
  save_data(committees_current, "committees-current.yaml")


def normalize_text(text):
  # Remove leading and trailing whitespace (coul also use .strip()).
  text = re.sub(r"^\s+|\s+$", "", text)

  # Remove double spaces and turn all internal whitespace into spaces.
  text = re.sub(r"\s+", " ", text)

  return text


if __name__ == '__main__':
  run()
