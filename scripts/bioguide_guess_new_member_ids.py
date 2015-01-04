import rtyaml

from bioguide import fetch_bioguide_page

def run():

  print("Finding highest bioguide numbers we know of...")
  highest_num_by_letter = { }
  for fn in ('legislators-current', 'legislators-historical'):
    P = rtyaml.load(open('../%s.yaml' % fn))
    for p in P:
      if not p['id'].get('bioguide'): continue
      if p['id']['bioguide'] == "TODO": continue # 114th Congress staging
      letter = p['id']['bioguide'][0]
      num = p['id']['bioguide'][1:]
      highest_num_by_letter[letter] = max(highest_num_by_letter.get(letter, ''), num)

  print("Checking for new bioguide pages...")
  for letter in sorted(highest_num_by_letter):
    num = int(highest_num_by_letter[letter])
    while True:
      num += 1
      bioguide = "%s%06d" % (letter, num)
      try:
        dom = fetch_bioguide_page(bioguide, True)
      except Exception:
        break
      print(bioguide, dom.cssselect("title")[0].text)

if __name__ == '__main__':
  run()
