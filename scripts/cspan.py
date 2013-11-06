#!/usr/bin/env python

# Update current cspan IDs using NYT Congress API.

import json, urllib
import utils
from utils import download, load_data, save_data, parse_date

# default to not caching
cache = utils.flags().get('cache', False)
force = not cache

# load in current members
y = load_data("legislators-current.yaml")
for m in y:
    # retrieve C-SPAN id, if available, from NYT API
    response = urllib.urlopen("http://politics.nytimes.com/congress/svc/politics/v3/us/legislative/congress/members/%s.json" % m['id']['bioguide']).read()
    j = json.loads(response)
    cspan = j['results'][0]['cspan_id']
    if not cspan == '':
        m['id']['cspan'] = int(cspan)
save_data(y, "legislators-current.yaml")