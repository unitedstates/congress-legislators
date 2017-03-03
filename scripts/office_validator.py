"""

Run validation tests on district office data.


For each legislator:
    has offices

For each office:
    Expected fields: address, city, state, zip, phone, latitude, longitude, id
    Office id: check consistent
    offices are in legislator's state

Globally:
    Every legislator has offices
    All offices belong to current legislators

"""

import logging as log
import os.path
import re
from collections import OrderedDict, defaultdict
from itertools import count

try:
    import rtyaml as yaml
except ImportError:
    import yaml


log.basicConfig(format='%(message)s')
error = log.error

NONALPHA = re.compile(r"[ .'-]")
PHONE = re.compile(r"\d{3}-\d{3}-\d{4}")


def relfile(path):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), path))


def id_offices(bioguide_id, offices):
    """
    Generate unique office ids using a similar algorithm to
    https://github.com/controlshift/congress-legislators/blob/add-ids-to-offices-script/add_ids_to_offices.rb

    Used for validation here, but could be used to generate ids.
    """
    id_count = defaultdict(count)
    for office in offices:
        locality = office.get('city', 'no_city').lower()
        locality = NONALPHA.sub('_', locality)

        office_id = '-'.join([bioguide_id, locality])

        city_count = next(id_count[office_id])
        if city_count:
            office_id = '-'.join([office_id, str(city_count)])

        yield office_id, office


def check_legislator_offices(legislator_offices, legislator):
    bioguide_id = legislator_offices['id']['bioguide']
    offices = legislator_offices.get('offices', [])

    state = None
    if legislator:
        state = legislator['terms'][-1]['state']

    expected = ['id', 'address', 'city', 'state', 'zip', 'phone',
                'latitude', 'longitude']

    if not legislator:
        yield "Offices for inactive legislator"

    if not offices:
        yield "Zero offices"

    for office_id, office in id_offices(bioguide_id, offices):

        for field in expected:
            if not office.get(field):
                yield "Office %s is missing field '%s'" % (office_id, field)

        found_id = office.get('id')
        if found_id and office_id != found_id:
            yield "Office %s has unexpected id '%s'" % (office_id, found_id)

        office_state = office.get('state')
        if state and office_state and office_state != state:
            yield ("Office %s is in '%s', legislator is from '%s'"
                   "") % (office_id, office_state, state)

        phone = office.get('phone')
        fax = office.get('fax')

        if phone and not PHONE.match(phone):
            yield("Office %s phone '%s' does not match format ddd-ddd-dddd"
                  "") % (office_id, phone)

        if fax and not PHONE.match(fax):
            yield("Office %s fax '%s' does not match format ddd-ddd-dddd"
                  "") % (office_id, fax)


def load_to_dict(path):
    # load to an OrderedDict keyed by bioguide id
    d = yaml.load(open(relfile(path)))
    return OrderedDict((l['id']['bioguide'], l) for l in d)

def print_errors(legislator, errors):
    if isinstance(legislator, basestring):
        info = legislator
    else:
        term = legislator['terms'][-1]
        info = u"{} [{} {}] {} ({})".format(
            legislator['id']['bioguide'], term['state'], term['type'],
            legislator['name']['official_full'], term.get('url', 'no url'))

    print_blank = False
    for i, err in enumerate(errors):
        if i == 0:
            print info.encode('utf-8')
            print_blank = True
        print (" " * 4 + err).encode('utf-8')
    if print_blank:
        print ""


def run():
    legislators = load_to_dict("../legislators-current.yaml")
    legislators_offices = load_to_dict("../legislators-district-offices.yaml")

    for bioguide_id, legislator_offices in legislators_offices.items():
        legislator = legislators.get(bioguide_id)

        errors = check_legislator_offices(legislator_offices, legislator)

        print_errors(legislator or bioguide_id, errors) 

    for bioguide_id in set(legislators.keys()) - set(legislators_offices.keys()):
        legislator = legislators.get(bioguide_id)
        print_errors(legislator or bioguide_id, ["No offices"])


if __name__ == '__main__':
    run()
