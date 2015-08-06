#!/usr/bin/env python

# This script makes the following adjustment to legislators-social-media.yaml:
# 1. For every entry that has a `social.twitter` (i.e. `screen_name `entry but
#    NOT a `social.twitter_id`,  a `social.twitter_id` key is created with the value
#    set to the user `id` that corresponds to the user's `screen_name`, as returned by
#    # https://dev.twitter.com/rest/reference/get/users/lookup
#
# 2. In "prune" mode, every `twitter` value is looked up on Twitter's API. If Twitter does not
#    return a corresponding user profile, the twitter value is deleted from the data file.
#
# options:
#  --prune: Go into "prune" mode and delete all `twitter` entries for which Twitter API has no
#     profile information.
#
#  --creds: points to a JSON file that contains Twitter credentials:
#    {
#      "consumer_secret": "xyz",
#      "access_token": "abc",
#      "access_token_secret": "def",
#      "consumer_key": "jk"
#     }
import json
import utils
from copy import deepcopy
from social_utils import get_twitter_api, fetch_twitter_profiles_for_screen_names
from os.path import expanduser

def run():
    creds_path = utils.flags().get('creds', "")
    prune_mode = utils.flags().get('prune', False)
    legis_data = utils.load_data("legislators-social-media.yaml")
    _databak = deepcopy(legis_data)
    social_data = [d['social'] for d in legis_data if d['social'].get('twitter')]
    # no creds is required yet, since we're just scanning the existing data file
    objs = find_accounts_without_ids(social_data)
    if not objs:
        print("Nothing to be done; all Twitter screen names have associated IDs.")
        return
    print("Missing Twitter IDs for:", ''.join(["\n - " + o['twitter'] for o in objs]))
    api = load_creds(creds_path)
    # legis_data is mutated here
    find_and_insert_missing_ids(api, socials = objs, prune_mode = prune_mode)
    # Write to file if changes made
    if legis_data != _databak:
        utils.save_data(legis_data, "legislators-social-media.yaml")
    else:
        print("No changes made to legislators-social-media.yaml")


def find_accounts_without_ids(socials):
    """
    socials is a list of dicts: [{'twitter': 'ev', 'facebook': 'Eve'}]

    Returns: list, filtered for dicts that have `twitter` but not `twitter_id`
    """
    arr = [d for d in socials if d.get('twitter') and not d.get('twitter_id')]
    return arr

def find_and_insert_missing_ids(api, socials, prune_mode = False):
    """
    given a list of dicts, call Twitter API and find profiles for social['twitter'] and
      insert 'twitter_id' attribute

    Returns: Nothing, socials is mutated
    """
    tnames = [s['twitter'] for s in socials]
    profiles = fetch_twitter_profiles_for_screen_names(api, tnames)
    for soc in socials:
        twitter_name = soc['twitter']
        # find a profile that has the given screen name
        profile = next((p for p in profiles if p['screen_name'].lower() == twitter_name.lower()), None)
        if profile:
            print("Match:\t%s\t%s" % (twitter_name, profile['id']))
            soc['twitter_id'] = profile['id']
        else:
            print("No Twitter user profile for:\t", twitter_name)
            if prune_mode:
                print("\t...removing", twitter_name)
                soc.pop('twitter')

def load_creds(creds_path):
    """
    Convenience method for get_twitter_api in which creds_path points to a JSON
    """

    if not creds_path:
        raise RuntimeError("Twitter credentials required; specify path with --creds='some.json'")
    else:
        creds = json.load(open(expanduser(creds_path)))
        # filter keys
        fcreds = { k: creds[k] for k in ['access_token', 'access_token_secret', 'consumer_key', 'consumer_secret']}
        api = get_twitter_api(**fcreds)
        return api






if __name__ == '__main__':
    run()


# if __name__ == '__main__':
#
#     # since we're dealing with only ~500 account names, let's just
#     # brute force collect them up front
#     tnames = [d['social']['twitter'] for d in data if d['social'].get('twitter')]
#     # initialize twitter API
#     api = get_twitter_api(json.load(open(MY_TWIT_CREDS_PATH)))
#     print("Fetching Twitter profiles")
#     profiles = get_twitter_profiles_from_screen_names(api, tnames)


#     for d in data:
#         soc = d['social']
#         tname = soc.get('twitter')
#         if tname and not soc.get('twitter_id'):
#             profile = next((p for p in profiles if p['screen_name'].lower() == tname.lower()), None)
#             if profile:
#                 soc['twitter_id'] = profile['id']
#             else:
#                 print(tname, 'does not exist, removing from data file')
#                 # remove it
#                 soc.pop('twitter')

#     with open(OUTPUT_DATA_PATH, "w") as ofile:
#         utils.save_data(data, "legislators-social-media.yaml")
