# Round-trippable YAML
# --------------------

# This module configures the YAML library so that it round-trips
# files:
#   a) without disturbing field order
#   b) so that it uses some saner output options than the defaults
#   c) preserving any comment block at the very beginning of the file
#
# Usage:
#
#   import rtyaml
#   stuff = rtyaml.load(open("myfile.yaml"))
#   # ...do things to stuf...
#   rtyaml.dump(stuff, open("myfile.yaml", "w"))
#
# Dependencies:
#
# * libyaml (in Ubuntu, the libyaml-0-2 package)
# * pyyaml (in Ubuntu, the python-yaml package)
#
# This library does the following:
#
# * Uses the native libyaml CSafeLoader and CDumper for both speed
#   and trustable operations.
# * Parses mappings as OrderedDicts so that the field order remains
#   the same when dumping the file later.
# * Writes unicode strings without any weird YAML tag. They just
#   appear as strings. Output is UTF-8 encoded, and non-ASCII
#   characters appear as Unicode without escaping.
# * Writes mappings and lists in the expanded (one per line) format,
#   which is nice when the output is going in version control.
# * Modifies the string quote rules so that any string made up of
#   digits is serialized with quotes. (The defaults will omit quotes
#   for octal-ish strings like "09" that are invalid octal notation.)
# * Serializes null values as the tilde, since "null" might be confused
#   for a string-typed value.
# * If a block comment appears at the start of the file (i.e. one or
#   more lines starting with a '#', write back out the commend if the
#   same object is written with rtyaml.dump().)

import sys, re, io
from collections import OrderedDict

import yaml
try:
    # Use the native code backends, if available.
    from yaml import CSafeLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import SafeLoader as Loader, Dumper

# In order to preserve the order of attributes, YAML must be
# hooked to load mappings as OrderedDicts. Adapted from:
# https://gist.github.com/317164

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

Loader.add_constructor('tag:yaml.org,2002:map', construct_odict)
def ordered_dict_serializer(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', list(data.items()))
Dumper.add_representer(OrderedDict, ordered_dict_serializer)

# Likewise, when we store unicode objects make sure we don't write
# them with weird YAML tags indicating the Python data type. str-typed
# strings come out fine, but unicode strings come out with unnecessary
# type tags. The easy solution is this:
#
#   Dumper.add_representer(unicode, lambda dumper, value:
#        dumper.represent_scalar(u'tag:yaml.org,2002:str', value))
#
# However, the standard PyYAML representer for strings does something
# weird: if a value cannot be parsed as an integer quotes are omitted.
#
# This is incredibly odd when the value is an integer with a leading
# zero. These values are typically parsed as octal integers, meaning
# quotes would normally be required (that's good). But when the value
# has an '8' or '9' in it, this would make it an invalid octal number
# and so quotes would no longer be required (that's confusing).
# We will override str and unicode output to choose the quotation
# style with our own logic. (According to PyYAML, style can be one of
# the empty string, ', ", |, or >, or None to, presumably, choose
# automatically.
def our_string_representer(dumper, value):
	# If it looks like an octal number, force '-quote style.
	style = None # let PyYAML choose?
	if re.match(r"^0\d*$", value): style = "'"
	return dumper.represent_scalar('tag:yaml.org,2002:str', value, style=style)
Dumper.add_representer(str, our_string_representer)
Dumper.add_representer(str, our_string_representer)

# Add a representer for nulls too. YAML accepts "~" for None, but the
# default output converts that to "null". Override to always use "~".
Dumper.add_representer(type(None), lambda dumper, value : \
	dumper.represent_scalar('tag:yaml.org,2002:null', "~"))


# Provide some wrapper methods that apply typical settings.

def load(stream):
    return yaml.load(stream, Loader=Loader)


def dump(data, stream):
    # if we got a file, check if there's an initial comment bloc
    if hasattr(stream, "seek") and hasattr(stream, "readline"):
        # Read any comment block at the start. We can only do this if we can
        # seek the stream back to the start so we can write out the contents
        # at the beginning of the file.
        initial_comment_block = ""
        while True:
            line = stream.readline()
            if line[0] != '#': break
            initial_comment_block += line

        stream.seek(0)
        stream.truncate() # in case file shrinks, make sure we don't leave anything at the end

        if initial_comment_block:
            stream.write(initial_comment_block)

    # Write the object to the stream.
    yaml.dump(data, stream, default_flow_style=False, allow_unicode=True, Dumper=Dumper)

def pprint(data):
    yaml.dump(data, sys.stdout, default_flow_style=False, allow_unicode=True)

