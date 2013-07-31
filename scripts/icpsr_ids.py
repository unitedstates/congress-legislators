 #!/usr/bin/env python

# gets ICPSR ID for every member

# options:
#  --cache: load from cache if present on disk (default: true)
#  --bioguide: load only one legislator, by his/her bioguide ID
#  --congress: do *only* updates for legislators serving in specific congress

import datetime
import re
import utils
import urllib2
import requests
from utils import download, load_data, save_data, parse_date, states, congress_from_legislative_year, legislative_year
import json
import string
import csv
import unicodedata

debug = utils.flags().get('debug', False)

# default to caching
cache = utils.flags().get('cache', True)
force = not cache


only_bioguide = utils.flags().get('bioguide', None)
congress = utils.flags().get('congress',None)


filename_historical = "legislators-historical.yaml"
filename_current = "legislators-current.yaml"
data_files = []

print "Loading %s..." % "legislators-current.yaml"
legislators = load_data("legislators-current.yaml")
data_files.append((legislators,"legislators-current.yaml"))
print "Loading %s..." % "legislators-historical.yaml"
legislators = load_data("legislators-historical.yaml")
data_files.append((legislators,"legislators-historical.yaml"))

#load roll call data. Will need to be updated (possibly) for 114th+ congresses, since it is unclear what the URl format will be
if congress == None:
    raise Exception("the --congress flag is required")
elif congress == "113":
    url_senate = "http://amypond.sscnet.ucla.edu/rollcall/static/S113.ord"
    url_house = "http://amypond.sscnet.ucla.edu/rollcall/static/H113.ord"
elif int(congress) <10 and int(congress) >0:
    url_senate = "ftp://voteview.com/dtaord/sen0%skh.ord" % congress
    url_house = "ftp://voteview.com/dtaord/hou0%skh.ord" % congress
elif int(congress) < 113 and int(congress) >= 10:
    url_senate = "ftp://voteview.com/dtaord/sen%skh.ord" % congress
    url_house = "ftp://voteview.com/dtaord/hou%skh.ord" % congress
else:
    raise Exception("no data for congress " + congress)

senate_destination = "icpsr/source/senate_rollcall%s.txt" % congress
senate_data = utils.download(url_senate, senate_destination, force)

house_destination = "icpsr/source/house_rollcall%s.txt" % congress
house_data = utils.download(url_house, house_destination, force)

error_log = csv.writer(open("cache/errors/mismatch/mismatch_%s.csv" % congress, "wb"))
error_log.writerow(["error_type","matches","icpsr_name","icpsr_state","is_territory","old_id","new_id"])



read_files = [(senate_data,"sen"),(house_data,"rep")]
print "Running for congress " + congress
for read_file in read_files:
    for data_file in data_files:
        for legislator in data_file[0]:
            num_matches = 0
            # # this can't run unless we've already collected a bioguide for this person
            bioguide = legislator["id"].get("bioguide", None)
            # if we've limited this to just one bioguide, skip over everyone else
            if only_bioguide and (bioguide != only_bioguide):
                continue
            #if not in currently read chamber, skip
            chamber = legislator['terms'][len(legislator['terms'])-1]['type']
            if chamber != read_file[1]:
                continue

            #only run for selected congress
            latest_congress = utils.congress_from_legislative_year(utils.legislative_year(parse_date(legislator['terms'][len(legislator['terms'])-1]['start'])))
            if chamber == "sen":
                congresses = [latest_congress,latest_congress+1,latest_congress+2]
            else:
                congresses =[latest_congress]

            if int(congress) not in congresses:
                continue

            # pull data to match from yaml
            
            last_name_unicode = legislator['name']['last'].upper().strip().replace('\'','')
            last_name = unicodedata.normalize('NFD', unicode(last_name_unicode)).encode('ascii', 'ignore')
            state = utils.states[legislator['terms'][len(legislator['terms'])-1]['state']].upper()[:7].strip()
            # select icpsr source data based on more recent chamber
            
            write_id = ""
            lines = read_file[0].split('\n')
            for line in lines:
                # parse source data
                icpsr_state = line[12:20].strip()
                icpsr_name = line[21:].strip().strip(string.digits).strip()
                icpsr_id = line[3:8].strip()

                #ensure unique match
                if icpsr_name[:8] == last_name[:8] and state == icpsr_state:
                    num_matches += 1
                    write_id = icpsr_id
            #skip if icpsr id is currently in data
            if "icpsr" in legislator["id"]:
                if write_id == legislator["id"]["icpsr"] or write_id == "":
                    continue
                elif write_id != legislator["id"]["icpsr"] and write_id != "":
                    error_log.writerow(["Incorrect_ID","NA",last_name[:8],state,"NA",legislator["id"]["icpsr"],write_id])
                    print "ID updated for %s" % last_name
            if num_matches == 1:
                legislator['id']['icpsr'] = int(write_id)
            else:
                if state == 'GUAM' or state == 'PUERTO' or state == "VIRGIN" or state == "DISTRIC" or state == "AMERICA" or state == "NORTHER" or state == "PHILIPP":
                    error_log.writerow(["Non_1_match_number",str(num_matches),last_name[:8],state,"Y","NA","NA"])
                else:
                    print str(num_matches) + " matches found for "+ last_name[:8] + ", " + state + " in congress " + str(congress)
                    error_log.writerow(["Non_1_match_number",str(num_matches),last_name,state,"N","NA","NA"])
 

        save_data(data_file[0], data_file[1])

## the following three lines can be run as a separate script to update icpsr id's for all historical congresses
# import os

# for i in range(1,114):
#     os.system("python ICPSR_id.py --congress=" + str(i))