#!/usr/bin/env python

# Stores a house_history ID for all legislators that don't yet
# have one, by scraping history.house.gov.

import lxml.html, io
import requests
from utils import load_data, save_data
import sys

def run():
  # load legislators YAML files
  yamlfiles = { }
  for fn in ('historical', 'current'):
    fn = 'legislators-%s.yaml' % fn
    print("Loading %s..." % fn)
    yamlfiles[fn] = load_data(fn)

  # reoriented cache to access by bioguide ID
  by_bioguide = { }
  known_house_history_ids = set()
  for legislators in yamlfiles.values():
    for m in legislators:
      if "bioguide" in m["id"]:
        by_bioguide[m["id"]["bioguide"]] = m
      if "house_history" in m["id"]:
        known_house_history_ids.add(m["id"]["house_history"])
  count = 0

  # scrape history.house.gov
  if len(sys.argv) == 1:
    id_range = range(22000, 25000)
  else:
    id_range = [int(arg) for arg in sys.argv[1:]]
  for id in id_range:
    # skip known IDs
    if id in known_house_history_ids:
      continue
    print(id)
    bioguide_id = get_bioguide_for_house_history_id(id)
    if bioguide_id and bioguide_id in by_bioguide:
      print(id, bioguide_id)
      by_bioguide[bioguide_id]["id"]["house_history"] = id
      count = count + 1

  # write YAML files to disk
  for filename, legislators in yamlfiles.items():
    print("Saving data to %s..." % filename)
    save_data(legislators, filename)

  # how many updates did we make?
  print("Saved %d legislators" % count)

def get_bioguide_for_house_history_id(id):
    url = "http://history.house.gov/People/Detail/%s" % id
    r = requests.get(url, allow_redirects=False)
    if r.status_code == 200:
        dom = lxml.html.parse(io.StringIO(r.text)).getroot()
        try:
            bioguide_link = dom.cssselect("a.view-in-bioguide")[0].get('href')
            return bioguide_link.split('=')[1]
        except:
            return None
    else:
        return None

if __name__ == '__main__':
  run()