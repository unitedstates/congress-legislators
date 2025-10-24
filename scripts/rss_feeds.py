from feedfinder2 import find_feeds
import json
import pathlib
import requests
import feedparser
import sys
from datetime import datetime, timedelta, timezone
from utils import load_data, save_data, states as state_names

def check_feed(url: str, days: int) -> bool:
    """
    Check whether an RSS feed has any entries published within the last `days` days.

    This function downloads and parses an RSS (or Atom) feed using a browser-like
    User-Agent string. Datetimes are normalized to UTC to avoid comparisons between naive and
    timezone-aware datetimes.

    Args:
        feed_url (str): The URL of the RSS or Atom feed to fetch.
        days (int, optional): The number of days in the look-back period.
            Defaults to 60 (≈ two months).

    Returns:
        bool: True if at least one entry in the feed was published within
        the past `days` days, otherwise False.

    Raises:
        requests.exceptions.RequestException:
            If there is a network error, timeout, or non-2xx HTTP response.
        Exception:
            If parsing fails or the feed structure is invalid.

    Example:
        >>> check_feed("https://example.com/feed.xml", days=30)
        True
    """

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # Download the feed
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error on {e} on {url}")
        return False


    # Parse the feed
    feed = feedparser.parse(response.text)

    # Calculate cutoff date (2 months ago)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Check if there are entries newer than cutoff
    for entry in feed.entries:
        if "published_parsed" in entry and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6])
            # avoids offset-native datetime compare error
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published > cutoff:
                return True

    return False

script_path = pathlib.Path(__file__).parent.resolve()

current = load_data(f"{script_path}/../legislators-current.yaml")

days_to_check = 60

counter = 0
for item in current:

    counter += 1 

    # For testing saving
    # if counter > 30:
    #     save_data(current, f"{script_path}/../legislators-current.yaml")
    #     sys.exit()

    term = item['terms'][-1]
    print(f"Checking for RSS for {item['name']['official_full']}")

    # skip senate republicans drupal sites, none have valid feeds
    if term['type'] == 'sen' and term['party'] == 'Republican':
        print(f"Skipping {item['id']['bioguide']}, republican senator\n")
        continue

    if 'url' in term and 'rss_url' in term:
        try:
            if not check_feed(term['rss_url'], days_to_check):
                print(f"Removing defunct url {term['rss_url']}")
                del term['rss_url']    
        except requests.exceptions.ConnectionError as e:
            print(f"Connection Error {e} on {term['url']} check url veracity")

    if not 'rss_url' in term and 'url' in term:
        print(f"Checking for feeds in {term['url']}")
        feeds = find_feeds(term['url'])
        good_feeds = []
        for feed in feeds:
            if check_feed(feed, days_to_check):
                good_feeds.append(feed)

        if len(good_feeds):
            print("Found 1 or more good feeds.")
            print(good_feeds)
            term['rss_url'] = good_feeds[0]

    print("\n")

save_data(current, f"{script_path}/../legislators-current.yaml")