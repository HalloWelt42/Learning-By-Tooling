"""Tests: Lernfortschritt zurücksetzen -- alles muss weg."""

import pytest


def _create_session(client, headers, pkg_id):
    """Session starten und ein paar Karten beantworten."""
    resp = client.post("/api/sessions", json={
        "package_id": pkg_id,
        "mode": "standard",
        "card_limit": 3,
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    sid = resp.json()["session_id"]

    # Erste Karte holen
    resp = client.get(f"/api/sessions/{sid}/current-card", headers=headers)
    assert resp.status_code == 200

    # 3 Karten beantworten
    for _ in range(3):
        resp = client.post(f"/api/sessions/{sid}/review-and-next", json={
            "result": "correct",
            "time_ms": 5000,
        }, headers=headers)
        if resp.json().get("done"):
            break

    return sid


class TestResetMyStats:
    """POST /api/reset/my-stats"""

    def test_reset_loescht_card_stats(self, client, auth_header, test_package):
        """card_stats muss nach Reset leer sein."""
        _create_session(client, auth_header, test_package)

        # Prüfe: card_stats hat Einträge
        import db as db_mod
        conn = db_mod.get_db()
        before = conn.execute("SELECT COUNT(*) as c FROM card_stats").fetchone()["c"]
        conn.close()
        assert before > 0, "Voraussetzung: card_stats muss Einträge haben"

        # Reset
        resp = client.post("/api/reset/my-stats", json={"package_id": test_package}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        after = conn.execute("SELECT COUNT(*) as c FROM card_stats").fetchone()["c"]
        conn.close()
        assert after == 0, "card_stats muss nach Reset leer sein"

    def test_reset_loescht_reviews(self, client, auth_header, test_package):
        """reviews muss nach Reset leer sein."""
        _create_session(client, auth_header, test_package)

        import db as db_mod
        conn = db_mod.get_db()
        before = conn.execute("SELECT COUNT(*) as c FROM reviews").fetchone()["c"]
        conn.close()
        assert before > 0, "Voraussetzung: reviews muss Einträge haben"

        resp = client.post("/api/reset/my-stats", json={"package_id": test_package}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        after = conn.execute("SELECT COUNT(*) as c FROM reviews").fetchone()["c"]
        conn.close()
        assert after == 0, "reviews muss nach Reset leer sein"

    def test_reset_loescht_sessions(self, client, auth_header, test_package):
        """sessions muss nach Reset leer sein."""
        _create_session(client, auth_header, test_package)

        import db as db_mod
        conn = db_mod.get_db()
        before = conn.execute("SELECT COUNT(*) as c FROM sessions WHERE package_id=?", (test_package,)).fetchone()["c"]
        conn.close()
        assert before > 0, "Voraussetzung: sessions muss Einträge haben"

        resp = client.post("/api/reset/my-stats", json={"package_id": test_package}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        after = conn.execute("SELECT COUNT(*) as c FROM sessions WHERE package_id=?", (test_package,)).fetchone()["c"]
        conn.close()
        assert after == 0, "sessions muss nach Reset leer sein"

    def test_reset_loescht_card_reports(self, client, auth_header, test_package):
        """card_reports muss nach Paket-Reset leer sein."""
        # Karte melden
        resp = client.post("/api/cards/T-001/report", json={"reason": "Falsche Antwort"}, headers=auth_header)
        assert resp.status_code == 200

        import db as db_mod
        conn = db_mod.get_db()
        before = conn.execute("SELECT COUNT(*) as c FROM card_reports").fetchone()["c"]
        conn.close()
        assert before > 0, "Voraussetzung: card_reports muss Einträge haben"

        resp = client.post("/api/reset/my-stats", json={"package_id": test_package}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        after = conn.execute("SELECT COUNT(*) as c FROM card_reports").fetchone()["c"]
        conn.close()
        assert after == 0, "card_reports muss nach Reset leer sein"

    def test_reset_reaktiviert_gemeldete_karten(self, client, auth_header, test_package):
        """Gemeldete Karten müssen nach Reset wieder active=1 und reported=0 sein."""
        client.post("/api/cards/T-001/report", json={"reason": "Test"}, headers=auth_header)
        client.post("/api/cards/T-002/report", json={"reason": "Test"}, headers=auth_header)

        import db as db_mod
        conn = db_mod.get_db()
        reported = conn.execute("SELECT COUNT(*) as c FROM cards WHERE reported=1").fetchone()["c"]
        conn.close()
        assert reported == 2

        resp = client.post("/api/reset/my-stats", json={"package_id": test_package}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        reported_after = conn.execute("SELECT COUNT(*) as c FROM cards WHERE reported=1").fetchone()["c"]
        inactive_after = conn.execute("SELECT COUNT(*) as c FROM cards WHERE active=0 AND package_id=?", (test_package,)).fetchone()["c"]
        conn.close()
        assert reported_after == 0, "reported muss nach Reset 0 sein"
        assert inactive_after == 0, "alle Karten müssen nach Reset aktiv sein"

    def test_reset_alles_loescht_xp(self, client, auth_header, test_package):
        """Globaler Reset muss auch user_xp löschen."""
        _create_session(client, auth_header, test_package)

        # User-ID aus /api/auth/me holen
        me = client.get("/api/auth/me", headers=auth_header).json()
        uid = me["id"]

        import db as db_mod
        conn = db_mod.get_db()
        conn.execute("INSERT OR REPLACE INTO user_xp (user_id, xp_total, xp_today) VALUES (?, 100, 50)", (uid,))
        conn.commit()
        conn.close()

        # Globaler Reset (kein package_id)
        resp = client.post("/api/reset/my-stats", json={}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        xp = conn.execute("SELECT * FROM user_xp WHERE user_id=?", (uid,)).fetchone()
        conn.close()
        assert xp is None, "user_xp muss nach globalem Reset gelöscht sein"


class TestResetVollstaendigkeit:
    """Prüft dass ALLE relevanten Tabellen bei Reset berücksichtigt werden."""

    RESET_TABLES = ["card_stats", "reviews", "sessions", "card_reports", "user_xp"]

    def test_alle_tabellen_werden_geleert(self, client, auth_header, test_package):
        """Globaler Reset muss alle lernrelevanten Tabellen leeren."""
        _create_session(client, auth_header, test_package)

        me = client.get("/api/auth/me", headers=auth_header).json()
        uid = me["id"]

        # Report erstellen
        client.post("/api/cards/T-001/report", json={"reason": "Test"}, headers=auth_header)

        import db as db_mod
        conn = db_mod.get_db()
        conn.execute("INSERT OR REPLACE INTO user_xp (user_id, xp_total, xp_today) VALUES (?, 100, 50)", (uid,))
        conn.commit()
        conn.close()

        # Globaler Reset
        resp = client.post("/api/reset/my-stats", json={}, headers=auth_header)
        assert resp.status_code == 200

        conn = db_mod.get_db()
        for table in self.RESET_TABLES:
            count = conn.execute(f"SELECT COUNT(*) as c FROM {table} WHERE user_id=?", (uid,)).fetchone()["c"]
            assert count == 0, f"Tabelle {table} muss nach globalem Reset leer sein (hat {count} Einträge)"
        conn.close()
