import unittest
from datetime import datetime, timedelta

from cachesade.app import CacheSadeApp


class ReminderTests(unittest.TestCase):
    def test_monthly_reminder_is_due_after_thirty_days(self):
        old_scan = (datetime.now() - timedelta(days=31)).isoformat(timespec="seconds")
        self.assertTrue(CacheSadeApp._is_reminder_due(old_scan))

    def test_monthly_reminder_is_not_due_for_recent_scan(self):
        recent_scan = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
        self.assertFalse(CacheSadeApp._is_reminder_due(recent_scan))


if __name__ == "__main__":
    unittest.main()
