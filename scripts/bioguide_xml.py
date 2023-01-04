# Update metadata fields like birthdays from
# bioguide.congress.gov bulk data downloads.
#
# Usage:
# python3 bioguide_xml.py path/to/BioguideProfiles.zip

import sys
import zipfile
import re
import json
import rtyaml
import datetime

def run():
    # Load existing legislators and map bioguide IDs
    # to their entries.
    legislator_data = { }
    legislators = { }
    for ft in ("current", "historical"):
        with open("../legislators-{}.yaml".format(ft)) as f:
            data = rtyaml.load(f)
            legislator_data[ft] = data
            for p in data:
                legislators[p["id"]["bioguide"]] = p

    def parse_birthday_from_text(text):
        # exceptions for not-nicely-placed semicolons
        text = text.replace("born in Cresskill, Bergen County, N. J.; April", "born April")
        text = text.replace("FOSTER, A. Lawrence, a Representative from New York; September 17, 1802;", "born September 17, 1802")
        text = text.replace("CAO, Anh (Joseph), a Representative from Louisiana; born in Ho Chi Minh City, Vietnam; March 13, 1967", "born March 13, 1967")
        text = text.replace("CRITZ, Mark S., a Representative from Pennsylvania; born in Irwin, Westmoreland County, Pa.; January 5, 1962;", "born January 5, 1962")
        text = text.replace("SCHIFF, Steven Harvey, a Representative from New Mexico; born in Chicago, Ill.; March 18, 1947", "born March 18, 1947")
        text = text.replace('KRATOVIL, Frank, M. Jr., a Representative from Maryland; born in Lanham, Prince George\u2019s County, Md.; May 29, 1968', "born May 29, 1968")

        # look for a date
        pattern = r"born [^;]*?((?:January|February|March|April|May|June|July|August|September|October|November|December),? \d{1,2},? \d{4})"
        match = re.search(pattern, text, re.I)
        if not match or not match.group(1):
          # specifically detect cases that we can't handle to avoid unnecessary warnings
          if re.search("birth dates? unknown|date of birth is unknown", text, re.I): return None, None
          if re.search("born [^;]*?(?:in|about|before )?(?:(?:January|February|March|April|May|June|July|August|September|October|November|December) )?\d{4}", text, re.I): return None, None
          return None, None
        original_text = match.group(1).strip()

        try:
          birthday = datetime.datetime.strptime(original_text.replace(",", ""), "%B %d %Y")
        except ValueError:
          print("[%s] BAD BIRTHDAY :(\n\n%s" % (bioguide_id, original_text))
          return None, original_text

        birthday = "%04d-%02d-%02d" % (birthday.year, birthday.month, birthday.day)
        return birthday, original_text

    # Process all profile data in the bioguide ZIP file.
    with zipfile.ZipFile(sys.argv[1]) as zf:
        for profile_fn in zf.namelist():
            bioguide_id = re.match(r"^([A-Z]\d+)\.json", profile_fn).group(1)
            if bioguide_id not in legislators:
                #print("No legislator for", bioguide_id)
                continue
            with zf.open(profile_fn) as zff:
                profile = json.load(zff)
                if "profileText" not in profile:
                    continue

                legislator = legislators[bioguide_id]

                # Get birthday from text.
                birthday, original_text = parse_birthday_from_text(profile["profileText"])
                if birthday:

                    # Check birthday from metadata --- not as reliable.
                    # Since the metadata may only have a year, only match
                    # as much of the date string as it has.
                    if profile.get("birthDate") and not profile.get("birthCirca"):
                        if profile["birthDate"] != birthday[0:len(profile["birthDate"])]:
                             print(bioguide_id, "metadata", repr(profile["birthDate"]), "doesn't match profile text", repr(original_text))
                        else:
                            # They match, so update.
                            legislators.setdefault("bio", {})
                            legislator["bio"]["birthday"] = birthday


    # Write out updated data files.
    for fn in legislator_data:
        with open("../legislators-{}.yaml".format(ft), "w") as f:
            rtyaml.dump(legislator_data[fn], f)

if __name__ == "__main__":
    run()
