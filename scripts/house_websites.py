#!/usr/bin/env python

# Uses https://www.house.gov/representatives/ to scrape official member websites.
# Only known source.

# Assumptions:
#  member's state and district fields are present and accurate.
#  member's most recent term in the terms field is their current one.

import lxml.html, io, urllib.request, urllib.error, urllib.parse
import re
import utils
from utils import load_data, save_data

def run():

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
  url = "https://www.house.gov/representatives/"
  body = utils.download(url, destination, force)
  if not body:
    print("Couldn't download House listing!")
    exit(0)

  try:
    dom = lxml.html.parse(io.StringIO(body)).getroot()
  except lxml.etree.XMLSyntaxError:
    print("Error parsing House listing!")
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

      district = str(cells[0].text_content())
      if district == "At Large":
        district = 0

      url = cells[1].cssselect("a")[0].get("href")

      # The House uses subdomains now, and occasionally the directory
      # uses URLs with some trailing redirected-to page, like /home.
      # We can safely use the subdomain as the root, to be future-proof
      # against redirects changing mid-session.

      # We should still follow any redirects, and not just trust the
      # directory to have the current active subdomain. As an example,
      # the directory lists randyforbes.house.gov, which redirects to
      # forbes.house.gov.
      resp = urllib.request.urlopen(url)
      url = resp.geturl()

      # kill everything after the domain
      url = re.sub(".gov/.*$", ".gov", url)

      if state == "AQ":
        state = "AS"
      full_district = "%s%02d" % (state, int(district))
      if full_district in by_district:
        print("[%s] %s" % (full_district, url))
        by_district[full_district]['terms'][-1]['url'] = url
      else:
        print("[%s] No current legislator" % full_district)

      count += 1

  print("Processed %i people rows on House listing." % count)

  print("Saving data...")
  save_data(current, "legislators-current.yaml")

if __name__ == '__main__':
  run()