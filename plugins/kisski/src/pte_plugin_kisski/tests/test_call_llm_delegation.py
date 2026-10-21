"""
Unit test confirming KisskiExtractor._call_llm delegates to the shared
chat_completion_sync function, rather than duplicating the HTTP call.

@testCovers plugins/kisski/src/pte_plugin_kisski/extractor.py:_call_llm
"""

import unittest
from unittest.mock import patch

from pte_plugin_kisski.extractor import KisskiExtractor


class TestCallLlmDelegation(unittest.TestCase):
    def test_call_llm_delegates_to_shared_chat_completion_sync(self):
        extractor = KisskiExtractor()
        extractor.client = "test-api-key"

        with patch(
            "pte_plugin_kisski.extractor.chat_completion_sync",
            return_value="delegated response",
        ) as mock_fn, patch(
            "pte_plugin_kisski.extractor.get_config"
        ) as mock_get_config:
            mock_get_config.return_value.get.return_value = "https://chat-ai.academiccloud.de/v1"

            result = extractor._call_llm(
                system_prompt="sys", user_prompt="usr", model="test-model", temperature=0.7
            )

        self.assertEqual(result, "delegated response")
        mock_fn.assert_called_once_with(
            base_url="https://chat-ai.academiccloud.de/v1",
            api_key="test-api-key",
            model_id="test-model",
            system_prompt="sys",
            user_prompt="usr",
            temperature=0.7,
        )

    def test_call_llm_raises_without_model(self):
        extractor = KisskiExtractor()
        extractor.client = "test-api-key"
        with self.assertRaises(RuntimeError):
            extractor._call_llm(system_prompt="sys", user_prompt="usr", model=None)


if __name__ == "__main__":
    unittest.main()
