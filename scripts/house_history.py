#!/usr/bin/env python

# gets bioguide id for every member with a house history ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)
#  --bioguide: do *only* a single legislator

import lxml.html, StringIO
import datetime
import re
import utils
import requests
from utils import download, load_data, save_data, parse_date

debug = utils.flags().get('debug', False)

# default to caching
cache = utils.flags().get('cache', True)
force = not cache

# pick either current or historical
# order is important here, since current defaults to true
if utils.flags().get('historical', False):
  filename = "legislators-historical.yaml"
elif utils.flags().get('current', True):
  filename = "legislators-current.yaml"
else:
  print "No legislators selected."
  exit(0)

print "Loading %s..." % filename
legislators = load_data(filename)

# reoriented cache to access by bioguide ID
by_bioguide = { }
for m in legislators:
  if m["id"].has_key("bioguide"):
    by_bioguide[m["id"]["bioguide"]] = m

count = 0

for id in range(8245,21131):
  print id
  url = "http://history.house.gov/People/Detail/%s" % id
  r = requests.get(url, allow_redirects=False)
  if r.status_code == 200:
      dom = lxml.html.parse(StringIO.StringIO(r.text)).getroot()
      try:
          bioguide_link = dom.cssselect("a.view-in-bioguide")[0].get('href')
          bioguide_id = bioguide_link.split('=')[1]
          by_bioguide[bioguide_id]["id"]["house_history"] = id
          count = count + 1
      except:
          continue
  else:
      continue

print "Saving data to %s..." % filename
save_data(legislators, filename)

print "Saved %d legislators to %s" % (count, filename)