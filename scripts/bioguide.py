#!/usr/bin/env python

# gets fundamental information for every member with a bioguide ID:
# first name, nickname, middle name, last name, name suffix
# birthday

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import lxml.html, StringIO
import time
import csv, re
import utils
from utils import download, load_data, save_data, parse_date


debug = utils.flags().get('debug', False)

# default to caching
cache = utils.flags().get('cache', True)
force = not cache

# pick either current or historical
current_flag = utils.flags().get('current', True)
historical_flag = utils.flags().get('historical', False)

if current_flag:
  filename = "legislators-current.yaml"
elif historical_flag:
  filename = "legislators-historical.yaml"
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


# optionally focus on one legislator

bioguide = utils.flags().get('bioguide', None)
if bioguide:
  bioguides = [bioguide]
else:
  bioguides = by_bioguide.keys()

warnings = []

for bioguide in bioguides:
  url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
  cache = "legislators/bioguide/%s.html" % bioguide
  try:
    body = download(url, cache, force)
    dom = lxml.html.parse(StringIO.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    print "Error parsing: ", url
    continue

  name = dom.cssselect("p font")[0]
  main = dom.cssselect("p")[0]

  if (name is None) or (main is None):
    print "[%s] Missing name or content!" % bioguide
    exit(0)

  name = name.text_content().strip()
  main = main.text_content().strip().replace("\n", " ").replace("\r", " ")
  main = re.sub("\s+", " ", main)

  birthday_matches = re.search("born.+?((?:January|February|March|April|May|June|July|August|September|October|November|December) .+?\\d{4})", main, re.I)
  if not birthday_matches:
    print "[%s] NO BIRTHDAY :(\n\n%s" % (bioguide, main)
    warnings.append(bioguide)
    continue

  birthday = birthday_matches.group(1).strip()
  if debug:
    print "[%s] Found birthday: %s" % (bioguide, birthday)

  birthday = time.strftime("%Y-%m-%d", time.strptime(birthday, "%B %d, %Y"))
  by_bioguide[bioguide]["bio"]["birthday"] = birthday

print "Saving data to %s..." % filename
save_data(legislators, filename)


if warnings:
  print "\nMissed %d birthdays: %s" % (len(warnings), str.join(", ", warnings))