#!/usr/bin/env python

# run with --sweep (or by default):
#   given a service, looks through current members for those missing an account on that service,
#   and checks that member's official website's source code for mentions of that service.
#   A CSV of "leads" is produced for manual review.
#
# run with --update:
#   reads the CSV produced by --sweep back in and updates the YAML accordingly.
#
# run with --clean:
#   removes legislators from the social media file who are no longer current
#
# run with --resolvefb:
#   finds both Facebook usernames and graph IDs and updates the YAML accordingly.

# other options:
#  --service (required): "twitter", "youtube", or "facebook"
#  --bioguide: limit to only one particular member

# uses a CSV at data/social_media_blacklist.csv to exclude known non-individual account names

import csv, re
import utils
from utils import download, load_data, save_data, parse_date

import requests

def main():
  regexes = {
    "youtube": [
      "https?://(?:www\\.)?youtube.com/(channel/[^\\s\"/\\?#']+)",
      "https?://(?:www\\.)?youtube.com/(?:subscribe_widget\\?p=)?(?:subscription_center\\?add_user=)?(?:user/)?([^\\s\"/\\?#']+)"
    ],
    "facebook": [
      "\\('facebook.com/([^']+)'\\)",
      "https?://(?:www\\.)?facebook.com/(?:home\\.php)?(?:business/dashboard/#/)?(?:government)?(?:#!/)?(?:#%21/)?(?:#/)?pages/[^/]+/(\\d+)",
      "https?://(?:www\\.)?facebook.com/(?:profile.php\\?id=)?(?:home\\.php)?(?:#!)?/?(?:people)?/?([^/\\s\"#\\?&']+)"
    ],
    "twitter": [
      "https?://(?:www\\.)?twitter.com/(?:intent/user\?screen_name=)?(?:#!/)?(?:#%21/)?@?([^\\s\"'/]+)",
      "\\.render\\(\\)\\.setUser\\('@?(.*?)'\\)\\.start\\(\\)"
    ]
  }

  debug = utils.flags().get('debug', False)
  do_update = utils.flags().get('update', False)
  do_clean = utils.flags().get('clean', False)
  do_verify = utils.flags().get('verify', False)
  do_resolvefb = utils.flags().get('resolvefb', False)

  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache

  if do_resolvefb:
    service = "facebook"
  else:
    service = utils.flags().get('service', None)
  if service not in ["twitter", "youtube", "facebook"]:
    print "--service must be one of twitter, youtube, or facebook"
    exit(0)

  # load in members, orient by bioguide ID
  print "Loading current legislators..."
  current = load_data("legislators-current.yaml")
  
  current_bioguide = { }
  for m in current:
    if m["id"].has_key("bioguide"):
      current_bioguide[m["id"]["bioguide"]] = m

  print "Loading blacklist..."
  blacklist = {
    'twitter': [], 'facebook': [], 'youtube': []
  }
  for rec in csv.DictReader(open("data/social_media_blacklist.csv")):
    blacklist[rec["service"]].append(rec["pattern"])

  print "Loading whitelist..."
  whitelist = {
    'twitter': [], 'facebook': [], 'youtube': []
  }
  for rec in csv.DictReader(open("data/social_media_whitelist.csv")):
    whitelist[rec["service"]].append(rec["account"].lower())

  # reorient currently known social media by ID
  print "Loading social media..."
  media = load_data("legislators-social-media.yaml")
  media_bioguide = { }
  for m in media:
    media_bioguide[m["id"]["bioguide"]] = m
  
  
  def resolvefb():
    updated_media = []
    for m in media:
      social = m['social']
      
      if 'facebook' in social and social['facebook']:
        graph_url = "https://graph.facebook.com/%s" % social['facebook']
        
        if re.match('\d+', social['facebook']):
          social['facebook_id'] = social['facebook']
          fbobj = requests.get(graph_url).json()
          if 'username' in fbobj:
            social['facebook'] = fbobj['username']
          
        else:
          try:
            social['facebook_id'] = requests.get(graph_url).json()['id']
          except:
            print "Unable to get graph ID for: %s" % social['facebook']
            social['facebook_id'] = None
            
      updated_media.append(m)
      
    print "Saving social media..."
    save_data(updated_media, "legislators-social-media.yaml")
    

  def sweep():
    to_check = []

    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      possibles = [bioguide]
    else:
      possibles = current_bioguide.keys()

    for bioguide in possibles:
      if media_bioguide.get(bioguide, None) is None:
        to_check.append(bioguide)
      elif media_bioguide[bioguide]["social"].get(service, None) is None:
        to_check.append(bioguide)
      else:
        pass

    utils.mkdir_p("cache/social_media")
    writer = csv.writer(open("cache/social_media/%s_candidates.csv" % service, 'w'))
    writer.writerow(["bioguide", "official_full", "website", "service", "candidate", "candidate_url"])

    for bioguide in to_check:
      candidate = candidate_for(bioguide)
      if candidate:
        url = current_bioguide[bioguide]["terms"][-1].get("url", None)
        candidate_url = "https://%s.com/%s" % (service, candidate)
        writer.writerow([bioguide, current_bioguide[bioguide]['name']['official_full'].encode('utf-8'), url, service, candidate, candidate_url])
        print "\tWrote: %s" % candidate

  def verify():
    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      to_check = [bioguide]
    else:
      to_check = media_bioguide.keys()

    for bioguide in to_check:
      entry = media_bioguide[bioguide]
      current = entry['social'].get(service, None)
      if not current:
        continue

      bioguide = entry['id']['bioguide']

      candidate = candidate_for(bioguide)
      if not candidate:
        # if current is in whitelist, and none is on the page, that's okay
        if current.lower() in whitelist[service]:
          continue
        else:
          candidate = ""

      url = current_bioguide[bioguide]['terms'][-1].get('url')

      if current.lower() != candidate.lower():
        print "[%s] mismatch on %s - %s -> %s" % (bioguide, url, current, candidate)

  def update():
    for rec in csv.DictReader(open("cache/social_media/%s_candidates.csv" % service)):
      bioguide = rec["bioguide"]
      candidate = rec["candidate"]

      if media_bioguide.has_key(bioguide):
        media_bioguide[bioguide]['social'][service] = candidate
      else:
        new_media = {'id': {}, 'social': {}}

        new_media['id']['bioguide'] = bioguide
        thomas_id = current_bioguide[bioguide]['id'].get("thomas", None)
        if thomas_id:
          new_media['id']['thomas'] = thomas_id

        new_media['social'][service] = candidate
        media.append(new_media)

    print "Saving social media..."
    save_data(media, "legislators-social-media.yaml")

  def clean():
    print "Loading historical legislators..."
    historical = load_data("legislators-historical.yaml")

    count = 0
    for m in historical:
      if media_bioguide.has_key(m["id"]["bioguide"]):
        media.remove(media_bioguide[m["id"]["bioguide"]])
        count += 1
    print "Removed %i out of office legislators from social media file..." % count

    print "Saving historical legislators..."
    save_data(media, "legislators-social-media.yaml")

  def candidate_for(bioguide):
    url = current_bioguide[bioguide]["terms"][-1].get("url", None)
    if not url:
      if debug:
        print "[%s] No official website, skipping" % bioguide
      return None

    if debug:
      print "[%s] Downloading..." % bioguide
    cache = "congress/%s.html" % bioguide
    body = utils.download(url, cache, force)

    all_matches = []
    for regex in regexes[service]:
      matches = re.findall(regex, body, re.I)
      if matches:
        all_matches.extend(matches)

    if all_matches:
      for candidate in all_matches:
        passed = True
        for blacked in blacklist[service]:
          if re.search(blacked, candidate, re.I):
            passed = False
        
        if not passed:
          if debug:
            print "\tBlacklisted: %s" % candidate
          continue

        return candidate
      return None

  if do_update:
    update()
  elif do_clean:
    clean()
  elif do_verify:
    verify()
  elif do_resolvefb:
    resolvefb()
  else:
    sweep()

main()