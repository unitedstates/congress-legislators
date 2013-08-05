import json
from utils import write, format_datetime, load_data

yaml_current = "legislators-current.yaml"
yaml_historical = "legislators-historical.yaml"
yamls = []
yamls.append(yaml_current)
yamls.append(yaml_historical)

for filename in yamls:

	print "Loading %s..." % filename
	legislators = load_data(filename)

	write(
	json.dumps(legislators, sort_keys=True, indent=2, default=format_datetime),
	"../%s.json" %filename.rstrip(".yaml"))