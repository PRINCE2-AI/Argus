import os
import unittest
from unittest import mock

from argus import i18n


class I18nTests(unittest.TestCase):
    def test_all_languages_have_the_same_keys(self):
        base = set(i18n.TRANSLATIONS["en"])
        for code, translations in i18n.TRANSLATIONS.items():
            self.assertEqual(set(translations), base, code)
        self.assertEqual(set(i18n.LANGUAGES), set(i18n.TRANSLATIONS))

    def test_translation_formats_values(self):
        self.assertEqual(
            i18n.t("mode_set", lang="en", mode="safe"), "Safety mode: safe"
        )
        self.assertEqual(
            i18n.t("mode_set", lang="es", mode="safe"), "Modo de seguridad: safe"
        )
        self.assertEqual(
            i18n.t("mode_set", lang="fr", mode="safe"), "Mode de sécurité : safe"
        )
        self.assertIn("सुरक्षा मोड", i18n.t("mode_set", lang="hi", mode="safe"))

    def test_unknown_key_falls_back_to_itself(self):
        self.assertEqual(i18n.t("no_such_key", lang="en"), "no_such_key")

    def test_unknown_language_falls_back_to_english(self):
        self.assertEqual(i18n.t("bye", lang="de"), "Bye.")
        self.assertEqual(i18n.t("bye", lang="nonsense"), "Bye.")

    def test_bad_format_values_do_not_raise(self):
        self.assertEqual(i18n.t("session_loaded", lang="en"), "Resumed session: {path}")

    def test_resolve_lang_prefers_explicit_value(self):
        self.assertEqual(i18n.resolve_lang("fr"), "fr")
        self.assertEqual(i18n.resolve_lang("xx"), "en")

    def test_resolve_lang_reads_environment_and_locale(self):
        with mock.patch.dict(
            os.environ, {"ARGUS_LANG": "hi", "LANG": "fr_FR.UTF-8"}, clear=True
        ):
            self.assertEqual(i18n.resolve_lang(), "hi")
        with mock.patch.dict(
            os.environ, {"LANG": "fr_FR.UTF-8"}, clear=True
        ):
            self.assertEqual(i18n.resolve_lang(), "fr")
        with mock.patch.dict(os.environ, {"LC_ALL": "es_ES.UTF-8"}, clear=True):
            self.assertEqual(i18n.resolve_lang(), "es")
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(i18n.resolve_lang(), "en")

    def test_available_languages_is_a_copy(self):
        languages = i18n.available_languages()
        languages["xx"] = "Test"
        self.assertNotIn("xx", i18n.LANGUAGES)


if __name__ == "__main__":
    unittest.main()
