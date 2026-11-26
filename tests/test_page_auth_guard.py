"""Tests for direct multipage authentication enforcement."""
import unittest
from unittest.mock import patch

from enterprise_core.streamlit_auth import require_page_enterprise_access


class StopRequested(Exception):
    pass


class FakeStreamlit:
    def __init__(self):
        self.messages = []

    def warning(self, message):
        self.messages.append(("warning", message))

    def error(self, message):
        self.messages.append(("error", message))

    def stop(self):
        raise StopRequested()


class PageAuthGuardTests(unittest.TestCase):
    def test_disabled_enterprise_mode_is_explicitly_prototype_only(self):
        st = FakeStreamlit()
        with patch.dict("os.environ", {"FRAUDSHIELD_ENTERPRISE_AUTH_ENABLED": "false"}):
            result = require_page_enterprise_access(st)
        self.assertIsNone(result)
        self.assertTrue(any(level == "warning" for level, _ in st.messages))

    def test_enabled_mode_fails_closed_when_database_is_unavailable(self):
        st = FakeStreamlit()
        with patch.dict("os.environ", {"FRAUDSHIELD_ENTERPRISE_AUTH_ENABLED": "true"}):
            with patch("enterprise_core.database.make_engine", side_effect=RuntimeError("db unavailable")):
                with self.assertRaises(StopRequested):
                    require_page_enterprise_access(st)
        self.assertTrue(any(level == "error" for level, _ in st.messages))


if __name__ == "__main__":
    unittest.main()
