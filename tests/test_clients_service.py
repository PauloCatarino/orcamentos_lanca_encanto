import unittest

from Martelo_Orcamentos_V2.app.services.clients import (
    phc_simplex_has_unjoined_words,
    phc_simplex_is_missing,
    phc_simplex_validation_issue,
)


class ClientServiceSimplexTests(unittest.TestCase):
    def test_phc_simplex_is_missing_handles_empty_and_placeholder(self):
        self.assertTrue(phc_simplex_is_missing(""))
        self.assertTrue(phc_simplex_is_missing("CLIENTE..."))
        self.assertFalse(phc_simplex_is_missing("CLIENTE_A"))

    def test_phc_simplex_has_unjoined_words_detects_spaces(self):
        self.assertTrue(phc_simplex_has_unjoined_words("CLIENTE CASAIS"))
        self.assertTrue(phc_simplex_has_unjoined_words("CLIENTE_CASAIS FILHO"))
        self.assertFalse(phc_simplex_has_unjoined_words("CLIENTE_CASAIS"))

    def test_phc_simplex_validation_issue_reports_missing_abreviatura(self):
        issue = phc_simplex_validation_issue(
            cliente_nome="Cliente A",
            num_phc="123",
            simplex="CLIENTE...",
            action_label="criar o processo",
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue[0], "Abreviado (PHC) em falta")
        self.assertIn("Atualizar PHC", issue[1])

    def test_phc_simplex_validation_issue_reports_spaces_without_underscores(self):
        issue = phc_simplex_validation_issue(
            cliente_nome="Cliente A",
            num_phc="123",
            simplex="CLIENTE CASAIS",
            action_label="criar o processo",
        )

        self.assertIsNotNone(issue)
        self.assertEqual(issue[0], "Abreviado (PHC) invalido")
        self.assertIn("ALEXANDRE_CASAIS", issue[1])


if __name__ == "__main__":
    unittest.main()
