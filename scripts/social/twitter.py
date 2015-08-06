# Helpful functions for accessing Twitter
import tweepy
TWITTER_PROFILE_BATCH_SIZE = 100
from math import ceil

def get_api(access_token, access_token_secret, consumer_key, consumer_secret):
    """
    Takes care of the Twitter OAuth authentication process and
    creates an API-handler to execute commands on Twitter

    Arguments: string values

    Returns:
      A tweepy.api.API object
    """
    # Get authentication token
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    # create an API handler
    return tweepy.API(auth)

def fetch_profiles(api, screen_names = [], ids = []):
    """
    A wrapper method around tweepy.API.lookup_users that handles the batch lookup of
      screen_names. Assuming number of screen_names < 10000, this should not typically
      run afoul of API limits (i.e. it's a good enough hack for now)

    `api` is a tweepy.API handle
    `screen_names` is a list of twitter screen names

    Returns: a list of dicts representing Twitter profiles
    """
    profiles = []
    key, lookups = ['user_ids', ids] if ids else ['screen_names', screen_names]
    for batch_idx in range(ceil(len(lookups) / TWITTER_PROFILE_BATCH_SIZE)):
        offset = batch_idx * TWITTER_PROFILE_BATCH_SIZE
        # break lookups list into batches of TWITTER_PROFILE_BATCH_SIZE
        batch = lookups[offset:(offset + TWITTER_PROFILE_BATCH_SIZE)]
        try:
            for user in api.lookup_users(**{key: batch}):
                profiles.append(user._json)
        # catch situation in which none of the names in the batch are found
        # or else Tweepy will error out
        except tweepy.error.TweepError as e:
            if e.response.status_code == 404:
                pass
            else: # some other error, raise the exception
                raise e
    return profiles
