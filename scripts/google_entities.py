#!/usr/bin/env python

# Update current Google entity IDs using ProPublica Congress API.

import json, urllib.request, urllib.parse, urllib.error
import rtyaml
from utils import load_data, save_data

def run():
    # load in current members
    y = load_data("legislators-current.yaml")
    for m in y:
        response = urllib.request.urlopen("http://propublica-congress.elasticbeanstalk.com/represent/api/v1/members/%s.json" % m['id']['bioguide']).read()
        j = json.loads(response.decode("utf8"))
        google = j['results'][0]['google_entity_id']
        if not google == '':
            m['id']['google_entity'] = google
    save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
