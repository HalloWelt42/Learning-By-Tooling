"""Tests: KI-Templates CRUD und Provider-Endpoints."""

import pytest


class TestListTemplates:
    """GET /api/ai/templates"""

    def test_liefert_7_default_templates(self, client, auth_header):
        """Seed muss 7 Templates erstellen."""
        resp = client.get("/api/ai/templates", headers=auth_header)
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) == 7
        slugs = {t["slug"] for t in templates}
        assert slugs == {
            "explain_card", "evaluate_answer", "generate_card",
            "generate_mc", "generate_hint", "summarize_topic",
            "analyze_mistakes"
        }

    def test_templates_haben_pflichtfelder(self, client, auth_header):
        """Jedes Template muss alle Pflichtfelder haben."""
        resp = client.get("/api/ai/templates", headers=auth_header)
        for t in resp.json():
            assert t["slug"], f"slug fehlt bei {t}"
            assert t["display_name"], f"display_name fehlt bei {t['slug']}"
            assert t["system_prompt"], f"system_prompt fehlt bei {t['slug']}"
            assert t["user_prompt"], f"user_prompt fehlt bei {t['slug']}"
            assert t["temperature"] > 0, f"temperature ungültig bei {t['slug']}"
            assert t["max_tokens"] > 0, f"max_tokens ungültig bei {t['slug']}"


class TestGetTemplate:
    """GET /api/ai/templates/{slug}"""

    def test_einzelnes_template(self, client, auth_header):
        resp = client.get("/api/ai/templates/explain_card", headers=auth_header)
        assert resp.status_code == 200
        t = resp.json()
        assert t["slug"] == "explain_card"
        assert "{question}" in t["user_prompt"]

    def test_unbekanntes_template_404(self, client, auth_header):
        resp = client.get("/api/ai/templates/gibts_nicht", headers=auth_header)
        assert resp.status_code == 404


class TestUpdateTemplate:
    """PATCH /api/ai/templates/{slug}"""

    def test_system_prompt_aendern(self, client, auth_header):
        """System-Prompt muss aktualisiert werden."""
        resp = client.patch("/api/ai/templates/explain_card", json={
            "system_prompt": "Neuer System-Prompt für Tests"
        }, headers=auth_header)
        assert resp.status_code == 200

        resp = client.get("/api/ai/templates/explain_card", headers=auth_header)
        assert resp.json()["system_prompt"] == "Neuer System-Prompt für Tests"

    def test_temperature_aendern(self, client, auth_header):
        resp = client.patch("/api/ai/templates/evaluate_answer", json={
            "temperature": 0.7
        }, headers=auth_header)
        assert resp.status_code == 200

        resp = client.get("/api/ai/templates/evaluate_answer", headers=auth_header)
        assert resp.json()["temperature"] == 0.7

    def test_unerlaubte_felder_ignoriert(self, client, auth_header):
        """slug und id dürfen nicht geändert werden."""
        resp = client.patch("/api/ai/templates/explain_card", json={
            "slug": "hacked",
            "id": 999,
            "temperature": 0.5,
        }, headers=auth_header)
        assert resp.status_code == 200

        resp = client.get("/api/ai/templates/explain_card", headers=auth_header)
        t = resp.json()
        assert t["slug"] == "explain_card"
        assert t["temperature"] == 0.5


class TestResetTemplate:
    """POST /api/ai/templates/{slug}/reset"""

    def test_reset_stellt_default_wieder_her(self, client, auth_header):
        """Nach Änderung und Reset muss der Original-Prompt zurück sein."""
        # Original merken
        resp = client.get("/api/ai/templates/explain_card", headers=auth_header)
        original_prompt = resp.json()["system_prompt"]

        # Ändern
        client.patch("/api/ai/templates/explain_card", json={
            "system_prompt": "Komplett geändert"
        }, headers=auth_header)

        # Reset
        resp = client.post("/api/ai/templates/explain_card/reset", headers=auth_header)
        assert resp.status_code == 200

        # Prüfen
        resp = client.get("/api/ai/templates/explain_card", headers=auth_header)
        assert resp.json()["system_prompt"] == original_prompt


class TestProviders:
    """GET /api/ai/providers"""

    def test_listet_provider(self, client, auth_header):
        resp = client.get("/api/ai/providers", headers=auth_header)
        assert resp.status_code == 200
        providers = resp.json()
        names = [p["name"] for p in providers]
        assert "lmstudio" in names
        assert "ollama" in names
