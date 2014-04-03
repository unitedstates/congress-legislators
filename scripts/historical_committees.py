#!/usr/bin/env python

# Parse the THOMAS advanced search page for a list of all committees
# and subcommittees from the 93rd Congress forward and store them in
# the committees-historical.yaml file. It will include current committees
# as well.

import re
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, CURRENT_CONGRESS

def run():
  committees_historical = load_data("committees-historical.yaml")

  # default to not caching
  flags = utils.flags()
  cache = flags.get('cache', False)
  force = not cache


  # map thomas_id's to their dicts
  committees_historical_ref = { }
  for cx in committees_historical: committees_historical_ref[cx["thomas_id"]] = cx


  # pick the range of committees to get
  single_congress = flags.get('congress', False)
  if single_congress:
    start_congress = int(single_congress)
    end_congress = int(single_congress) + 1
  else:
    start_congress = 93
    end_congress = CURRENT_CONGRESS + 1


  for congress in range(start_congress, end_congress):
    print(congress, '...')

    url = "http://thomas.loc.gov/home/LegislativeData.php?&n=BSS&c=%d" % congress
    body = download(url, "committees/structure/%d.html" % congress, force)

    for chamber, options in re.findall('>Choose (House|Senate) Committees</option>(.*?)</select>', body, re.I | re.S):
      for name, id in re.findall(r'<option value="(.*?)\{(.*?)}">', options, re.I | re.S):
        id = str(id).upper()
        name = name.strip().replace("  ", " ") # weirdness
        if id.endswith("00"):
        	# This is a committee.
          id = id[:-2]

          if id in committees_historical_ref:
            # Update existing record.
            cx = committees_historical_ref[id]

          else:
            # Create a new record.
            cx = OrderedDict()
            committees_historical_ref[id] = cx
            cx['type'] = chamber.lower()
            if id[0] != "J": # Joint committees show their full name, otherwise they show a partial name
              cx['name'] = chamber + " Committee on " + name
            else:
              cx['name'] = name
            cx['thomas_id'] = id
            committees_historical.append(cx)

        else:
          # This is a subcommittee. The last two characters are the subcommittee code.

          # Get a reference to the parent committee.
          if id[:-2] not in committees_historical_ref:
            print("Historical committee %s %s is missing!" % (id, name))
            continue

          cx = committees_historical_ref[id[:-2]]

          # Get a reference to the subcommittee.
          for sx in cx.setdefault('subcommittees', []):
            if sx['thomas_id'] == id[-2:]:
              # found existing record
              cx = sx
              break
          else:
            # 'break' not executed, so create a new record
            sx = OrderedDict()
            sx['name'] = name
            sx['thomas_id'] = id[-2:]
            cx['subcommittees'].append(sx)
            cx = sx

        cx.setdefault('congresses', [])
        cx.setdefault('names', {})

        # print "[%s] %s (%s)" % (cx['thomas_id'], cx['name'], congress)

        if congress not in cx['congresses']:
          cx['congresses'].append(congress)

        cx['names'][congress] = name

  # TODO
  # after checking diff on first commit, we should re-sort
  #committees_historical.sort(key = lambda c : c["thomas_id"])
  #for c in committees_historical:
  #  c.get("subcommittees", []).sort(key = lambda s : s["thomas_id"])

  save_data(committees_historical, "committees-historical.yaml")

if __name__ == '__main__':
  run()