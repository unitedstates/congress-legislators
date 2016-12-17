#!/usr/bin/env python

from utils import load_data, save_data

def run():
    # load in members, orient by bioguide ID
    print("Loading current legislators...")
    current = load_data("legislators-current.yaml")

    current_bioguide = { }
    for m in current:
      if "bioguide" in m["id"]:
        current_bioguide[m["id"]["bioguide"]] = m

    # remove out-of-office people from current committee membership
    print("Sweeping committee membership...")
    membership_current = load_data("committee-membership-current.yaml")
    for committee_id in list(membership_current.keys()):
      for member in membership_current[committee_id]:
        if member["bioguide"] not in current_bioguide:
          print("\t[%s] Ding ding ding! (%s)" % (member["bioguide"], member["name"]))
          membership_current[committee_id].remove(member)
    save_data(membership_current, "committee-membership-current.yaml")

    # remove out-of-office people from social media info
    print("Sweeping social media accounts...")
    socialmedia_current = load_data("legislators-social-media.yaml")
    for member in list(socialmedia_current):
      if member["id"]["bioguide"] not in current_bioguide:
        print("\t[%s] Ding ding ding! (%s)" % (member["id"]["bioguide"], member["social"]))
        socialmedia_current.remove(member)
    save_data(socialmedia_current, "legislators-social-media.yaml")

if __name__ == '__main__':
  run()
