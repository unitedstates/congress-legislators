#!/usr/bin/env python

import csv
import json
import unicodedata
import utils
from utils import load_data, mkdir_p, save_data, parse_date

# Update legislators current pictorial ids
# https://pictorialapi.gpo.gov/index.html
#
# options:
#  --cache: load from cache if present on disk (default: false)
#  --bioguide: load only one legislator, by their bioguide ID
#  --congress: do *only* updates for legislators serving in specific congress
#
# example:
#  python pictorial_ids.py --congress=118


def run():

    # default to not caching
    cache = utils.flags().get("cache", False)
    force = not cache

    only_bioguide = utils.flags().get("bioguide", None)
    congress = utils.flags().get("congress", None)

    data_files = []
    print("Loading %s..." % "legislators-current.yaml")
    legislators = load_data("legislators-current.yaml")
    data_files.append((legislators, "legislators-current.yaml"))
    print("Loading %s..." % "legislators-historical.yaml")
    legislators = load_data("legislators-historical.yaml")
    data_files.append((legislators, "legislators-historical.yaml"))

    if congress == None:
        raise Exception("the --congress flag is required")
    elif int(congress) >= 110:
        # Pictorial seems to go back to 110th Congress
        url = f"https://pictorialapi.gpo.gov/api/GuideMember/GetMembers/{congress}"
        pass
    else:
        raise Exception("no data for congress " + congress)

    pictorial_destination = f"pictorial/source/GetMembers/{congress}.json"
    pictorial_data = json.loads(utils.download(url, pictorial_destination, force))

    # Filter out non-legislators and the vacant placeholders
    pictorial_members = [
        member
        for member in pictorial_data["memberCollection"]
        if member["memberType"] in ("Senator", "Representative", "Delegate")
        and member["name"] != "Vacant, Vacant"
    ]

    error_filename = f"cache/errors/pictorial/mismatch_{congress}.csv"
    mkdir_p("cache/errors/pictorial")
    error_log = csv.writer(open(error_filename, "w"))
    error_log.writerow(
        [
            "message",
            "bioguide_id",
            "name_first",
            "name_last",
        ]
    )
    error_count = 0

    print("Running for congress " + congress)
    for legislators, filename in data_files:
        for legislator in legislators:
            # this can't run unless we've already collected a bioguide for this person
            bioguide = legislator["id"].get("bioguide", None)
            # if we've limited this to just one bioguide, skip over everyone else
            if only_bioguide and (bioguide != only_bioguide):
                continue

            # only run for selected congress
            latest_term = legislator["terms"][-1]
            latest_congress = utils.congress_from_legislative_year(
                utils.legislative_year(parse_date(latest_term["start"]))
            )
            if int(congress) != latest_congress:
                continue

            # skip if we already have it
            if legislator["id"].get("pictorial"):
                continue
            try:
                pictorial_id = match_pictorial_id(legislator, pictorial_members)
                legislator["id"]["pictorial"] = pictorial_id
            except ValueError as e:
                error_count += 1
                error_log.writerow(
                    [
                        e,
                        bioguide,
                        legislator["name"]["first"],
                        legislator["name"]["last"],
                    ]
                )

        save_data(legislators, filename)

    if error_count:
        print(f"{error_count} error details written to {error_filename}")


def to_ascii(s):
    return unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")


def reverse_name(name):
    """
    Given a name in "Last, First" format, return "First Last"
    """
    return " ".join(name.split(", ")[::-1])


def match_pictorial_id(legislator, pictorial_members):
    """
    Attempt to find the corresponding pictorial id for the given member.

    There are many odd cases -- see tests/test_gpo_member_photos.py for
    examples.
    """
    name = legislator["name"]["official_full"]

    # Map common nicknames (and GPO typos) from legislators to pictorial
    common_nicknames = {
        "Nick": "Nicolas",
        "Daniel": "Dan",
        "Mike": "Michael",
        "Michael": "Mike",
        "Richard": "Rich",
        "Christopher": "Chris",
        "JOhn": "John",
    }

    matches = []
    for member_pictorial in pictorial_members:
        # First check whether the name matches
        name_matches = False
        legislator_name_last = to_ascii(legislator["name"]["last"].replace(" ", ""))
        legislator_name_first = to_ascii(legislator["name"]["first"].replace(" ", ""))

        if legislator_name_last == member_pictorial["lastName"]:
            if legislator_name_first == member_pictorial["firstName"] or (
                "nickname" in legislator["name"]
                and legislator["name"]["nickname"] == member_pictorial["firstName"]
            ):
                name_matches = True
            # Sometimes the nickname is encoded in the first name
            elif member_pictorial["firstName"] in legislator_name_first:
                name_matches = True
            # Sometimes the nickname is encoded in the middle name
            elif (
                "middle" in legislator["name"]
                and member_pictorial["firstName"] in legislator["name"]["middle"]
            ):
                name_matches = True
            # Sometimes the nickname is not encoded
            elif (
                member_pictorial["firstName"] in common_nicknames
                and common_nicknames[member_pictorial["firstName"]]
                == legislator_name_first
            ):
                name_matches = True

        # Sometimes matching the official full name is best
        if legislator["name"]["official_full"] == reverse_name(
            member_pictorial["name"]
        ):
            name_matches = True

        # The GPO has some first and last names swapped, so check those too
        if not name_matches and legislator_name_first == member_pictorial["lastName"]:
            if legislator_name_last == member_pictorial["firstName"] or (
                "nickname" in legislator["name"]
                and legislator["name"]["nickname"] == member_pictorial["firstName"]
            ):
                name_matches = True

        # If the name matches, check the office and state
        # Note: Assumes we're matching against most recent term
        if name_matches:
            most_recent_term = legislator["terms"][-1]
            mType = "sen" if member_pictorial["memberType"] == "Senator" else "rep"
            if (
                most_recent_term["state"] == member_pictorial["stateId"]
                and most_recent_term["type"] == mType
            ):
                matches.append(member_pictorial)

    if len(matches) == 1:
        return matches[0]["memberId"]
    else:
        if len(matches):
            raise ValueError(f"Multiple pictorial id matches found for {name}")
        else:
            raise ValueError(f"No pictorial id match found for {name}")


if __name__ == "__main__":
    run()
