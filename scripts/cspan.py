#!/usr/bin/env python

# Update current cspan IDs using NYT Congress API.

import json, urllib.request, urllib.parse, urllib.error
from utils import load_data, save_data

def run():
    # load in current members
    y = load_data("legislators-current.yaml")
    for m in y:
        # retrieve C-SPAN id, if available, from ProPublica API
        # TODO: use utils.download here
        response = urllib.request.urlopen("https://projects.propublica.org/represent/api/v1/members/%s.json" % m['id']['bioguide']).read()
        j = json.loads(response.decode("utf8"))
        cspan = j['results'][0]['cspan_id']
        if not cspan == '':
            m['id']['cspan'] = int(cspan)
    save_data(y, "legislators-current.yaml")

if __name__ == '__main__':
  run()
