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
from utils import download, load_data, save_data, parse_date
import json
import string
import csv
import unicodedata

def congress_from_legislative_year(year):
    return ((year + 1) / 2) - 894

def current_legislative_year(date=None):
    if not date:
        date = datetime.datetime.now()
    year = date.year

    if date.month == 1:
        if date.day == 1 or date.day == 2:
            return date.year - 1
        #yaml has no time data, so can't distinguish between pre/post noon dates. So, since this script is based on start-dates to determine congress numbers, starting anytime on 01-03 is the new congress
        elif date.day == 3:
            return date.year
        else:
            return date.year
    else:
        return date.year

states = {
        'AK': 'Alaska',
        'AL': 'Alabama',
        'AR': 'Arkansas',
        'AS': 'American Samoa',
        'AZ': 'Arizona',
        'CA': 'California',
        'CO': 'Colorado',
        'CT': 'Connecticut',
        'DC': 'District of Columbia',
        'DE': 'Delaware',
        'FL': 'Florida',
        'GA': 'Georgia',
        'GU': 'Guam',
        'HI': 'Hawaii',
        'IA': 'Iowa',
        'ID': 'Idaho',
        'IL': 'Illinois',
        'IN': 'Indiana',
        'KS': 'Kansas',
        'KY': 'Kentucky',
        'LA': 'Louisiana',
        'MA': 'Massachusetts',
        'MD': 'Maryland',
        'ME': 'Maine',
        'MI': 'Michigan',
        'MN': 'Minnesota',
        'MO': 'Missouri',
        'MP': 'Northern Mariana Islands',
        'MS': 'Mississippi',
        'MT': 'Montana',
        'NA': 'National',
        'NC': 'North Carolina',
        'ND': 'North Dakota',
        'NE': 'Nebraska',
        'NH': 'New Hampshire',
        'NJ': 'New Jersey',
        'NM': 'New Mexico',
        'NV': 'Nevada',
        'NY': 'New York',
        'OH': 'Ohio',
        'OK': 'Oklahoma',
        'OR': 'Oregon',
        'PA': 'Pennsylvania',
        'PR': 'Puerto Rico',
        'RI': 'Rhode Island',
        'SC': 'South Carolina',
        'SD': 'South Dakota',
        'TN': 'Tennessee',
        'TX': 'Texas',
        'UT': 'Utah',
        'VA': 'Virginia',
        'VI': 'Virgin Islands',
        'VT': 'Vermont',
        'WA': 'Washington',
        'WI': 'Wisconsin',
        'WV': 'West Virginia',
        'WY': 'Wyoming',
        'OL': 'Orleans',
        'DK': 'Dakota',
        'PI': 'Philippine Islands'
}

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
    destination = "icpsr/source/senate_rollcall%s.txt" % congress
    senate_data = utils.download(url_senate, destination, force)

    url_house = "http://amypond.sscnet.ucla.edu/rollcall/static/H113.ord"
    destination = "icpsr/source/house_rollcall%s.txt" % congress
    house_data = utils.download(url_house, destination, force)
elif int(congress) <10 and int(congress) >0:
    url_senate = "ftp://voteview.com/dtaord/sen0%skh.ord" % congress
    destination = "icpsr/source/senate_rollcall%s.txt" % congress
    senate_data = utils.download(url_senate, destination, force)

    url_house = "ftp://voteview.com/dtaord/hou0%skh.ord" % congress
    destination = "icpsr/source/house_rollcall%s.txt" % congress
    house_data = utils.download(url_house, destination, force)
elif int(congress) < congress_from_legislative_year(current_legislative_year()) and int(congress) >= 10:
    url_senate = "ftp://voteview.com/dtaord/sen%skh.ord" % congress
    destination = "icpsr/source/senate_rollcall%s.txt" % congress
    senate_data = utils.download(url_senate, destination, force)

    url_house = "ftp://voteview.com/dtaord/hou%skh.ord" % congress
    destination = "icpsr/source/house_rollcall%s.txt" % congress
    house_data = utils.download(url_house, destination, force)
else:
    raise Exception("no data for congress " + congress)

cw = csv.writer(open("cache/errors/mismatch/mismatch_%s.csv" % congress, "wb"))
cw.writerow(["matches","icpsr_name","icpsr_state","is_territory"])

read_files = [(senate_data,"sen"),(house_data,"rep")]
print "Running for congress " + congress
for r in read_files:
    for f in data_files:
        for m in f[0]:
            num_matches = 0
            # # this can't run unless we've already collected a bioguide for this person
            bioguide = m["id"].get("bioguide", None)
            # if we've limited this to just one bioguide, skip over everyone else
            if only_bioguide and (bioguide != only_bioguide):
                num_matches += 1
                continue
            #skip if icpsr id is currently in data
            if "icpsr" in m["id"]:
                num_matches += 1
                continue
            #if not in currently read chamber, skip
            chamber = m['terms'][len(m['terms'])-1]['type']
            if chamber != r[1]:
                num_matches += 1
                continue

            #only run for selected congress
            latest_congress = congress_from_legislative_year(current_legislative_year(parse_date(m['terms'][len(m['terms'])-1]['start'])))
            if chamber == "sen":
                congresses = [latest_congress,latest_congress+1,latest_congress+2]
            else:
                congresses =[latest_congress]

            if int(congress) not in congresses:
                num_matches += 1
                continue

            # pull data to match from yaml
            
            last_name_unicode = m['name']['last'].upper().strip().replace('\'','')
            last_name = unicodedata.normalize('NFD', unicode(last_name_unicode)).encode('ascii', 'ignore')
            state = states[m['terms'][len(m['terms'])-1]['state']].upper()[:7].strip()
            # select icpsr source data based on more recent chamber
     
            lines = r[0].split('\n')
            for l in lines:
                disp = False
                # parse source data
                icpsr_state = l[12:20].strip()
                icpsr_name = l[21:].strip().strip(string.digits).strip()
                icpsr_id = l[3:8].strip()

                #ensure unique match
                if icpsr_name[:8] == last_name[:8] and state == icpsr_state:
                    num_matches += 1
                    write_id = icpsr_id
            if num_matches == 1:
                m['id']['icpsr'] = int(write_id)
            elif num_matches == 0:
                print "No matches found for " + last_name + ", " + state + "in congress " + str(congress)
                cw.writerow(["0",last_name,state])
            else:
                if state == 'GUAM' or state == 'PUERTO' or state == "VIRGIN" or state == "DISTRIC" or state == "AMERICA" or state == "NORTHER":
                    cw.writerow([str(num_matches),last_name[:8],state,"Y"])
                else:
                    print str(num_matches) + " matches found for "+ last_name[:8] + ", " + state + " in congress " + str(congress)
                    cw.writerow([str(num_matches),last_name,state,"N"])

        save_data(f[0], f[1])