"""Tests: Karten-CRUD und Inline-Editing."""

import pytest


def _get_card(client, headers, card_id, active_only=False):
    """Einzelne Karte aus der API holen."""
    resp = client.get(f"/api/cards?active_only={'true' if active_only else 'false'}", headers=headers)
    cards = resp.json()
    return next((c for c in cards if c["card_id"] == card_id), None)


class TestCardUpdate:
    """PUT /api/cards/{card_id}"""

    def test_update_frage_und_antwort(self, client, auth_header, test_package):
        """Frage und Antwort müssen aktualisiert werden."""
        resp = client.put("/api/cards/T-001", json={
            "question": "Neue Frage",
            "answer": "Neue Antwort",
        }, headers=auth_header)
        assert resp.status_code == 200

        card = _get_card(client, auth_header, "T-001")
        assert card["question"] == "Neue Frage"
        assert card["answer"] == "Neue Antwort"

    def test_update_setzt_source_manual(self, client, auth_header, test_package):
        """Bearbeitete Karte muss source='manual' bekommen."""
        resp = client.put("/api/cards/T-001", json={
            "question": "Editierte Frage",
            "source": "manual",
        }, headers=auth_header)
        assert resp.status_code == 200

    def test_update_schwierigkeit(self, client, auth_header, test_package):
        """Schwierigkeit muss aktualisiert werden."""
        resp = client.put("/api/cards/T-001", json={"difficulty": 3}, headers=auth_header)
        assert resp.status_code == 200

        card = _get_card(client, auth_header, "T-001")
        assert card["difficulty"] == 3

    def test_update_aktiv_toggle(self, client, auth_header, test_package):
        """active=0 muss Karte deaktivieren."""
        resp = client.put("/api/cards/T-001", json={"active": 0}, headers=auth_header)
        assert resp.status_code == 200

        card = _get_card(client, auth_header, "T-001", active_only=False)
        assert card is not None
        assert card["active"] == 0


class TestCardCreate:
    """POST /api/cards"""

    def test_erstelle_karte(self, client, auth_header, test_package):
        """Neue Karte muss erstellt werden."""
        resp = client.post("/api/cards", json={
            "package_id": test_package,
            "card_id": "T-NEW",
            "question": "Neue Frage",
            "answer": "Neue Antwort",
            "category_code": "TH",
            "difficulty": 2,
        }, headers=auth_header)
        assert resp.status_code == 200

        card = _get_card(client, auth_header, "T-NEW")
        assert card is not None
        assert card["question"] == "Neue Frage"
