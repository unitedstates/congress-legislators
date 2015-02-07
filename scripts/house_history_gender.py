import re, urllib.request, urllib.parse
from utils import yaml_load, yaml_dump

def run():

	# Use the House History Website's Women in Congress search results to get a list of IDs.
	# Because this requires a POST, our utils.download() function won't work.
	querystring = b"Command=Next&Term=Search&SearchIn=LastName&ShowNonMember=true&ShowNonMember=false&Office=&Leadership=&State=&Party=&ContinentalCongress=false&BlackAmericansInCongress=false&WomenInCongress=true&WomenInCongress=false&HispanicAmericansInCongress=false&CongressNumber=65&CongressNumber=66&CongressNumber=67&CongressNumber=68&CongressNumber=69&CongressNumber=70&CongressNumber=71&CongressNumber=72&CongressNumber=73&CongressNumber=74&CongressNumber=75&CongressNumber=76&CongressNumber=77&CongressNumber=78&CongressNumber=79&CongressNumber=80&CongressNumber=81&CongressNumber=82&CongressNumber=83&CongressNumber=84&CongressNumber=85&CongressNumber=86&CongressNumber=87&CongressNumber=88&CongressNumber=89&CongressNumber=90&CongressNumber=91&CongressNumber=92&CongressNumber=93&CongressNumber=94&CongressNumber=95&CongressNumber=96&CongressNumber=97&CongressNumber=98&CongressNumber=99&CongressNumber=100&CongressNumber=101&CongressNumber=102&CongressNumber=103&CongressNumber=104&CongressNumber=105&CongressNumber=106&CongressNumber=107&CongressNumber=108&CongressNumber=109&CongressNumber=110&CongressNumber=111&CongressNumber=112&CongressNumber=113&CongressNumber=114&CurrentPage=__PAGE__&SortOrder=LastName&ResultType=Grid&PreviousSearch=Search%2CLastName%2C%2C%2C%2C%2CFalse%2CFalse%2CTrue%2C65%2C66%2C67%2C68%2C69%2C70%2C71%2C72%2C73%2C74%2C75%2C76%2C77%2C78%2C79%2C80%2C81%2C82%2C83%2C84%2C85%2C86%2C87%2C88%2C89%2C90%2C91%2C92%2C93%2C94%2C95%2C96%2C97%2C98%2C99%2C100%2C101%2C102%2C103%2C104%2C105%2C106%2C107%2C108%2C109%2C110%2C111%2C112%2C113%2C114%2CLastName&X-Requested-With=XMLHttpRequest"
	women_house_history_ids = set()
	for pagenum in range(0, 30+1):
		body = urllib.request.urlopen(
			"http://history.house.gov/People/Search?Length=6",
			querystring.replace(b"__PAGE__", str(pagenum).encode("ascii"))
			).read().decode("utf8")
		for match in re.findall(r"/People/Detail/(\d+)\?ret=True", body):
			women_house_history_ids.add(int(match))

	# Now check and update the gender of all legislators.
	matched_women_house_history_ids = set()
	missing_ids = set()
	for fn in ("../legislators-current.yaml", "../legislators-historical.yaml"):
		legislators = yaml_load(fn)
		for p in legislators:
			house_history_id = p.get("id", {}).get("house_history")

			if not house_history_id:
				# We have all of the women, so anyone left must be a man.
				p.setdefault("bio", {})["gender"] = "M"
				missing_ids.add(p.get("id", {}).get("bioguide"))
				continue

			p.setdefault("bio", {})["gender"] = "F" if house_history_id in women_house_history_ids else "M"

			if house_history_id in women_house_history_ids:
				matched_women_house_history_ids.add(house_history_id)

		yaml_dump(legislators, fn)

	print("%d women in Congress reported by the House History website" % len(women_house_history_ids))
	print("%d women in Congress were not found in our files." % len(women_house_history_ids-matched_women_house_history_ids))
	print(" ", " ".join((str(x) for x in (women_house_history_ids-matched_women_house_history_ids))))
	print("%d legislators are missing house_history IDs, set to male." % len(missing_ids))

if __name__ == '__main__':
  run()