# Helpful functions for finding data about members and committees

CURRENT_CONGRESS = 113

import urllib2
import os, errno, sys, traceback
import re, htmlentitydefs
import pprint
import rtyaml
from datetime import datetime

import lxml.html # for meta redirect parsing

def parse_date(date):
  return datetime.strptime(date, "%Y-%m-%d").date()

def log(object):
  if isinstance(object, (str, unicode)):
    print object
  else:
    pprint(object)

def uniq(seq):
  seen = set()
  seen_add = seen.add
  return [ x for x in seq if x not in seen and not seen_add(x)]

def flags():
  options = {}
  for arg in sys.argv[1:]:
    if arg.startswith("--"):

      if "=" in arg:
        key, value = arg.split('=')
      else:
        key, value = arg, True

      key = key.split("--")[1]
      if value == 'True': value = True
      elif value == 'False': value = False
      options[key.lower()] = value
  return options

##### Data management

def data_dir():
  return ".."

def load_data(path):
  return yaml_load(os.path.join(data_dir(), path))

def save_data(data, path):
  return yaml_dump(data, os.path.join(data_dir(), path))


##### Downloading

import scrapelib
scraper = scrapelib.Scraper(requests_per_minute=60, follow_robots=False, retry_attempts=3)
scraper.user_agent = "github.com/unitedstates/congress-legislators"

def cache_dir():
  return "cache"

def download(url, destination=None, force=False, options=None):
  if not destination and not force:
    raise TypeError("destination must not be None if force is False.")

  if not options:
    options = {}

  # get the path to cache the file, or None if destination is None
  cache = os.path.join(cache_dir(), destination) if destination else None

  if not force and os.path.exists(cache):
    if options.get('debug', False):
      log("Cached: (%s, %s)" % (cache, url))

    with open(cache, 'r') as f:
      body = f.read()
  else:
    try:
      if options.get('debug', False):
        log("Downloading: %s" % url)

      if options.get('urllib', False):
        response = urllib2.urlopen(url)
        body = response.read()
      else:
        response = scraper.urlopen(url)
        body = response.encode('utf-8')
    except scrapelib.HTTPError as e:
      log("Error downloading %s" % url)
      return None

    # don't allow 0-byte files
    if (not body) or (not body.strip()):
      return None

    # the downloader can optionally parse the body as HTML
    # and look for meta redirects. a bit expensive, so opt-in.
    if options.get('check_redirects', False):
      html_tree = lxml.html.fromstring(body)
      meta = html_tree.xpath("//meta[translate(@http-equiv, 'REFSH', 'refsh') = 'refresh']/@content")
      if meta:
        attr = meta[0]
        wait, text = attr.split(";")
        if text.lower().startswith("url="):

          new_url = text[4:]
          print "Found redirect, downloading %s instead.." % new_url

          options.pop('check_redirects')
          body = download(new_url, None, True, options)

    # cache content to disk
    if cache: write(body, cache)


  return body

def write(content, destination):
  mkdir_p(os.path.dirname(destination))
  f = open(destination, 'w')
  f.write(content)
  f.close()

# mkdir -p in python, from:
# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as exc: # Python >2.5
    if exc.errno == errno.EEXIST:
      pass
    else:
      raise

def format_exception(exception):
  exc_type, exc_value, exc_traceback = sys.exc_info()
  return "\n".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

# taken from http://effbot.org/zone/re-sub.htm#unescape-html
def unescape(text):

  def remove_unicode_control(str):
    remove_re = re.compile(u'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]')
    return remove_re.sub('', str)

  def fixup(m):
    text = m.group(0)
    if text[:2] == "&#":
      # character reference
      try:
        if text[:3] == "&#x":
          return unichr(int(text[3:-1], 16))
        else:
          return unichr(int(text[2:-1]))
      except ValueError:
        pass
    else:
      # named entity
      try:
        text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
      except KeyError:
        pass
    return text # leave as is

  text = re.sub("&#?\w+;", fixup, text)
  text = remove_unicode_control(text)
  return text

##### YAML serialization ######

# Apply some common settings for loading/dumping YAML and cache the
# data in pickled format which is a LOT faster than YAML.

def yaml_load(path, use_cache=True):
    # Loading YAML is ridiculously slow, so cache the YAML data
    # in a pickled file which loads much faster.

    # Check if the .pickle file exists and a hash stored inside it
    # matches the hash of the YAML file, and if so unpickle it.
    import cPickle as pickle, os.path, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    if use_cache and os.path.exists(path + ".pickle"):

        try:
          store = pickle.load(open(path + ".pickle"))
          if store["hash"] == h:
            return store["data"]
        except EOFError:
          pass # bad .pickle file, pretend it doesn't exist

    # No cached pickled data exists, so load the YAML file.
    data = rtyaml.load(open(path))

    # Store in a pickled file for fast access later.
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

    return data

def yaml_dump(data, path):
    rtyaml.dump(data, open(path, "w"))

    # Store in a pickled file for fast access later.
    import cPickle as pickle, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

def pprint(data):
    rtyaml.pprint(data)

