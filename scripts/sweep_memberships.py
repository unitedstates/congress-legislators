#!/usr/bin/env python

import re, lxml.html, lxml.etree, io, datetime
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, parse_date, CURRENT_CONGRESS


# load in members, orient by bioguide ID
print("Loading current legislators...")
current = load_data("legislators-current.yaml")

current_bioguide = { }
for m in current:
  if "bioguide" in m["id"]:
    current_bioguide[m["id"]["bioguide"]] = m

# go over current members, remove out-of-office people
membership_current = load_data("committee-membership-current.yaml")
for committee_id in list(membership_current.keys()):
  print("[%s] Looking through members..." % committee_id)

  for member in membership_current[committee_id]:
    if member["bioguide"] not in current_bioguide:
      print("\t[%s] Ding ding ding! (%s)" % (member["bioguide"], member["name"]))
      membership_current[committee_id].remove(member)

print("Saving current memberships...")
save_data(membership_current, "committee-membership-current.yaml")