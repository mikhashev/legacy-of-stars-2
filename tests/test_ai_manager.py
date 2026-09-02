"""
AIManager: never raises, never returns error strings, honours offline mode and timeouts.
"""
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src import ai_manager as ai_module  # noqa: E402
from src.ai_manager import AIManager, load_dotenv  # noqa: E402

URLOPEN = "src.ai_manager.urllib.request.urlopen"


class OfflineTest(unittest.TestCase):
    def test_offline_never_touches_network(self):
        manager = AIManager(offline=True)
        with mock.patch(URLOPEN) as urlopen:
            self.assertFalse(manager.is_available())
            self.assertIsNone(manager.generate_text("hello"))
            urlopen.assert_not_called()

    def test_env_offline_flag(self):
        with mock.patch.dict(os.environ, {"LOS_OFFLINE": "1"}):
            manager = AIManager(offline=False)
        self.assertTrue(manager.offline)
        self.assertIn("offline", manager.describe())


class ProbeAndFailureTest(unittest.TestCase):
    def _online_manager(self, **provider):
        with mock.patch.dict(os.environ, {"LOS_OFFLINE": "0"}):
            manager = AIManager(offline=False, probe=True, config_path=Path("does-not-exist.json"))
        manager.offline = False
        manager.current_provider = {"alias": "test", "type": "ollama", "host": "http://127.0.0.1:1", **provider}
        manager.provider_alias = "test"
        return manager

    def test_unreachable_provider_is_unavailable_and_returns_none(self):
        manager = self._online_manager()
        with mock.patch(URLOPEN, side_effect=urllib.error.URLError("refused")) as urlopen:
            self.assertFalse(manager.is_available())
            self.assertIsNone(manager.generate_text("hello"))
            # probe happened once; generate_text did not retry the network
            self.assertEqual(urlopen.call_count, 1)
        self.assertIn("refused", manager.last_error)

    def test_request_timeout_is_forwarded_and_failures_disable_llm(self):
        manager = self._online_manager()
        manager._available = True  # pretend the probe succeeded

        def failing_urlopen(request, timeout=None):
            self.assertEqual(timeout, 7.5)
            raise urllib.error.URLError("timed out")

        with mock.patch(URLOPEN, side_effect=failing_urlopen):
            self.assertIsNone(manager.generate_text("hello", timeout=7.5))
            self.assertTrue(manager.is_available())
            self.assertIsNone(manager.generate_text("hello", timeout=7.5))
        self.assertFalse(manager.is_available())  # switched off after repeated failures

    def test_successful_ollama_response(self):
        manager = self._online_manager()
        manager._available = True

        class FakeResponse:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self):
                return json.dumps({"response": "  Greetings, Earth.  "}).encode("utf-8")

        with mock.patch(URLOPEN, return_value=FakeResponse()):
            self.assertEqual(manager.generate_text("hello"), "Greetings, Earth.")
        self.assertEqual(manager.failures, 0)

    def test_anthropic_without_key_is_unavailable(self):
        manager = self._online_manager(type="anthropic", api_key_env="LOS_TEST_MISSING_KEY")
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LOS_TEST_MISSING_KEY", None)
            self.assertFalse(manager.is_available())
        self.assertIn("key", manager.last_error.lower())


class ConfigTest(unittest.TestCase):
    def test_config_path_is_project_relative(self):
        self.assertEqual(ai_module.CONFIG_PATH, ROOT / "data" / "llm_providers.json")
        config = AIManager.load_config()
        aliases = {p["alias"] for p in config["providers"]}
        self.assertIn(config["default_provider"], aliases)
        self.assertIn("openai_gpt", aliases)

    def test_provider_override_via_env(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER": "claude_haiku", "LOS_OFFLINE": "1"}):
            manager = AIManager()
        self.assertEqual(manager.provider_alias, "claude_haiku")
        self.assertEqual(manager.current_provider["type"], "anthropic")

    def test_unknown_alias_gives_no_provider(self):
        manager = AIManager(offline=True, provider_alias="nope")
        self.assertIsNone(manager.current_provider)
        self.assertFalse(manager.is_available())


class DotenvTest(unittest.TestCase):
    def test_parser_and_no_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# comment\n"
                "LOS_TEST_A=alpha\n"
                "export LOS_TEST_B='beta value'\n"
                'LOS_TEST_C="gamma=delta"\n'
                "LOS_TEST_EXISTING=from_file\n"
                "not a valid line\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"LOS_TEST_EXISTING": "from_env"}, clear=False):
                for key in ("LOS_TEST_A", "LOS_TEST_B", "LOS_TEST_C"):
                    os.environ.pop(key, None)
                loaded = load_dotenv(env_file)
                self.assertEqual(os.environ["LOS_TEST_A"], "alpha")
                self.assertEqual(os.environ["LOS_TEST_B"], "beta value")
                self.assertEqual(os.environ["LOS_TEST_C"], "gamma=delta")
                self.assertEqual(os.environ["LOS_TEST_EXISTING"], "from_env")
                self.assertEqual(loaded["LOS_TEST_EXISTING"], "from_file")

    def test_missing_file_is_fine(self):
        self.assertEqual(load_dotenv(Path("definitely-missing.env")), {})


if __name__ == "__main__":
    unittest.main()
