#!/usr/bin/env python

# Uses http://house.gov/representatives/ to scrape official member websites. 
# Only known source.

# Assumptions:
#  member's state and district fields are present and accurate.
#  member's most recent term in the terms field is their current one.

import lxml.html, StringIO, urllib2
import re
import utils
from utils import download, load_data, save_data, parse_date

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache


states = []
current = load_data("legislators-current.yaml")
by_district = { }
for m in current:
  last_term = m['terms'][-1]
  if last_term['type'] != 'sen':
    state = last_term['state']
    
    full_district = "%s%02d" % (state, int(last_term['district']))
    by_district[full_district] = m

    if not state in states:
      # house lists AS (American Samoa) as AQ, awesome
      if state == "AS":
        state = "AQ"
      states.append(state)

destination = "legislators/house.html"
url = "http://house.gov/representatives/"
body = utils.download(url, destination, force)
if not body:
  print "Couldn't download House listing!"
  exit(0)

try:
  dom = lxml.html.parse(StringIO.StringIO(body.decode("utf-8"))).getroot()
except lxml.etree.XMLSyntaxError:
  print "Error parsing House listing!"
  exit(0)


# process:
#   go through every state in our records, fetching that state's table
#   go through every row after the first, pick the district to isolate the member
#   pluck out the URL, update that member's last term's URL
count = 0
for state in states:
  rows = dom.cssselect("h2#state_%s+table tr" % state.lower())

  for row in rows:
    cells = row.cssselect("td")
    if not cells:
      continue

    district = unicode(cells[0].text_content())
    if district == "At Large":
      district = 0

    url = cells[1].cssselect("a")[0].get("href")

    # hit the URL to resolve any redirects to get the canonical URL,
    # since the listing on house.gov sometimes gives URLs that redirect.
    resp = urllib2.urlopen(url)
    url = resp.geturl()

    # kill trailing slashes
    url = re.sub("/$", "", url)

    if state == "AQ":
      state = "AS"
    full_district = "%s%02d" % (state, int(district))
    if by_district.has_key(full_district):
      by_district[full_district]['terms'][-1]['url'] = url
    else:
      print "[%s] No current legislator" % full_district

    count += 1

print "Processed %i people rows on House listing." % count

print "Saving data..."
save_data(current, "legislators-current.yaml")