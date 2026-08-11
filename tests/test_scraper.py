"""Tests offline pour Scraping-Deputes-France.

Fixtures HTML capturées depuis le vrai site (août 2026) :
- tests/fixtures/liste_regions.html  — page liste complète des députés par région
- tests/fixtures/depute_breton.html  — fiche dyn de Xavier Breton (cas des deux
  mailto : adresse officielle @assemblee-nationale.fr + contact perso)

Aucun accès réseau : get_with_retries est mocké quand nécessaire.
"""
import csv
import importlib.util
import io
import json
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load():
    spec = importlib.util.spec_from_file_location(
        "scraper", ROOT / "Scraping-Deputes-France.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def scraper():
    return _load()


@pytest.fixture(scope="session")
def liste_soup():
    return BeautifulSoup(
        (FIXTURES / "liste_regions.html").read_text(encoding="utf-8"),
        "html.parser")


# ── normalize_region ─────────────────────────────────────────────────────────

def test_normalize_region_valid(scraper):
    assert scraper.normalize_region("Corse") == "Corse"
    assert scraper.normalize_region("  corse  ") == "Corse"      # casse + espaces
    assert scraper.normalize_region("MAYOTTE") == "Mayotte"


def test_normalize_region_invalid(scraper):
    assert scraper.normalize_region("Atlantide") is None
    assert scraper.normalize_region("") is None


def test_valid_regions_complete(scraper, liste_soup):
    """Les 24 <h2> du site doivent tous être dans VALID_REGIONS (et réciproque)."""
    site_h2 = {h.get_text(strip=True) for h in liste_soup.find_all("h2")}
    assert set(scraper.VALID_REGIONS) == site_h2
    assert len(scraper.VALID_REGIONS) == 24


# ── parse_deputes_from_region ────────────────────────────────────────────────

def test_parse_region_returns_tuples_with_departement(scraper, liste_soup):
    deps = scraper.parse_deputes_from_region(liste_soup, "Corse")
    assert len(deps) == 4
    names = [d[0] for d in deps]
    assert any("Castellani" in n for n in names)
    # tuples (nom, url, departement) — les deux départements corses présents
    depts = {d[2] for d in deps}
    assert depts == {"Corse-du-Sud", "Haute-Corse"}
    # URLs complètes et au bon format
    assert all(d[1].startswith(scraper.BASE_URL + "/deputes/fiche/") for d in deps)


def test_parse_region_homonymes_preserved(scraper, liste_soup):
    """La structure liste (et non dict) ne doit écraser aucun député."""
    total = 0
    for region in scraper.VALID_REGIONS:
        total += len(scraper.parse_deputes_from_region(liste_soup, region))
    assert total >= 570   # 577 députés à la capture des fixtures


def test_parse_region_unknown_warns(scraper, liste_soup, capsys):
    deps = scraper.parse_deputes_from_region(liste_soup, "Région Inexistante")
    assert deps == []
    assert "structure" in capsys.readouterr().err.lower()


# ── get_depute_info (réseau mocké sur la fixture Breton) ─────────────────────

class _FakeResp:
    def __init__(self, text):
        self.text = text


def test_depute_info_prefers_official_email(scraper, monkeypatch):
    """La fiche Breton contient deux mailto : l'officiel doit gagner."""
    html = (FIXTURES / "depute_breton.html").read_text(encoding="utf-8")
    monkeypatch.setattr(
        scraper, "get_with_retries",
        lambda *a, **k: _FakeResp(html))
    info = scraper.get_depute_info(
        "M. Xavier Breton",
        "https://www.assemblee-nationale.fr/deputes/fiche/OMC_PA330008",
        "Auvergne-Rhône-Alpes", "Ain (01)",
        3, 0.0, 10.0, False)
    assert info["email"] == "Xavier.Breton@assemblee-nationale.fr"
    assert info["email"] != "contact@xavierbreton.fr"
    assert info["departement"] == "Ain (01)"
    assert info["groupe"]
    assert info["circonscription"]


def test_depute_info_fetch_failure_returns_nones(scraper, monkeypatch):
    monkeypatch.setattr(scraper, "get_with_retries", lambda *a, **k: None)
    info = scraper.get_depute_info(
        "X", "https://www.assemblee-nationale.fr/deputes/fiche/OMC_PA000000",
        "Corse", "Corse-du-Sud", 3, 0.0, 10.0, False)
    assert info == {"nom": "X", "region": "Corse", "departement": "Corse-du-Sud",
                    "email": None, "groupe": None, "circonscription": None}


def test_depute_info_bad_url_returns_nones(scraper):
    info = scraper.get_depute_info(
        "X", "https://example.com/no-id-here", "Corse", None,
        3, 0.0, 10.0, False)
    assert info["email"] is None and info["groupe"] is None


# ── build_ascii_table ────────────────────────────────────────────────────────

def test_ascii_table(scraper):
    rows = [{"nom": "A", "email": "a@x.fr"}, {"nom": "BB", "email": "bb@x.fr"}]
    table = scraper.build_ascii_table(rows, ["nom", "email"])
    lines = table.splitlines()
    assert lines[0].startswith("Nom")
    assert "-+-" in lines[1]
    assert len(lines) == 4   # header + séparateur + 2 lignes de données


def test_ascii_table_empty(scraper):
    assert "Aucune donnée" in scraper.build_ascii_table([], ["nom"])


# ── session / UA ─────────────────────────────────────────────────────────────

def test_session_has_browser_ua(scraper):
    s = scraper.get_session()
    assert "Mozilla" in s.headers["User-Agent"]
    assert scraper.get_session() is s   # réutilisation (connexions poolées)


# ── CLI offline (validations avant tout accès réseau) ────────────────────────

def _run_cli(scraper, *argv):
    import subprocess
    import sys
    return subprocess.run(
        [sys.executable, str(ROOT / "Scraping-Deputes-France.py"), *argv],
        capture_output=True, text=True, timeout=30)


def test_cli_invalid_region_exit_1(scraper):
    r = _run_cli(scraper, "--region", "Atlantide")
    assert r.returncode == 1
    assert "invalides" in r.stderr


def test_cli_invalid_field_exit_1(scraper):
    r = _run_cli(scraper, "--region", "Corse", "--fields", "nom,emial")
    assert r.returncode == 1
    assert "emial" in r.stderr


def test_cli_list_regions_exit_0(scraper):
    r = _run_cli(scraper, "--list-regions")
    assert r.returncode == 0
    assert "Mayotte" in r.stdout and "Français établis hors de France" in r.stdout
