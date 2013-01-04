#!/usr/bin/env python

# gets fundamental information for every member with a bioguide ID:
# first name, nickname, middle name, last name, name suffix
# birthday

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import lxml.html, StringIO
import datetime
import csv, re
import utils
from utils import download, load_data, save_data, parse_date

def birthday_for(string):
  pattern = "born(.+?)((?:January|February|March|April|May|June|July|August|September|October|November|December),? \\d{1,2},? \\d{4})"
  match = re.search(pattern, string, re.I)
  if match:
    if len(re.findall(";", match.group(1))) <= 1:
      return match.group(2).strip()

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


# optionally focus on one legislator

bioguide = utils.flags().get('bioguide', None)
if bioguide:
  bioguides = [bioguide]
else:
  bioguides = by_bioguide.keys()

warnings = []
missing = []
count = 0

for bioguide in bioguides:
  url = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=%s" % bioguide
  cache = "legislators/bioguide/%s.html" % bioguide
  try:
    body = download(url, cache, force)
    dom = lxml.html.parse(StringIO.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    print "Error parsing: ", url
    continue

  if len(dom.cssselect("title")) == 0:
    print "[%s] No page for this bioguide!" % bioguide
    missing.append(bioguide)
    continue

  try:
    name = dom.cssselect("p font")[0]
    main = dom.cssselect("p")[0]
  except IndexError:
    print "[%s] Missing name or content!" % bioguide
    exit(0)

  name = name.text_content().strip()
  main = main.text_content().strip().replace("\n", " ").replace("\r", " ")
  main = re.sub("\s+", " ", main)

  birthday = birthday_for(main)
  if not birthday:
    print "[%s] NO BIRTHDAY :(\n\n%s" % (bioguide, main)
    warnings.append(bioguide)
    continue

  if debug:
    print "[%s] Found birthday: %s" % (bioguide, birthday)

  try:
    birthday = datetime.datetime.strptime(birthday.replace(",", ""), "%B %d %Y")
  except ValueError:
    print "[%s] BAD BIRTHDAY :(\n\n%s" % (bioguide, main)
    warnings.append(bioguide)
    continue

  birthday = "%04d-%02d-%02d" % (birthday.year, birthday.month, birthday.day)
  
  # some older legislators may not have a bio section yet
  if not by_bioguide[bioguide].has_key("bio"):
    by_bioguide[bioguide]["bio"] = {}

  by_bioguide[bioguide]["bio"]["birthday"] = birthday
  count = count + 1

print "Saving data to %s..." % filename
save_data(legislators, filename)


print
if warnings:
  print "Missed %d birthdays: %s" % (len(warnings), str.join(", ", warnings))

if missing:
  print "Missing a page for %d bioguides: %s" % (len(missing), str.join(", ", warnings))

print "Saved %d legislators to %s" % (count, filename)