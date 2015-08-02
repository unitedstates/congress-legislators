# standalone script to read legislators-social-media.yaml
#  and then add twitter ids derived from Twitter usernames
#  Twitter names that do not successfully fetch a profile are removed
#  A file is created in OUTPUT_DATA_PATH
#  [script added as proof of concept and is not part of the actual build process]
#
# run:
# python3 ./scripts/fetch_and_insert_twitter_ids.py
#

# requires:
#  Python3
#  tweepy
#
#
import tweepy
import rtyaml
import json
from os.path import expanduser
from math import ceil

TWITTER_PROFILE_BATCH_SIZE = 100
OUTPUT_DATA_PATH = "/tmp/new-social-media.yaml"
MY_TWIT_CREDS_PATH = expanduser("~/.creds/twit.json")

def get_twitter_api(creds):
    """
    Takes care of the Twitter OAuth authentication process and
    creates an API-handler to execute commands on Twitter

    Arguments:
      - creds (dict): {
            "consumer_secret": "xyz",
            "access_token": "abc",
            "access_token_secret": "def",
            "consumer_key": "jk"
        }

    Returns:
      A tweepy.api.API object

    """
    # Get authentication token
    auth = tweepy.OAuthHandler(consumer_key = creds['consumer_key'],
                               consumer_secret = creds['consumer_secret'])
    auth.set_access_token(creds['access_token'], creds['access_token_secret'])
    # create an API handler
    return tweepy.API(auth)

def get_twitter_profiles_from_screen_names(api, screen_names):
    """
    `api` is a tweepy.API handle
    `screen_names` is a list of twitter screen names

    Returns: a list of dicts representing Twitter profiles
    """
    profiles = []
    for i in range(ceil(len(data) / TWITTER_PROFILE_BATCH_SIZE)):
        print("Batch %s" % i)
        s = i * TWITTER_PROFILE_BATCH_SIZE
        batchnames = screen_names[s:(s + TWITTER_PROFILE_BATCH_SIZE)]
        for user in api.lookup_users(screen_names = batchnames):
            profiles.append(user._json)

    return profiles


# meh

if __name__ == '__main__':
    data = rtyaml.load(open("legislators-social-media.yaml"))
    # since we're dealing with only ~500 account names, let's just
    # brute force collect them up front
    tnames = [d['social']['twitter'] for d in data if d['social'].get('twitter')]
    # initialize twitter API
    api = get_twitter_api(json.load(open(MY_TWIT_CREDS_PATH)))
    print("Fetching Twitter profiles")
    profiles = get_twitter_profiles_from_screen_names(api, tnames)


    for d in data:
        soc = d['social']
        tname = soc.get('twitter')
        if tname and not soc.get('twitter_id'):
            profile = next((p for p in profiles if p['screen_name'].lower() == tname.lower()), None)
            if profile:
                soc['twitter_id'] = profile['id']
            else:
                print(tname, 'does not exist, removing from data file')
                # remove it
                soc.pop('twitter')

    with open(OUTPUT_DATA_PATH, "w") as ofile:
        rtyaml.dump(data, ofile)
        print("Saved to", OUTPUT_DATA_PATH)
        # manually copy this over to the original file
