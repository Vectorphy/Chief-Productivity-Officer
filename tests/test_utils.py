import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import ProductivityService, parse_duration, parse_seconds_to_hms


class TestUtils(unittest.TestCase):
    def test_parse_duration(self):
        self.assertEqual(parse_duration("30s"), 30)
        self.assertEqual(parse_duration("15m"), 900)
        self.assertEqual(parse_duration("2h"), 7200)
        self.assertEqual(parse_duration("1d"), 86400)
        self.assertEqual(parse_duration("45 mins"), 2700)
        self.assertEqual(parse_duration("3 hours"), 10800)
        self.assertIsNone(parse_duration("invalid_string"))

    def test_parse_seconds_to_hms(self):
        self.assertEqual(parse_seconds_to_hms(45), "45s")
        self.assertEqual(parse_seconds_to_hms(125), "2m 5s")
        self.assertEqual(parse_seconds_to_hms(3665), "1h 1m 5s")
        self.assertEqual(parse_seconds_to_hms(7200), "2h")

    def test_productivity_efficiency_calculation(self):
        service = ProductivityService(db_handler=None)
        self.assertEqual(service.calculate_efficiency(10, 2), 5.0)
        self.assertEqual(service.calculate_efficiency(0, 5), 0.0)
        self.assertEqual(service.calculate_efficiency(10, 0), 0.0)
        self.assertEqual(service.calculate_efficiency(7, 3), 2.33)

if __name__ == '__main__':
    unittest.main()
