#!/usr/bin/env python

# Parse the THOMAS advanced search page for a list of all committees
# and subcommittees from the 93rd Congress forward and store them in
# the committees-historical.yaml file. It will include current committees
# as well.

import zipfile
from collections import OrderedDict
import utils
from utils import load_data, save_data, CURRENT_CONGRESS, scraper
import io
import lxml.etree

def run():
  committees_historical = load_data("committees-historical.yaml")

  # default to not caching
  flags = utils.flags()
  cache = flags.get('cache', False)

  if cache:
    from scrapelib.cache import FileCache
    scraper.cache_storage = FileCache('cache')
    scraper.cache_write_only = False
  else:
    raise

  # map thomas_id's to their dicts
  committees_historical_ref = { }
  for cx in committees_historical:
    committees_historical_ref[cx["thomas_id"]] = cx


  # pick the range of committees to get
  single_congress = flags.get('congress', False)
  if single_congress:
    start_congress = int(single_congress)
    end_congress = int(single_congress) + 1
  else:
    start_congress = 113
    end_congress = CURRENT_CONGRESS + 1


  urls = {'senate': 'https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/s/BILLSTATUS-{congress}-s.zip',
          'house': 'https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/hr/BILLSTATUS-{congress}-hr.zip'}

  all_committees = {'house': {}, 'senate': {}}
    
  for congress in range(start_congress, end_congress):
    for chamber, bill_status_url in urls.items():
      chamber_committees = all_committees[chamber]
      
      url = bill_status_url.format(congress=congress)
      response = scraper.get(url)      

      with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        for name in z.namelist():
          if name.startswith('BILLSTATUS'):
            with z.open(name) as xml_file:
              bill_status = lxml.etree.parse(xml_file)
              committees =  bill_status.xpath('//billCommittees/item')
              for committee in committees:
                code = str(committee.xpath('./systemCode/text()')[0])
                name = str(committee.xpath('./name/text()')[0])
                if name.endswith(' Committee'):
                  name = name[:-10]
                if code not in chamber_committees:
                  chamber_committees[code] = {'names': {congress: name},
                                              'subcommittees': {}}
                else:
                  if congress not in chamber_committees[code]:
                    chamber_committees[code]['names'][congress] = name

                subcommittees_d = chamber_committees[code]['subcommittees']
                for subcommittee in committee.xpath('./subcommittees/item'):
                  code = str(subcommittee.xpath('./systemCode/text()')[0])
                  name = str(subcommittee.xpath('./name/text()')[0])
                  if name.endswith(' Subcommittee'):
                    name = name[:-13]
                  if code not in subcommittees_d:
                    subcommittees_d[code] = {congress: name}
                  else:
                    if congress not in subcommittees_d[code]:
                      subcommittees_d[code][congress] = name

      import pprint
      pprint.pprint(chamber_committees)
      print(len(chamber_committees))


  for chamber, committees in all_committees.items():
    for code, committee in committees.items():
      id = str(code).upper()

      id = id[:-2]

      if id in committees_historical_ref:
        # Update existing record.
        cx = committees_historical_ref[id]

      else:
        # Create a new record.
        cx = OrderedDict()
        committees_historical_ref[id] = cx
        cx['type'] = chamber.lower()
        if id[0] != "J": # Joint committees show their full name, otherwise they show a partial name
          cx['name'] = chamber + " Committee on " + name
        else:
          cx['name'] = committee['names'][min(committee['names'])]
        cx['thomas_id'] = id
        committees_historical.append(cx)

      for code, subcommittee in committee['subcommittees'].items():

        for sx in cx.setdefault('subcommittees', []):
          if sx['thomas_id'] == code[-2:]:
            # found existing record
            break
        else:
          # 'break' not executed, so create a new record
          sx = OrderedDict()
          sx['name'] = subcommittee[min(subcommittee)]
          sx['thomas_id'] = code[-2:]
          cx['subcommittees'].append(sx)


          sx.setdefault('congresses', [])
          sx.setdefault('names', {})

          for congress, name in subcommittee.items():
            if congress not in sx['congresses']:
               sx['congresses'].append(congress)

               sx['names'][congress] = name

      cx.setdefault('congresses', [])
      cx.setdefault('names', {})

      for congress, name in committee['names'].items():
        if congress not in cx['congresses']:
          cx['congresses'].append(congress)
          cx['names'][congress] = name

                 
  # TODO
  # after checking diff on first commit, we should re-sort
  #committees_historical.sort(key = lambda c : c["thomas_id"])
  #for c in committees_historical:
  #  c.get("subcommittees", []).sort(key = lambda s : s["thomas_id"])

  save_data(committees_historical, "committees-historical.yaml")

if __name__ == '__main__':
  run()
