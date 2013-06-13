#!/usr/bin/env python

# gets CRP id for every member with a bioguide ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import datetime
import re
import utils
import urllib2
import requests
from utils import download, load_data, save_data, parse_date
import json

debug = utils.flags().get('debug', False)

# default to caching
cache = utils.flags().get('cache', True)
force = not cache


only_bioguide = utils.flags().get('bioguide', None)


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


api_file = open('cache/sunlight_api_key.txt','r')
api_key = api_file.read()


for m in legislators:

    # this can't run unless we've already collected a bioguide for this person
    bioguide = m["id"].get("bioguide", None)
    if not bioguide:
        continue
    # if we've limited this to just one bioguide, skip over everyone else
    if only_bioguide and (bioguide != only_bioguide):
        continue

    url_BG = "http://transparencydata.com/api/1.0/entities/id_lookup.json?bioguide_id="
    url_BG += bioguide
    url_BG += "&apikey="+api_key


    destination = "legislators/influence_explorer/%s.json" % bioguide
    body = utils.download(url_BG, destination, force)

    jsondata = json.loads(body)
    if (jsondata != []):    
        IE_ID = jsondata[0]['id']
        url_CRP = "http://transparencydata.com/api/1.0/entities/"
        url_CRP += IE_ID
        url_CRP += ".json?apikey=" + api_key

        destination = "legislators/influence_explorer/%s.json" % IE_ID
        body = utils.download(url_CRP, destination, force)

        jsondata = json.loads(body)


        m["id"]["opensecrets"] = jsondata['external_ids'][0]['id']
    else:
        print "No data exists for Bioguide id: " + bioguide




print "Saving data to %s..." % filename
save_data(legislators, filename)
