#!/usr/bin/env python

# gets CRP id for every member with a bioguide ID:

# options:
#  --cache: load from cache if present on disk (default: true)
#  --current: do *only* current legislators (default: true)
#  --historical: do *only* historical legislators (default: false)

import utils
from utils import load_data, save_data
import json

def run():

    options = utils.flags()
    options['urllib'] = True # disable scrapelib for this

    debug = options.get('debug', False)

    # default to NOT caching
    cache = options.get('cache', False)
    force = not cache


    only_bioguide = options.get('bioguide', None)


    # pick either current or historical
    # order is important here, since current defaults to true
    if utils.flags().get('historical', False):
      filename = "legislators-historical.yaml"
    elif utils.flags().get('current', True):
      filename = "legislators-current.yaml"
    else:
      print("No legislators selected.")
      exit(0)


    print("Loading %s..." % filename)
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


        destination = "legislators/influence_explorer/lookups/%s.json" % bioguide
        if debug: print("[%s] Looking up ID..." % bioguide)
        body = utils.download(url_BG, destination, force, options)

        if not body:
            print("[%s] Bad request, skipping" % bioguide)
            continue

        jsondata = json.loads(body)
        if (jsondata != []):
            IE_ID = jsondata[0]['id']
            url_CRP = "http://transparencydata.com/api/1.0/entities/"
            url_CRP += IE_ID
            url_CRP += ".json?apikey=" + api_key

            destination = "legislators/influence_explorer/entities/%s.json" % IE_ID
            body = utils.download(url_CRP, destination, force, options)

            jsondata = json.loads(body)

            opensecrets_id = None
            fec_ids = []
            for external in jsondata['external_ids']:
                if external["namespace"].startswith("urn:crp"):
                    opensecrets_id = external['id']
                elif external["namespace"].startswith("urn:fec"):
                    fec_ids.append(external['id'])

            if opensecrets_id:
                m["id"]["opensecrets"] = opensecrets_id

            # preserve existing FEC IDs, but don't duplicate them
            if len(fec_ids) > 0:
                if m["id"].get("fec", None) is None: m["id"]["fec"] = []
                for fec_id in fec_ids:
                    if fec_id not in m["id"]["fec"]:
                        m["id"]["fec"].append(fec_id)

            print("[%s] Added opensecrets ID of %s" % (bioguide, opensecrets_id))
        else:
            print("[%s] NO DATA" % bioguide)




    print("Saving data to %s..." % filename)
    save_data(legislators, filename)

if __name__ == '__main__':
  run()