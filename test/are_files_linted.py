# Check that each YAML file has been linted.

import difflib
import glob
import io
import sys

import rtyaml

ok = True

for fn in glob.glob("*.yaml"):
  with open(fn) as f:
    body = f.read()

  # Round-trip the file. Because of the comment block at the top
  # of legislators-social-media.yaml, we need to go through file-like
  # streams so that rtyaml preserves it.
  data = rtyaml.load(io.StringIO(body))

  # Save it back to a buffer.
  buf = io.StringIO()
  rtyaml.dump(data, buf)
  buf = buf.getvalue()

  # Check that the file round-trips to the same bytes,
  # except don't worry about trailing newlines because
  # editors mess with the last line line ending.
  if buf.rstrip() != body.rstrip():
    ok = False
    print(fn, "needs to be linted:")

    # Show a diff.
    for line in difflib.unified_diff(body.split("\n"), buf.split("\n"), fromfile='in repository', tofile='after linting', lineterm=''):
      print(line)

sys.exit(0 if ok else 1)
