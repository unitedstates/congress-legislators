#!/usr/bin/env python

# gets CRP id for every member with a bioguide ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import lxml.html, StringIO
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
    url_BG = "http://transparencydata.com/api/1.0/entities/id_lookup.json?bioguide_id="
    if m["id"].has_key("bioguide"):
        url_BG += m["id"]["bioguide"]
        url_BG += "&apikey="+api_key
        root = lxml.html.parse(url_BG)
        jsondata = json.loads(root.find(".//p").text)
        try:
            IE_ID = jsondata[0]['id']
        except:
            continue
        url_CRP = "http://transparencydata.com/api/1.0/entities/"
        url_CRP += IE_ID
        url_CRP += ".json?apikey=" + api_key
        root2 = lxml.html.parse(url_CRP).getroot()
        jsondata2 = json.loads(root2.find(".//body").text_content())
        try:
            m["id"]["opensecrets"] = jsondata2['external_ids'][0]['id']
        except:
            continue

print "Saving data to %s..." % filename
save_data(legislators, filename)
