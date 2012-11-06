# In order to preserve the order of attributes, YAML must be
# hooked to load mappings as OrderedDicts. Adapted from:
# https://gist.github.com/317164
# Additionally, we need to set default output parameters
# controlling formatting.

import yaml
from collections import OrderedDict
from datetime import datetime

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

def yaml_load(stream):
	return yaml.load(stream)

def ordered_dict_serializer(self, data):
	return self.represent_mapping('tag:yaml.org,2002:map', data.items())
yaml.add_representer(OrderedDict, ordered_dict_serializer)
yaml.add_representer(unicode, lambda dumper, value: dumper.represent_scalar(u'tag:yaml.org,2002:str', value))

def yaml_dump(data, stream):
	yaml.dump(data, stream, default_flow_style=False, allow_unicode=True)
	
# Other utilities

def parse_date(date):
	return datetime.strptime(date, "%Y-%m-%d").date()

