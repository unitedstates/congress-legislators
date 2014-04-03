#!/usr/bin/env python

# Update current THOMAS IDs using beta.congress.gov. Congressmen's
# IDs are updated directly. For Senators, we just print out new
# IDs because name matching is hard.

import lxml.html, io, urllib.request, urllib.parse, urllib.error
import re
import utils
from utils import download, load_data, save_data

def run():
  CONGRESS_ID = "113th Congress (2013-2014)" # the query string parameter

  # constants
  state_names = {"Alabama": "AL", "Alaska": "AK", "American Samoa": "AS", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Guam": "GU", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Northern Mariana Islands": "MP", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Puerto Rico": "PR", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virgin Islands": "VI", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache

  # load in current members
  y = load_data("legislators-current.yaml")
  by_district = { }
  existing_senator_ids = set()
  for m in y:
    last_term = m['terms'][-1]
    if last_term['type'] == 'rep':
      full_district = "%s%02d" % (last_term['state'], int(last_term['district']))
      by_district[full_district] = m
    elif last_term['type'] == 'sen':
      if "thomas" in m["id"]:
        existing_senator_ids.add(m["id"]["thomas"])

  seen_ids = set()
  for chamber in ("House of Representatives", "Senate"):
    url = "http://beta.congress.gov/members?pageSize=500&Legislative_Source=Member+Profiles&Congress=%s&Chamber_of_Congress=%s" % (
      urllib.parse.quote_plus(CONGRESS_ID), urllib.parse.quote_plus(chamber))
    cache = "congress.gov/members/%s-%s.html" % (CONGRESS_ID, chamber)
    try:
      body = download(url, cache, force)
      dom = lxml.html.parse(io.StringIO(body)).getroot()
    except lxml.etree.XMLSyntaxError:
      print("Error parsing: ", url)
      continue

    for node in dom.xpath("//ul[@class='results_list']/li"):
      thomas_id = "%05d" % int(re.search("/member/.*/(\d+)$", node.xpath('h2/a')[0].get('href')).group(1))

      # THOMAS misassigned these 'new' IDs to existing individuals.
      if thomas_id in ('02139', '02132'):
        continue

      name = node.xpath('h2/a')[0].text

      state = node.xpath('div[@class="memberProfile"]/table/tbody/tr[1]/td')[0].text.strip()
      state = state_names[state]

      if chamber == "House of Representatives":
        # There's enough information to easily pick out which Member this refers to, so write it
        # directly to the file.
        district = node.xpath('div[@class="memberProfile"]/table/tbody/tr[2]/td')[0].text.strip()
        if district == "At Large": district = 0
        district = "%02d" % int(district)

        if state + district not in by_district:
          print(state + district + "'s", name, "appears on Congress.gov but the office is vacant in our data.")
          continue

        if state + district in seen_ids:
          print("Congress.gov lists two people for %s%s!" % (state, district))
        seen_ids.add(state+district)

        by_district[state + district]["id"]["thomas"] = thomas_id

      elif chamber == "Senate":
        # For senators we'd have to match on name or something else, so that's too difficult.
        # Just look for new IDs.
        if thomas_id not in existing_senator_ids:
          print("Please manually set", thomas_id, "for", name, "from", state)

  save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()