# Just loads and saves each .yaml file to normalize serialization syntax.
#
# python lint.py
# ... will lint every .yaml file in the data directory.
#
# python lint.py file1.yaml file2.yaml ...
# ... will lint the specified files.

import glob, sys
from utils import yaml_load, yaml_dump, data_dir

def run():
    for fn in glob.glob(data_dir() + "/*.yaml") if len(sys.argv) == 1 else sys.argv[1:]:
        print(fn + "...")
        data = yaml_load(fn, use_cache=False)
        yaml_dump(data, fn)

if __name__ == '__main__':
  run()