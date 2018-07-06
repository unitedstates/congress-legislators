"""

Run validation tests on district office data.


For each legislator:
    has offices

For each office:
    Required fields: id, city, state
    Expected fields: address, city, state, zip, phone, latitude, longitude, id
    Optional fields: building, fax, hours, suite
    Office id: check consistent
    offices are in legislator's state

Globally:
    Every legislator has offices
    All offices belong to current legislators

"""

import datetime
import os.path
import re
from collections import OrderedDict, defaultdict
from itertools import count
import sys

try:
    import rtyaml as yaml
except ImportError:
    import yaml

try:
    from termcolor import colored
except ImportError:
    colored = None


NONALPHA = re.compile(r"\W")
PHONE = re.compile(r"^\d{3}-\d{3}-\d{4}$")
FIELD_ORDER = """

    id
    address suite building
    city state zip
    latitude longitude
    fax hours phone

""".split()


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

    required = ['id', 'city', 'state']
    expected = ['address', 'zip', 'phone', 'latitude', 'longitude']
    optional = ['building', 'suite', 'hours', 'fax']
    all_fields = set(required + expected + optional)

    errors = []
    warnings = []

    if not legislator:
        errors.append("Offices for inactive legislator")

    if not offices:
        errors.append("Zero offices")

    for office_id, office in id_offices(bioguide_id, offices):

        for field in required:
            if not office.get(field):
                errors.append("Office %s is missing required field '%s'" % (office_id, field))

        for field in expected:
            if not office.get(field):
                warnings.append("Office %s is missing field '%s'" % (office_id, field))

        for field in office:
            if field not in all_fields:
                errors.append("Office %s has unrecognized field '%s'" % (office_id, field))
            if not office.get(field):
                warnings.append("Office %s has empty field %s" % (office_id, field))

        found_id = office.get('id')
        if found_id and office_id != found_id:
            errors.append("Office %s has unexpected id '%s'" % (office_id, found_id))

        office_state = office.get('state')
        if state and office_state and office_state != state:
            errors.append("Office %s is in '%s', legislator is from '%s'" % (office_id, office_state, state))

        phone = office.get('phone')
        fax = office.get('fax')

        if phone and not PHONE.match(phone):
            errors.append("Office %s phone '%s' does not match format ddd-ddd-dddd" % (office_id, phone))

        if fax and not PHONE.match(fax):
            errors.append("Office %s fax '%s' does not match format ddd-ddd-dddd" % (office_id, fax))

        if (office.get('address') and
                not (office.get('latitude') and office.get('longitude'))):
            warnings.append("Office %s missing geocode" % office_id)

        if not office.get('address') and not office.get('phone'):
            errors.append("Office %s needs at least address or phone" % office_id)

        fields = [f for f in office if f in FIELD_ORDER]  # unknown fields checked above
        sorted_fields = sorted(fields, key=FIELD_ORDER.index)
        if fields != sorted_fields:
            warnings.append("Office %s fields out of order, expected %s" % (office_id, sorted_fields))

    return errors, warnings


def load_to_dict(path):
    # load to an OrderedDict keyed by bioguide id
    d = yaml.load(open(relfile(path)))
    return OrderedDict((l['id']['bioguide'], l) for l in d)


def print_issues(legislator, errors, warnings):
    if not (errors or warnings):
        return

    if isinstance(legislator, str):
        info = legislator
    else:
        term = legislator['terms'][-1]
        info = "{} [{} {}] {} ({})".format(
            legislator['id']['bioguide'], term['state'], term['type'],
            legislator['name'].get('official_full'), term.get('url', 'no url'))

    print(info)

    for error in errors:
        msg = "    ERROR: {}".format(error)
        if colored:
            msg = colored(msg, "red")
        print(msg)
    for warning in warnings:
        msg = "    WARNING: {}".format(warning)
        if colored:
            msg = colored(msg, "yellow")
        print(msg)
    print("")


def run(skip_warnings=False):
    legislators = load_to_dict("../legislators-current.yaml")
    legislators_offices = load_to_dict("../legislators-district-offices.yaml")

    has_errors = False

    for bioguide_id, legislator_offices in legislators_offices.items():
        legislator = legislators.get(bioguide_id)

        errors, warnings = check_legislator_offices(legislator_offices, legislator)

        if skip_warnings:
            warnings = []

        if errors:
            has_errors = True

        print_issues(legislator or bioguide_id, errors, warnings)

    for bioguide_id in set(legislators) - set(legislators_offices):
        # Only report an error for a missing office if the
        # legislator has been in office for at least 60 days.
        start_date = legislators[bioguide_id]['terms'][-1]['start']
        if datetime.date.today() - datetime.datetime.strptime(start_date, '%Y-%m-%d').date() >= datetime.timedelta(60):
            has_errors = True
            errors, warnings = ["No offices"], []
        else:
            errors, warnings = [], ["No offices"]
        print_issues(legislators[bioguide_id], errors, warnings)

    return has_errors

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-warnings", action="store_true")
    args = parser.parse_args()

    has_errors = run(skip_warnings=args.skip_warnings)
    sys.exit(1 if has_errors else 0)
