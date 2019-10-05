 #!/usr/bin/env python

# gets ICPSR ID for every member

# options:
#  --cache: load from cache if present on disk (default: true)
#  --bioguide: load only one legislator, by his/her bioguide ID
#  --congress: do *only* updates for legislators serving in specific congress

import utils
from utils import load_data, save_data, parse_date
import csv
from io import StringIO

def run():

    # default to caching
    cache = utils.flags().get('cache', True)
    force = not cache


    only_bioguide = utils.flags().get('bioguide', None)
    congress = utils.flags().get('congress',None)


    data_files = []

    print("Loading %s..." % "legislators-current.yaml")
    legislators = load_data("legislators-current.yaml")
    data_files.append((legislators,"legislators-current.yaml"))
    print("Loading %s..." % "legislators-historical.yaml")
    legislators = load_data("legislators-historical.yaml")
    data_files.append((legislators,"legislators-historical.yaml"))

    # load member data from vote view
    if congress == None:
        raise Exception("the --congress flag is required")
    elif int(congress) < 10 and int(congress) > 0:
        url_senate = "https://voteview.com/static/data/out/members/S00%s_members.csv" % congress
        url_house = "https://voteview.com/static/data/out/members/H00%s_members.csv" % congress
    elif int(congress) < 100 and int(congress) >= 10:
        url_senate = "https://voteview.com/static/data/out/members/S0%s_members.csv" % congress
        url_house = "https://voteview.com/static/data/out/members/H0%s_members.csv" % congress
    elif int(congress) >= 100:
        url_senate = "https://voteview.com/static/data/out/members/S%s_members.csv" % congress
        url_house = "https://voteview.com/static/data/out/members/H%s_members.csv" % congress
    else:
        raise Exception("no data for congress " + congress)

    senate_destination = "icpsr/source/senate_rollcall%s.txt" % congress
    senate_data = utils.download(url_senate, senate_destination, force)

    house_destination = "icpsr/source/house_rollcall%s.txt" % congress
    house_data = utils.download(url_house, house_destination, force)

    error_log = csv.writer(open("cache/errors/mismatch/mismatch_%s.csv" % congress, "w"))
    error_log.writerow(["error_type","matches","icpsr_name","icpsr_state","is_territory","old_id","new_id"])



    read_files = [("sen",senate_data),("rep",house_data)]
    print("Running for congress " + congress)
    for read_file_chamber,read_file_content in read_files:
        for data_file in data_files:
            for legislator in data_file[0]:
                num_matches = 0
                write_id = ""
                # this can't run unless we've already collected a bioguide for this person
                bioguide = legislator["id"].get("bioguide", None)
                # if we've limited this to just one bioguide, skip over everyone else
                if only_bioguide and (bioguide != only_bioguide):
                    continue
                #if not in currently read chamber, skip
                chamber = legislator['terms'][len(legislator['terms'])-1]['type']
                if chamber != read_file_chamber:
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

                last_name = legislator['name']['last'].upper()
                state = utils.states[legislator['terms'][len(legislator['terms'])-1]['state']].upper()[:7].strip()

                # convert read_file_content str to file object, then parse as csv file
                content_as_file = StringIO(read_file_content)
                content_parsed = csv.reader(content_as_file, delimiter=',')

                # loop through congress members in read file, see if one matches the current legislator
                for icpsr_member in content_parsed:
                    # ensure unique match bassed of bioguide id
                    if bioguide == icpsr_member[10]:
                        num_matches += 1
                        write_id = int(icpsr_member[2])

                # skip if icpsr id is currently in data
                if "icpsr" in legislator["id"]:
                    if write_id == legislator["id"]["icpsr"] or write_id == "":
                        continue
                    elif write_id != legislator["id"]["icpsr"] and write_id != "":
                        error_log.writerow(["Incorrect_ID","NA",last_name[:8],state,"NA",legislator["id"]["icpsr"],write_id])
                        print("ID updated for %s" % last_name)

                if num_matches == 1:
                    legislator['id']['icpsr'] = int(write_id)
                else:
                    if state == 'GUAM' or state == 'PUERTO' or state == "VIRGIN" or state == "DISTRIC" or state == "AMERICA" or state == "NORTHER" or state == "PHILIPP":
                        print('error: non 1 match')
                        error_log.writerow(["Non_1_match_number",str(num_matches),last_name[:8],state,"Y","NA","NA"])
                    else:
                        print(str(num_matches) + " matches found for "+ last_name[:8] + ", " + state + " in congress " + str(congress))
                        error_log.writerow(["Non_1_match_number",str(num_matches),last_name,state,"N","NA","NA"])

            save_data(data_file[0], data_file[1])

    ## the following three lines can be run as a separate script to update icpsr id's for all historical congresses
    # import os

    # for i in range(1,114):
    #     os.system("python ICPSR_id.py --congress=" + str(i))

if __name__ == '__main__':
  run()
