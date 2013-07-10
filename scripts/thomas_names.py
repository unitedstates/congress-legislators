#!/usr/bin/env python

# Update current beta names using beta.congress.gov. We cannot use the site beta without the name and the thomas id!

import lxml.html, StringIO, urllib
import re, sys
from datetime import date, datetime
import utils
from utils import download, load_data, save_data, parse_date

CONGRESS_ID = "113th Congress (2013-2014)" # the query string parameter

# constants
state_names = {"Alabama": "AL", "Alaska": "AK", "American Samoa": "AS", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Guam": "GU", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Northern Mariana Islands": "MP", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Puerto Rico": "PR", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virgin Islands": "VI", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

# load in current members
y = load_data("legislators-current.yaml")
by_district = { }
by_thomas = { }
existing_senator_ids = set()
for m in y:
  last_term = m['terms'][-1]
  by_thomas[m["id"]["thomas"]]=m
  if last_term['type'] == 'rep':
    full_district = "%s%02d" % (last_term['state'], int(last_term['district']))
    by_district[full_district] = m
  elif last_term['type'] == 'sen':
    if "thomas" in m["id"]:
      existing_senator_ids.add(m["id"]["thomas"])


seen_ids = set()
for chamber in ("House of Representatives", "Senate"):
  url = "http://beta.congress.gov/members?pageSize=1500&Legislative_Source=Member+Profiles&Congress=%s&Chamber_of_Congress=%s" % (
    urllib.quote_plus(CONGRESS_ID), urllib.quote_plus(chamber))
  cache = "congress.gov/members/%s-%s.html" % (CONGRESS_ID, chamber)

  try:
    body = download(url, cache, force)
    dom = lxml.html.parse(StringIO.StringIO(body.decode("utf-8"))).getroot()
  except lxml.etree.XMLSyntaxError:
    print "Error parsing: ", url
    continue
    
  for node in dom.xpath("//option"):
    val = node.get('value')
    match = re.search("/member\/([\w\-]+)\/(\d+)$", val)
    if (not match):
      
      continue
    thomas_id = "%05d" % int(match.group(2))
    urlname =match.group(1)

    if thomas_id in by_thomas:
      by_thomas[thomas_id]['id']['beta_name']=urlname
      
    

save_data(y, "legislators-current-test.yaml")
