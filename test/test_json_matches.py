#!/usr/bin/env python

import json
import rtyaml
import glob

def jsonKeys2str(x):
    """Some of the yamls have integer keys, which json converts to string.
    in the future if there are keys that are strings that are intended to be left
    as strings this may break"""
    if isinstance(x, dict):
        return {(int(k) if k.isdigit() else k):v for k, v in x.items()}
    return x

yamls = glob.glob("*.yaml")

ret = 0
for path in yamls:
    yaml_data = rtyaml.load(open(path))
    json_data = json.load(
	       open("alternate_formats/{}".format(
		                 path.replace(".yaml", ".json")), 'r'),
	       object_hook=jsonKeys2str)
    if yaml_data != json_data:
        ret = 1
        print("Error: {} does not match the generated json.".format(path))

exit(ret)
