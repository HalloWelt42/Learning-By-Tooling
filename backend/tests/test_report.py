"""Tests: Karten als fehlerhaft melden und reaktivieren."""

import pytest


class TestReportCard:
    """POST /api/cards/{card_id}/report"""

    def test_report_deaktiviert_karte(self, client, auth_header, test_package):
        """Gemeldete Karte muss active=0 und reported=1 sein."""
        resp = client.post("/api/cards/T-001/report", json={"reason": "Falsche Antwort"}, headers=auth_header)
        assert resp.status_code == 200

        import db as db_mod
        conn = db_mod.get_db()
        card = conn.execute("SELECT active, reported FROM cards WHERE card_id='T-001'").fetchone()
        conn.close()
        assert card["active"] == 0, "Karte muss deaktiviert sein"
        assert card["reported"] == 1, "Karte muss als reported markiert sein"

    def test_report_erstellt_eintrag(self, client, auth_header, test_package):
        """card_reports muss einen Eintrag mit Grund haben."""
        client.post("/api/cards/T-001/report", json={"reason": "Tippfehler in Antwort"}, headers=auth_header)

        import db as db_mod
        conn = db_mod.get_db()
        reports = conn.execute("SELECT * FROM card_reports WHERE card_id='T-001'").fetchall()
        conn.close()
        assert len(reports) == 1
        assert reports[0]["reason"] == "Tippfehler in Antwort"
        assert reports[0]["status"] == "open"

    def test_report_ohne_grund(self, client, auth_header, test_package):
        """Report ohne Grund muss auch funktionieren."""
        resp = client.post("/api/cards/T-002/report", json={}, headers=auth_header)
        assert resp.status_code == 200

    def test_report_unbekannte_karte(self, client, auth_header, test_package):
        """Report auf nicht existierende Karte muss 404 geben."""
        resp = client.post("/api/cards/GIBTS-NICHT/report", json={"reason": "test"}, headers=auth_header)
        assert resp.status_code == 404


class TestUnreportCard:
    """POST /api/cards/{card_id}/unreport"""

    def test_unreport_reaktiviert_karte(self, client, auth_header, test_package):
        """Unreport muss Karte wieder active=1 und reported=0 setzen."""
        client.post("/api/cards/T-001/report", json={"reason": "Test"}, headers=auth_header)
        resp = client.post("/api/cards/T-001/unreport", headers=auth_header)
        assert resp.status_code == 200

        import db as db_mod
        conn = db_mod.get_db()
        card = conn.execute("SELECT active, reported FROM cards WHERE card_id='T-001'").fetchone()
        conn.close()
        assert card["active"] == 1, "Karte muss wieder aktiv sein"
        assert card["reported"] == 0, "reported muss wieder 0 sein"

    def test_unreport_schliesst_reports(self, client, auth_header, test_package):
        """Unreport muss offene Reports auf 'resolved' setzen."""
        client.post("/api/cards/T-001/report", json={"reason": "Test"}, headers=auth_header)
        client.post("/api/cards/T-001/unreport", headers=auth_header)

        import db as db_mod
        conn = db_mod.get_db()
        open_reports = conn.execute(
            "SELECT COUNT(*) as c FROM card_reports WHERE card_id='T-001' AND status='open'"
        ).fetchone()["c"]
        resolved = conn.execute(
            "SELECT COUNT(*) as c FROM card_reports WHERE card_id='T-001' AND status='resolved'"
        ).fetchone()["c"]
        conn.close()
        assert open_reports == 0, "Keine offenen Reports mehr"
        assert resolved == 1, "Report muss auf resolved stehen"


class TestGetReports:
    """GET /api/cards/{card_id}/reports"""

    def test_reports_leer(self, client, auth_header, test_package):
        """Karte ohne Reports gibt leere Liste."""
        resp = client.get("/api/cards/T-001/reports", headers=auth_header)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_reports_nach_meldung(self, client, auth_header, test_package):
        """Nach Meldung muss Report mit Usernamen zurückkommen."""
        client.post("/api/cards/T-001/report", json={"reason": "Fehler"}, headers=auth_header)
        resp = client.get("/api/cards/T-001/reports", headers=auth_header)
        assert resp.status_code == 200
        reports = resp.json()
        assert len(reports) == 1
        assert reports[0]["reason"] == "Fehler"
        assert reports[0]["display_name"] is not None
