#!/usr/bin/env python

import csv, re
import utils
from utils import download, load_data, save_data, parse_date

social_media = load_data("legislators-social-media.yaml")

new_social_media = []

for l in social_media:
  if l['social'].has_key('facebook_graph'):
    del l['social']['facebook_graph']
  if len(l['social']) > 0:
    new_social_media.append(l)

save_data(new_social_media, "legislators-social-media.yaml")