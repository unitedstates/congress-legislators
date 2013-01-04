# Helpful functions for finding data about members and committees

CURRENT_CONGRESS = 112


import os, errno, sys, traceback
import re, htmlentitydefs
import pprint
from datetime import datetime

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
scraper = scrapelib.Scraper(requests_per_minute=120, follow_robots=False, retry_attempts=3)

def cache_dir():
  return "cache"

def download(url, destination, force=False, options=None):
  if not options:
    options = {}

  cache = os.path.join(cache_dir(), destination)

  if not force and os.path.exists(cache):
    if options.get('debug', False):
      log("Cached: (%s, %s)" % (cache, url))

    with open(cache, 'r') as f:
      body = f.read()
  else:
    try:
      if options.get('debug', False):
        log("Downloading: %s" % url)
      response = scraper.urlopen(url)
      body = response.encode('utf-8')
    except scrapelib.HTTPError as e:
      log("Error downloading %s" % url)
      return None

    # don't allow 0-byte files
    if (not body) or (not body.strip()):
      return None

    # cache content to disk
    write(body, cache)

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

# In order to preserve the order of attributes, YAML must be
# hooked to load mappings as OrderedDicts. Adapted from:
# https://gist.github.com/317164
# Additionally, we need to set default output parameters
# controlling formatting.

import yaml
from collections import OrderedDict

def construct_odict(load, node):
    omap = OrderedDict()
    yield omap
    if not isinstance(node, yaml.MappingNode):
        raise yaml.constructor.ConstructorError(
            "while constructing an ordered map",
            node.start_mark,
            "expected a map, but found %s" % node.id, node.start_mark
        )
    for key, value in node.value:
        key = load.construct_object(key)
        value = load.construct_object(value)
        omap[key] = value

yaml.add_constructor(u'tag:yaml.org,2002:map', construct_odict)

def yaml_load(path):
    # Loading YAML is ridiculously slow, so cache the YAML data
    # in a pickled file which loads much faster.

    # Check if the .pickle file exists and a hash stored inside it
    # matches the hash of the YAML file, and if so unpickle it.
    import cPickle as pickle, os.path, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    if os.path.exists(path + ".pickle"):
        store = pickle.load(open(path + ".pickle"))
        if store["hash"] == h:
            return store["data"]
	
	# No cached pickled data exists, so load the YAML file.
    data = yaml.load(open(path))
    
    # Store in a pickled file for fast access later.
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))
    
    return data

def ordered_dict_serializer(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', data.items())
yaml.add_representer(OrderedDict, ordered_dict_serializer)
yaml.add_representer(unicode, lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))

def yaml_dump(data, path):
    yaml.dump(data, open(path, "w"), default_flow_style=False, allow_unicode=True)

    # Store in a pickled file for fast access later.
    import cPickle as pickle, hashlib
    h = hashlib.sha1(open(path).read()).hexdigest()
    pickle.dump({ "hash": h, "data": data }, open(path+".pickle", "w"))

def pprint(data):
    yaml.dump(data, sys.stdout, default_flow_style=False, allow_unicode=True)

