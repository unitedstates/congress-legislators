#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for utils.py.
Run from root dir:
`python test/test_utils.py`
"""
import sys
import unittest

sys.path.insert(0, 'scripts')
import utils

class TestFunctions(unittest.TestCase):

    def test_congress_from_legislative_year(self):
        input = 2014
        output = utils.congress_from_legislative_year(input)
        self.assertEqual(output, 113)

if __name__ == '__main__':
    unittest.main()

# End of file
