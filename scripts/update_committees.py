#!/usr/bin/env python

# Parse the THOMAS advanced search page for a list of all committees
# and subcommittees. While we surely have comprehensive info on current
# committees, we may not have comprehensive information on historical
# committees/subcommittees or current subcommittees (because there are
# so many). The THOMAS pages do not list joint committees, however.

import re, itertools
from collections import OrderedDict
from utils import download, load_data, save_data


committees_historical = load_data("committees-historical.yaml")
committees_current = load_data("committees-current.yaml")

CURRENT_CONGRESS = 112

# map thomas_id's to their dicts
committees_historical_ref = { }
for cx in committees_historical: committees_historical_ref[cx["thomas_id"]] = cx
committees_current_ref = { }
for cx in committees_current: committees_current_ref[cx["thomas_id"]] = cx

# clear out some fields that we'll set again
for cx in itertools.chain(committees_historical, committees_current):
  if "congresses" in cx: del cx["congresses"]
  if "names" in cx: del cx["names"]
  for sx in cx.get('subcommittees', []):
    if "congresses" in sx: del sx["congresses"]
    if "names" in sx: del sx["names"]

for congress in range(93, CURRENT_CONGRESS+1):
  print congress, '...'

  url = "http://thomas.loc.gov/home/LegislativeData.php?&n=BSS&c=%d" % congress
  body = download(url, "committees/structure/%d.html" % congress)

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
          
      cx.setdefault('congresses', []).append(str(congress))
      cx.setdefault('names', {})[congress] = name

# format some fields
def format_name_info(names):
  ret = []
  prev = None
  for c in sorted(names.keys()):
    if prev and prev[1] == c-1 and prev[2] == names[c]:
      prev[1] = c
    else:
      prev = [c, c, names[c]]
      ret.append(prev)
  return OrderedDict((d1 if d1 == d2 else "%d-%d" % (d1, d2), name) for (d1, d2, name) in ret)

for cx in itertools.chain(committees_historical, committees_current):
  if "congresses" in cx: cx["congresses"] = ",".join(cx["congresses"])
  if "names" in cx: cx["names"] = format_name_info(cx["names"])
  for sx in cx.get('subcommittees', []):
    if "congresses" in sx: sx["congresses"] = ",".join(sx["congresses"])
    if "names" in sx: sx["names"] = format_name_info(sx["names"])

save_data(committees_historical, "committees-historical.yaml")
save_data(committees_current, "committees-current.yaml")