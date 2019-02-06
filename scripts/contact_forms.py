#!/usr/bin/env python

'''Gets contact webform URLs for the intersection of members with bioguide ids
and with correlating contact form steps in unitedstates/contact-congress:

args:
<bioguide_id bioguide_id ...>
A list of bioguide ids to import.

options:
  --debug[=True]
  Whether or not verbose output should be printed to the command line
'''

import yaml
from urllib.request import urlopen

import utils
from utils import load_data, save_data


# These members have forms in iframes, and Contact-Congress has different
# needs than human users might.
SKIP_BIOGUIDES = ['M000312']


def run():
    options = utils.flags()
    debug = options.get('debug', False)

    filename = "legislators-current.yaml"
    args = utils.args()
    legislators = load_data(filename)

    if len(args) != 0:
        bioguides = args
        print("Fetching contact forms for %s..." % ', '.join(bioguides))
    else:
        bioguides = [member['id']['bioguide'] for member in legislators]
        print("Fetching contact forms for all current members...")

    for legislator in legislators:
        bioguide = legislator['id']['bioguide']
        if bioguide not in bioguides: continue
        if bioguide in SKIP_BIOGUIDES: continue

        if debug: print("Downloading form for %s" % bioguide, flush=True)

        try:
            steps = contact_steps_for(bioguide)
        except LegislatorNotFoundError as e:
            if debug: print("skipping, %s..." % e, flush=True)
            continue

        legislator['terms'][-1]['contact_form'] = steps['contact_form']['steps'][0]['visit']

    print("Saving data to %s..." % filename)
    save_data(legislators, filename)


def contact_steps_for(bioguide):
    base_url = "https://raw.githubusercontent.com/unitedstates/contact-congress/master/members/{bioguide}.yaml"
    response = urlopen(base_url.format(bioguide=bioguide))
    if response.code == 404:
        raise LegislatorNotFoundError("%s not found in unitedstates/contact-congress!" % bioguide)
    return yaml.load(response.read())


class LegislatorNotFoundError(Exception):
    pass


if __name__ == '__main__':
    run()
