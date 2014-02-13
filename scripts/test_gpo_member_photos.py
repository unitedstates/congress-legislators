#!/usr/bin/env python
# -*- coding: utf-8 -*- 
"""
Unit tests for gpo_member_photos.py
"""
import gpo_member_photos
import unittest

class TestSequenceFunctions(unittest.TestCase):

    yaml_data = None

    def setUp(self):
        if self.yaml_data is None:
            self.__class__.yaml_data = gpo_member_photos.load_yaml("legislators-test.yaml")
            self.assertTrue(len(self.yaml_data))


    # Test bioguide_id_from_url()

    def test_bioguide_id_from_url__last_char_not_slash(self):
        """ Test last char is not / """
        input = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=S001177/"
        output = gpo_member_photos.bioguide_id_from_url(input)
        self.assertNotEqual(output[-1], "/")

    def test_bioguide_id_from_url__last_char_not_slash2(self):
        """ Test last char is not / """
        input = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=S001177"
        output = gpo_member_photos.bioguide_id_from_url(input)
        self.assertNotEqual(output[-1], "/")

    def test_bioguide_id_from_url__is_string(self):
        """ Test output is string """
        input = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=S001177/"
        output = gpo_member_photos.bioguide_id_from_url(input)
        self.assertTrue(isinstance(output, str))

    def test_bioguide_id_from_url__uppercase(self):
        """ Test output is string """
        input = "http://bioguide.congress.gov/scripts/biodisplay.pl?index=e000288/"
        output = gpo_member_photos.bioguide_id_from_url(input)
        self.assertEqual(output[0], "E")


    # Test bioguide_id_valid()

    def test_bioguide_id_valid__None_returns_False(self):
        """ Test with None """
        input = None
        output = gpo_member_photos.bioguide_id_valid(input)
        self.assertFalse(output)

    def test_bioguide_id_valid__returns_True(self):
        """ Test with a valid ID """
        input = "K000362"
        output = gpo_member_photos.bioguide_id_valid(input)
        self.assertTrue(output)

    def test_bioguide_id_valid__returns_False(self):
        """ Test with an invalid ID """
        input = "aK000362z"
        output = gpo_member_photos.bioguide_id_valid(input)
        self.assertFalse(output)

    def test_bioguide_id_valid_url__returns_False(self):
        """ Test with an invalid ID, an URL """
        input = "http://young.house.gov"
        output = gpo_member_photos.bioguide_id_valid(input)
        self.assertFalse(output)

    def test_bioguide_id_valid_url__first_not_cap(self):
        """ Test with lower case initial """
        input = "r000515"
        output = gpo_member_photos.bioguide_id_valid(input)
        self.assertFalse(output)


    # Test remove_from_yaml()

    def test_remove_from_yaml__success(self):
        """ Test smaller after remove """
        bioguide_id = "C000127"
        length_before = len(self.yaml_data)
        
        self.yaml_data = gpo_member_photos.remove_from_yaml(self.yaml_data, bioguide_id)
        self.assertTrue(length_before > len(self.yaml_data))
        self.assertEqual(len(self.yaml_data) + 1, length_before)
        
    def test_remove_from_yaml__not_found(self):
        """ Test same size """
        bioguide_id = "NOT_THERE"
        length_before = len(self.yaml_data)
        self.yaml_data = gpo_member_photos.remove_from_yaml(self.yaml_data, bioguide_id)
        self.assertEqual(len(self.yaml_data), length_before)


    # Test reverse_names()

    def test_reverse_names(self):
        """ Test reversing names """
        text = "Hagan, Kay R."
        output = gpo_member_photos.reverse_names(text)
        self.assertEqual(output, "Kay R. Hagan")


    # Test resolve()

    def test_resolve__exact_match_last_first(self):
        """ Test resolve """
        text = "Alexander, Lamar"
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "A000360")
        
    def test_resolve__exact_match_last_first_middle(self):
        """ Test resolve """
        text = "Amodei, Mark E."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "A000369")
        
    def test_resolve__exact_match_last_nickname(self):
        """ Test resolve """
        text = "Isakson, Johnny"
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "I000055")
        
    def test_resolve__with_accented_chars(self):
        """ Test resolve """
        text = u"Velázquez, Nydia M."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "V000081")
        
    def test_resolve__initial_dot_from_middle(self):
        """ Test resolve """
        text = "Kirk, Mark S."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "K000360")

    def test_resolve__initial_dot_from_middle(self):
        """ Test resolve """
        text = "Kirk, Mark S."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "K000360")

    def test_resolve__initial_not_in_yaml(self):
        """ Test resolve """
        text = "Ayotte, Kelly A."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "A000368")

    def test_resolve__remove_nickname_quotes(self):
        """ Test resolve """
        text = str('Barr, Garland “Andy"')
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "B001282")

    def test_resolve__quoted_nickname(self):
        """ Test resolve """
        text = 'Fleischmann, Charles J. “Chuck"'
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "F000459")

    def test_resolve__missing_accents(self):
        """ Test resolve """
        text = "Cardenas, Tony"
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "C001097")

    def test_resolve__partial_firstname(self):
        """ Test resolve e.g. Michael to Mike """
        text = "Lee, Michael S."
        output = gpo_member_photos.resolve(self.yaml_data, text)
        self.assertEqual(output, "L000577")

if __name__ == '__main__':
    unittest.main()

# End of file
