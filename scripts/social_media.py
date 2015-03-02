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
# run with --verify:
#   verifies that current usernames are still valid. (tries to catch renames)
#
# run with --resolvefb:
#   finds both Facebook usernames and graph IDs and updates the YAML accordingly.
#
# run with --resolveyt:
#   finds both YouTube usernames and channel IDs and updates the YAML accordingly.

# other options:
#  --service (required): "twitter", "youtube", "facebook", or "instagram"
#  --bioguide: limit to only one particular member
#  --email:
#      in conjunction with --sweep, send an email if there are any new leads, using
#      settings in scripts/email/config.yml (if it was created and filled out).

# uses a CSV at data/social_media_blacklist.csv to exclude known non-individual account names

import csv, re
import utils
from utils import load_data, save_data
import requests
import time

def main():
  regexes = {
    "youtube": [
      "https?://(?:www\\.)?youtube.com/channel/([^\\s\"/\\?#']+)",
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
    ],
    "instagram": [
      "instagram.com/(\w{3,})"
    ]
  }

  email_enabled = utils.flags().get('email', False)
  debug = utils.flags().get('debug', False)
  do_update = utils.flags().get('update', False)
  do_clean = utils.flags().get('clean', False)
  do_verify = utils.flags().get('verify', False)
  do_resolvefb = utils.flags().get('resolvefb', False)
  do_resolveyt = utils.flags().get('resolveyt', False)
  do_resolveig = utils.flags().get('resolveig', False)

  
  # default to not caching
  cache = utils.flags().get('cache', False)
  force = not cache

  if do_resolvefb:
    service = "facebook"
  elif do_resolveyt:
    service = "youtube"
  elif do_resolveig:
    service = "instagram"
  else:
    service = utils.flags().get('service', None)
  if service not in ["twitter", "youtube", "facebook", "instagram"]:
    print("--service must be one of twitter, youtube, facebook, or instagram")
    exit(0)

  # load in members, orient by bioguide ID
  print("Loading current legislators...")
  current = load_data("legislators-current.yaml")

  current_bioguide = { }
  for m in current:
    if "bioguide" in m["id"]:
      current_bioguide[m["id"]["bioguide"]] = m

  print("Loading blacklist...")
  blacklist = {
    'twitter': [], 'facebook': [], 'youtube': [], 'instagram': []
  }
  for rec in csv.DictReader(open("data/social_media_blacklist.csv")):
    blacklist[rec["service"]].append(rec["pattern"])

  print("Loading whitelist...")
  whitelist = {
    'twitter': [], 'facebook': [], 'youtube': []
  }
  for rec in csv.DictReader(open("data/social_media_whitelist.csv")):
    whitelist[rec["service"]].append(rec["account"].lower())

  # reorient currently known social media by ID
  print("Loading social media...")
  media = load_data("legislators-social-media.yaml")
  media_bioguide = { }
  for m in media:
    media_bioguide[m["id"]["bioguide"]] = m

  def resolvefb():
    # in order to preserve the comment block at the top of the file,
    # copy it over into a new RtYamlList instance. We do this because
    # Python list instances can't hold other random attributes.
    import rtyaml
    updated_media = rtyaml.RtYamlList()
    if hasattr(media, '__initial_comment_block'):
      updated_media.__initial_comment_block = getattr(media, '__initial_comment_block')

    for m in media:
      social = m['social']

      if ('facebook' in social and social['facebook']) and ('facebook_id' not in social):
        graph_url = "https://graph.facebook.com/%s" % social['facebook']

        if re.match('\d+', social['facebook']):
          social['facebook_id'] = social['facebook']
          print("Looking up graph username for %s" % social['facebook'])
          fbobj = requests.get(graph_url).json()
          if 'username' in fbobj:
            print("\tGot graph username of %s" % fbobj['username'])
            social['facebook'] = fbobj['username']
          else:
            print("\tUnable to get graph username")

        else:
          try:
            print("Looking up graph ID for %s" % social['facebook'])
            fbobj = requests.get(graph_url).json()
            if 'id' in fbobj:
              print("\tGot graph ID of %s" % fbobj['id'])
              social['facebook_id'] = fbobj['id']
            else:
              print("\tUnable to get graph ID")
          except:
            print("\tUnable to get graph ID for: %s" % social['facebook'])
            social['facebook_id'] = None

      updated_media.append(m)

    print("Saving social media...")
    save_data(updated_media, "legislators-social-media.yaml")


  def resolveyt():
    # To avoid hitting quota limits, register for a YouTube 2.0 API key at
    # https://code.google.com/apis/youtube/dashboard
    # and put it below
    api_file = open('cache/youtube_api_key','r')
    api_key = api_file.read()

    bioguide = utils.flags().get('bioguide', None)

    updated_media = []
    for m in media:
      if bioguide and (m['id']['bioguide'] != bioguide):
        updated_media.append(m)
        continue

      social = m['social']

      if ('youtube' in social) or ('youtube_id' in social):

        if 'youtube' not in social:
          social['youtube'] = social['youtube_id']

        ytid = social['youtube']

        profile_url = ("http://gdata.youtube.com/feeds/api/users/%s"
        "?v=2&prettyprint=true&alt=json&key=%s" % (ytid, api_key))

        try:
          print("Resolving YT info for %s" % social['youtube'])
          ytreq = requests.get(profile_url)
          # print "\tFetched with status code %i..." % ytreq.status_code

          if ytreq.status_code == 404:
            # If the account name isn't valid, it's probably a redirect.
            try:
              # Try to scrape the real YouTube username
              print("\Scraping YouTube username")
              search_url = ("http://www.youtube.com/%s" % social['youtube'])
              csearch = requests.get(search_url).text.encode('ascii','ignore')

              u = re.search(r'<a[^>]*href="[^"]*/user/([^/"]*)"[.]*>',csearch)

              if u:
                print("\t%s maps to %s" % (social['youtube'],u.group(1)))
                social['youtube'] = u.group(1)
                profile_url = ("http://gdata.youtube.com/feeds/api/users/%s"
                "?v=2&prettyprint=true&alt=json" % social['youtube'])

                print("\tFetching GData profile...")
                ytreq = requests.get(profile_url)
                print("\tFetched GData profile")

              else:
                raise Exception("Couldn't figure out the username format for %s" % social['youtube'])

            except:
              print("\tCouldn't locate YouTube account")
              raise

          ytobj = ytreq.json()
          social['youtube_id'] = ytobj['entry']['yt$channelId']['$t']
          print("\tResolved youtube_id to %s" % social['youtube_id'])

          # even though we have their channel ID, do they also have a username?
          if ytobj['entry']['yt$username']['$t'] != ytobj['entry']['yt$userId']['$t']:
            if social['youtube'].lower() != ytobj['entry']['yt$username']['$t'].lower():
              # YT accounts are case-insensitive.  Preserve capitalization if possible.
              social['youtube'] = ytobj['entry']['yt$username']['$t']
              print("\tAdded YouTube username of %s" % social['youtube'])
          else:
            print("\tYouTube says they do not have a separate username")
            del social['youtube']
        except:
          print("Unable to get YouTube Channel ID for: %s" % social['youtube'])

      updated_media.append(m)

    print("Saving social media...")
    save_data(updated_media, "legislators-social-media.yaml")


  def resolveig():
    # in order to preserve the comment block at the top of the file,
    # copy it over into a new RtYamlList instance. We do this because
    # Python list instances can't hold other random attributes.
    import rtyaml
    updated_media = rtyaml.RtYamlList()
    if hasattr(media, '__initial_comment_block'):
      updated_media.__initial_comment_block = getattr(media, '__initial_comment_block')

    client_id_file = open('cache/instagram_client_id','r')
    client_id = client_id_file.read()

    bioguide = utils.flags().get('bioguide', None)

    for m in media:
      if bioguide and (m['id']['bioguide'] != bioguide):
        updated_media.append(m)
        continue

      social = m['social']
      if 'instagram' not in social and 'instagram_id' not in social:
        updated_media.append(m)
        continue

      instagram_handle = social['instagram']
      query_url = "https://api.instagram.com/v1/users/search?q={query}&client_id={client_id}".format(query=instagram_handle,client_id=client_id)
      instagram_user_search = requests.get(query_url).json()
      for user in instagram_user_search['data']:
        time.sleep(0.5)
        if user['username'] == instagram_handle:
          m['social']['instagram_id'] = int(user['id'])
          print("matched instagram_id {instagram_id} to {instagram_handle}".format(instagram_id=social['instagram_id'],instagram_handle=instagram_handle))
      updated_media.append(m)

    save_data(updated_media, "legislators-social-media.yaml")

  def sweep():
    to_check = []

    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      possibles = [bioguide]
    else:
      possibles = list(current_bioguide.keys())

    for bioguide in possibles:
      if media_bioguide.get(bioguide, None) is None:
        to_check.append(bioguide)
      elif (media_bioguide[bioguide]["social"].get(service, None) is None) and \
        (media_bioguide[bioguide]["social"].get(service + "_id", None) is None):
        to_check.append(bioguide)
      else:
        pass

    utils.mkdir_p("cache/social_media")
    writer = csv.writer(open("cache/social_media/%s_candidates.csv" % service, 'w'))
    writer.writerow(["bioguide", "official_full", "website", "service", "candidate", "candidate_url"])

    if len(to_check) > 0:
      rows_found = []
      for bioguide in to_check:
        candidate = candidate_for(bioguide)
        if candidate:
          url = current_bioguide[bioguide]["terms"][-1].get("url", None)
          candidate_url = "https://%s.com/%s" % (service, candidate)
          row = [bioguide, current_bioguide[bioguide]['name']['official_full'].encode('utf-8'), url, service, candidate, candidate_url]
          writer.writerow(row)
          print("\tWrote: %s" % candidate)
          rows_found.append(row)

      if email_enabled and len(rows_found) > 0:
        email_body = "Social media leads found:\n\n"
        for row in rows_found:
          email_body += ("%s\n" % row)
        utils.send_email(email_body)

  def verify():
    bioguide = utils.flags().get('bioguide', None)
    if bioguide:
      to_check = [bioguide]
    else:
      to_check = list(media_bioguide.keys())

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
        print("[%s] mismatch on %s - %s -> %s" % (bioguide, url, current, candidate))

  def update():
    for rec in csv.DictReader(open("cache/social_media/%s_candidates.csv" % service)):
      bioguide = rec["bioguide"]
      candidate = rec["candidate"]

      if bioguide in media_bioguide:
        media_bioguide[bioguide]['social'][service] = candidate
      else:
        new_media = {'id': {}, 'social': {}}

        new_media['id']['bioguide'] = bioguide
        thomas_id = current_bioguide[bioguide]['id'].get("thomas", None)
        govtrack_id = current_bioguide[bioguide]['id'].get("govtrack", None)
        if thomas_id:
          new_media['id']['thomas'] = thomas_id
        if govtrack_id:
          new_media['id']['govtrack'] = govtrack_id


        new_media['social'][service] = candidate
        media.append(new_media)

    print("Saving social media...")
    save_data(media, "legislators-social-media.yaml")

    # if it's a youtube update, always do the resolve
    # if service == "youtube":
    #   resolveyt()


  def clean():
    print("Loading historical legislators...")
    historical = load_data("legislators-historical.yaml")

    count = 0
    for m in historical:
      if m["id"]["bioguide"] in media_bioguide:
        media.remove(media_bioguide[m["id"]["bioguide"]])
        count += 1
    print("Removed %i out of office legislators from social media file..." % count)

    print("Saving historical legislators...")
    save_data(media, "legislators-social-media.yaml")

  def candidate_for(bioguide):
    url = current_bioguide[bioguide]["terms"][-1].get("url", None)
    if not url:
      if debug:
        print("[%s] No official website, skipping" % bioguide)
      return None

    if debug:
      print("[%s] Downloading..." % bioguide)
    cache = "congress/%s.html" % bioguide
    body = utils.download(url, cache, force, {'check_redirects': True})
    if not body:
      return None

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
            print("\tBlacklisted: %s" % candidate)
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
  elif do_resolveyt:
    resolveyt()
  elif do_resolveig:
    resolveig()
  else:
    sweep()

if __name__ == '__main__':
  main()