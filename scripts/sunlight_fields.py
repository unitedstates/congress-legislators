#!/usr/bin/env python

# import some fields from Sunlight's Congress API data spreadsheet
# can be gotten rid of once the transition is complete

import re
import csv
import utils
from utils import download, load_data, save_data

print "Reading current data..."
current_data = load_data("legislators-current.yaml")
historical_data = load_data("legislators-historical.yaml")
social_data = load_data("legislators-social-media.yaml")

historical = {}
for l in historical_data: historical[l["id"]["bioguide"]] = l
current = {}
for l in current_data: current[l["id"]["bioguide"]] = l
social = {}
for l in social_data: social[l["id"]["bioguide"]] = l

def update_legislator(bioguide_id, row):
  active = (row[9] == '1')
  
  if current.has_key(bioguide_id):
    legislator = current[bioguide_id]
  elif historical.has_key(bioguide_id):
    legislator = historical[bioguide_id]
  else:
    print "Error, couldn't find bioguide_id %s" % bioguide_id
    exit(1)

  # New ID: FEC
  legislator['id']['fec_id'] = row[18]

  # Other contact information, but only if active
  if active:
    contact = {}
    if row[11]: contact['phone'] = row[11]
    if row[12]: contact['fax'] = row[12]
    if row[14]: contact['contact_form'] = row[14]
    if row[15]: contact['office'] = row[15]
    
    # update last term fields
    term = legislator['terms'][-1]
    term.update(contact)

    # update top-level contact fields
    # if not legislator.has_key('contact'): legislator['contact'] = {}
    # legislator['contact'].update(contact)
    # # copy 'url' and 'address' fields up to top-level as well
    # if term['url']: legislator['contact']['url'] = term['url']
    # if term['address']: legislator['contact']['address'] = term['address']

  return True

def update_social(bioguide_id, row):
  # initialize social media details if needed
  if not social.has_key(bioguide_id):
    social[bioguide_id] = {
      'id': {
        'bioguide': bioguide_id
      },
      'social': {}
    }
  accounts = social[bioguide_id]['social']

  # assume sunlight as authoritative
  if row[21]:
    accounts['twitter'] = row[21]

  if row[23]:
    accounts['youtube'] = re.sub("http://www.youtube.com/(?:user/)?", "", row[23])

  if row[24]:
    accounts['facebook_graph'] = row[24]

  return True

count = 0
with open("cache/sunlight/legislators.csv", "rb") as csvfile:
  reader = csv.reader(csvfile)

  for row in reader:
    count += 1
    if count == 1: continue

    bioguide_id = row[16]
    
    update_legislator(bioguide_id, row)
    update_social(bioguide_id, row)
    print "[%s] Updated legislator" % bioguide_id
    count += 1


print "Saving new data..."
save_data(current_data, "legislators-current.yaml")
save_data(historical_data, "legislators-historical.yaml")
save_data(social_data, "legislators-social-media.yaml")