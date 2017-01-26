#!/usr/bin/env python

# Use the NYTimes API to get House committee information.
# When we wrote this script we believed the House Clerk was
# not yet making this info available.

import utils
import json
import copy
from utils import download, load_data, save_data

committee_membership = { }

committees_current = load_data("committees-current.yaml")
memberships_current = load_data("committee-membership-current.yaml")

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

congress = 113

# map house/senate committee IDs to their dicts
all_ids = []

house_ref = { }
for cx in committees_current:
  if cx["type"] == "house":
    house_ref[cx["thomas_id"]] = cx
    all_ids.append(cx['thomas_id'])

senate_ref = { }
for cx in committees_current:
  if cx["type"] == "senate":
    senate_ref[cx["thomas_id"]] = cx
    all_ids.append(cx['thomas_id'])

# map people by their bioguide ID
y = load_data("legislators-current.yaml")
by_bioguide = { }
for m in y:
  bioguide = m['id']['bioguide']
  by_bioguide[bioguide] = m


# load in committees from the NYT Congress API (API key not kept in source control)
api_key = open("cache/nyt_api_key").read() # file's whole body is the api key

url = "http://api.nytimes.com/svc/politics/v3/us/legislative/congress/%i/house/committees.json?api-key=%s" % (congress, api_key)

body = download(url, "committees/membership/nyt-house.json", force)
committees = json.loads(body)['results'][0]['committees']

for committee in committees:
  committee_id = committee['id']

  committee_url = "http://api.nytimes.com/svc/politics/v3/us/legislative/congress/%i/house/committees/%s.json?api-key=%s" % (congress, committee_id, api_key)

  # current disagreement between THOMAS and NYT (but use HSIG in URL above)
  if committee_id == "HSIG":
    committee_id = "HLIG"

  if committee_id not in all_ids:
    continue

  committee_party = committee['chair_party']

  committee_body = download(committee_url, "committees/membership/house/%s.json" % committee_id, force)
  members = json.loads(committee_body)['results'][0]['current_members']

  committee_membership[committee_id] = []
  for member in members:
    bioguide_id = member['id']

    print("[{}] {}".format(committee_id, bioguide_id))

    if bioguide_id not in by_bioguide:
      continue

    legislator = by_bioguide[bioguide_id]
    # last_term = legislator['terms'][-1]

    if member['party'] == committee_party:
      party = "majority"
    else:
      party = "minority"

    # this really shouldn't be calculated, but for now it's what we've got
    rank = int(member['rank_in_party'])
    if rank == 1:
      if party == "majority":
        title = "Chair"
      else:
        title = "Ranking Member"
    else:
      title = None

    details = {
      'name': legislator['name']['official_full'],
      'party': party,
      'rank': rank,
      'bioguide': bioguide_id,
      'thomas': legislator['id']['thomas']
    }

    if title:
      details['title'] = title

    committee_membership[committee_id].append(details)

# sort members to put majority party first, then order by rank
# (fixing the order makes for better diffs)
for c in committee_membership.values():
  c.sort(key = lambda m : (m["party"]=="minority", m["rank"]))

# preserve senate memberships
senate_membership = {}
for committee_id in memberships_current:
  if not committee_id.startswith("H"):
    committee_membership[committee_id] = copy.deepcopy(memberships_current[committee_id])

print("Saving committee memberships...")
save_data(committee_membership, "committee-membership-current.yaml")
