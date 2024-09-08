#!/usr/bin/env python

# Uses https://www.house.gov/representatives/ to scrape official member websites.
# Only known source.

# Assumptions:
#  member's state and district fields are present and accurate.
#  member's most recent term in the terms field is their current one.

import lxml.html, io, urllib.request, urllib.error, urllib.parse
import re
import utils
from utils import load_data, save_data, states as state_names
from feedfinder2 import find_feeds

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
  for state in sorted(states):
    state_name = state_names[state].lower().replace(' ', '-')
    table = dom.cssselect("table.table caption#state-%s" % state_name)[0].getparent()
    rows = table.cssselect("tbody tr")

    for row in rows:
      cells = row.cssselect("td")
      if not cells:
        continue

      district = str(cells[0].text_content()).strip()
      if (
        (district == "At Large")
        or (district == "Delegate")
        or (district == "Resident Commissioner")
      ):
        district = 0
      else:
        district = int(re.sub(r'[^\d]', '', district))

      url = cells[1].cssselect("a")[0].get("href")
      original_url = url
      print(url)

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

      # find rss feed
      feeds = find_feeds(url)

      if state == "AQ":
        state = "AS"
      full_district = "%s%02d" % (state, int(district))
      if full_district in by_district:
        print("[%s] %s %s" % (full_district, url, "" if url == original_url.rstrip("/") else (" <= " + original_url)))
        by_district[full_district]['terms'][-1]['url'] = url
        if len(feeds) > 0:
          rss_url = feeds[0]
          by_district[full_district]['terms'][-1]['rss_url'] = rss_url
      else:
        print("[%s] No current legislator" % full_district)

      count += 1

  print("Processed %i people rows on House listing." % count)

  print("Saving data...")
  save_data(current, "legislators-current.yaml")

if __name__ == '__main__':
  run()
