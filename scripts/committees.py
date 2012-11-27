#!/usr/bin/env python

# Parse the THOMAS advanced search page for a list of all committees
# and subcommittees. While we surely have comprehensive info on current
# committees, we may not have comprehensive information on historical
# committees/subcommittees or current subcommittees (because there are
# so many). The THOMAS pages do not list joint committees, however.

import re, itertools
from collections import OrderedDict
import utils
from utils import download, load_data, save_data, CURRENT_CONGRESS

committees_historical = load_data("committees-historical.yaml")
committees_current = load_data("committees-current.yaml")


# default to not caching
flags = utils.flags()
cache = flags.get('cache', False)
force = not cache


# map thomas_id's to their dicts
committees_historical_ref = { }
for cx in committees_historical: committees_historical_ref[cx["thomas_id"]] = cx
committees_current_ref = { }
for cx in committees_current: committees_current_ref[cx["thomas_id"]] = cx


# pick the range of committees to get
single_congress = flags.get('congress', False)
if single_congress:
  start_congress = int(single_congress)
  end_congress = int(single_congress) + 1
else:
  start_congress = 93
  end_congress = CURRENT_CONGRESS + 1


for congress in range(start_congress, end_congress):
  print congress, '...'

  url = "http://thomas.loc.gov/home/LegislativeData.php?&n=BSS&c=%d" % congress
  body = download(url, "committees/structure/%d.html" % congress, force)

  for chamber, options in re.findall('>Choose (House|Senate) Committees</option>(.*?)</select>', body, re.I | re.S):
    for name, id in re.findall(r'<option value="(.*?)\{(.*?)}">', options, re.I | re.S):
      id = str(id).upper()
      name = name.strip().replace("  ", " ") # weirdness
      if id.endswith("00"):
      	# This is a committee.
        id = id[:-2]
        
        if id in committees_current_ref:
          # We know it as a current committee.
          cx = committees_current_ref[id]
          
        elif congress == CURRENT_CONGRESS:
          # It is an error if it is missing from the committees_current file.
          print "Committee %s %s is missing!" % (id, name)
          continue
           
        elif id in committees_historical_ref:
          # We know it as a historical committee.
          cx = committees_historical_ref[id]
        
        else:
          # This is a historical committee that we don't have a record for.
          cx = OrderedDict()
          committees_historical_ref[id] = cx
          cx['type'] = chamber.lower()
          if id[0] != "J":
            cx['name'] = chamber + " Committee on " + name
          else:
            cx['name'] = name
          cx['thomas_id'] = id
          committees_historical.append(cx)
          
      else:
        # This is a subcommittee. The last two characters are the subcommittee
        # code.

        # Get a reference to the parent committee.
        if id[:-2] in committees_current_ref:
          cx = committees_current_ref[id[:-2]]
        elif congress == CURRENT_CONGRESS:
          print "Committee %s %s is missing!" % (id, name)
          continue
        elif id[:-2] in committees_historical_ref:
          cx = committees_historical_ref[id[:-2]]
        else:
          print "Historical committee %s %s is missing!" % (id, name)
          continue
          
        # Get a reference to the subcommittee.
        for sx in cx.setdefault('subcommittees', []):
          if sx['thomas_id'] == id[-2:]:
            cx = sx
            break
        else:
          sx = OrderedDict()
          sx['name'] = name
          sx['thomas_id'] = id[-2:]
          cx['subcommittees'].append(sx)
          cx = sx
          
      cx.setdefault('congresses', [])
      cx.setdefault('names', {})

      print "[%s] %s (%s)" % (cx['thomas_id'], cx['name'], congress)

      if congress not in cx['congresses']:
        cx['congresses'].append(congress)
      
      cx['names'][congress] = name
    

save_data(committees_historical, "committees-historical.yaml")
save_data(committees_current, "committees-current.yaml")