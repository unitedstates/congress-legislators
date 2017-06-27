#!/usr/bin/env python

import json
import utils
import glob
import os

def run():

	#yaml filenames
    yamls = list(map(os.path.basename, glob.glob("../*.yaml")))

    for filename in yamls:
        print("Converting %s..." % filename)
        data = utils.load_data(filename)

		#convert yaml to json
        utils.write(
            json.dumps(data, default=utils.format_datetime),
            "../alternate_formats/%s.json" %filename.replace(".yaml", ""))

if __name__ == '__main__':
    run()
