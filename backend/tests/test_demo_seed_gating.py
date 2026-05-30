from unittest.mock import patch

from backend.db import seed


def test_skips_when_disabled():
    with patch.object(seed.settings, "seed_demo_data", False), \
         patch.object(seed, "get_connection") as conn:
        seed.run_demo_seed()
        conn.assert_not_called()


def test_skips_when_no_database_url():
    with patch.object(seed.settings, "seed_demo_data", True), \
         patch.object(seed.settings, "database_url", ""), \
         patch.object(seed, "get_connection") as conn:
        seed.run_demo_seed()
        conn.assert_not_called()
