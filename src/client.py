"""Totomondiale HTTP client: login, fetch, submit all bet types."""
import os
import re
import requests
from src.models import MATCHES, TEAMS, PLAYERS, TEAM_BY_ID, PLAYER_BY_ID, QUALIFICATION_REQUIRED

BASE_URL = "https://totomondiale.altervista.org"
SESSION = requests.Session()
_logged_in = False
TIMEOUT = 30


# ─── Auth & session utilities ────────────────────────────────────

def _get_csrf_token(html: str) -> str:
    m = re.search(r'csrf_token["\']\s+value="([^"]*)"', html)
    return m.group(1) if m else ""


def _get_fresh_csrf() -> str:
    r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?group=A&edit=1", timeout=TIMEOUT)
    return _get_csrf_token(r.text)


def login(email: str, password: str) -> dict:
    global _logged_in
    SESSION.cookies.clear()
    _logged_in = False
    r = SESSION.get(f"{BASE_URL}/index_scommesse.php", allow_redirects=True, timeout=TIMEOUT)
    csrf = _get_csrf_token(r.text)
    if not csrf:
        return {"success": False, "error": "Could not get CSRF token"}
    r = SESSION.post(
        f"{BASE_URL}/processaAccesso.php",
        data={"csrf_token": csrf, "email": email, "password": password, "login": "1"},
        allow_redirects=True,
        timeout=TIMEOUT,
    )
    if "wizard_scommesse.php" in r.url or "logout-btn" in r.text or "Benvenuto" in r.text:
        _logged_in = True
        return {"success": True, "message": "Login OK"}
    return {"success": False, "error": "Login failed — check credentials"}


def ensure_auth() -> dict:
    global _logged_in
    if _logged_in:
        return {"success": True}
    email = os.environ.get("TOTOMONDIALE_EMAIL")
    password = os.environ.get("TOTOMONDIALE_PASSWORD")
    if not email or not password:
        return {
            "success": False,
            "error": "Not logged in. Set TOTOMONDIALE_EMAIL and TOTOMONDIALE_PASSWORD env vars.",
        }
    return login(email, password)


def _post(data: dict) -> dict:
    """Submit form data to processaWizard.php. Returns {success, message|error}."""
    auth = ensure_auth()
    if not auth["success"]:
        return auth
    csrf = _get_fresh_csrf()
    data["csrf_token"] = csrf
    data["redirect"] = "scommesse"
    r = SESSION.post(f"{BASE_URL}/processaWizard.php", data=data, allow_redirects=True, timeout=TIMEOUT)

    text_lower = r.text.lower()
    if r.status_code >= 400:
        return {"success": False, "error": f"HTTP {r.status_code}"}
    if "index_accesso.php" in r.url and "Benvenuto" not in r.text:
        return {"success": False, "error": "Session expired — re-login required"}
    if "successo" in text_lower or "salvat" in text_lower:
        return {"success": True, "message": "Saved"}
    if "scommesse" in r.url:
        return {"success": True, "message": "Saved"}
    snippet = r.text[:200].replace("\n", " ")
    return {
        "success": False,
        "error": f"Unexpected response (status {r.status_code}, url={r.url}, text={snippet})",
    }


# ─── Submit functions ────────────────────────────────────────────

def submit_group_bets(group: str, scores: list[str], prolific_index: int) -> dict:
    group = group.upper()
    if group not in MATCHES:
        return {"success": False, "error": f"Invalid group: {group}"}
    match_ids = MATCHES[group]
    if len(scores) != 6:
        return {"success": False, "error": "Need exactly 6 scores"}
    data = {"action": "group_bets", "group": group}
    for i, mid in enumerate(match_ids):
        parts = scores[i].split("-")
        if len(parts) != 2:
            return {
                "success": False,
                "error": f"Invalid score format: '{scores[i]}'. Expected 'H-A' (e.g. '2-1')",
            }
        data[f"gCasa[{mid}]"] = parts[0].strip()
        data[f"gOspite[{mid}]"] = parts[1].strip()
    data["prolific_id"] = str(match_ids[prolific_index])
    return _post(data)


def submit_prolific_total(group: str, match_index: int) -> dict:
    match_id = MATCHES[group][match_index]
    data = {"action": "prolifica_totale", "prolific_id": str(match_id)}
    return _post(data)


def submit_qualification(fase: int, team_names: list[str]) -> dict:
    expected = QUALIFICATION_REQUIRED.get(fase)
    if expected is not None and len(team_names) != expected:
        return {
            "success": False,
            "error": f"Fase {fase} requires exactly {expected} teams, got {len(team_names)}",
        }
    ids = []
    for t in team_names:
        tid = TEAMS.get(t)
        if tid is None:
            return {"success": False, "error": f"Unknown team: '{t}'"}
        ids.append(str(tid))
    data = {"action": "qualificazioni", "fase": str(fase)}
    for i, tid in enumerate(ids):
        data[f"qualificate[{i}]"] = tid
    return _post(data)


def submit_special_bets(winner: str, capocannoniere_key: str) -> dict:
    winner_id = TEAMS.get(winner)
    player_id = PLAYERS.get(capocannoniere_key)
    if winner_id is None:
        return {"success": False, "error": f"Unknown winner team: '{winner}'"}
    if player_id is None:
        return {"success": False, "error": f"Unknown player: '{capocannoniere_key}'"}
    data = {
        "action": "special_bets",
        "vincitrice": str(winner_id),
        "capocannoniere": str(player_id),
    }
    return _post(data)


# ─── Retrieval helpers ────────────────────────────────────────────

def _empty_formation() -> dict:
    return {
        "group_bets": {},
        "qualifications": {},
        "special_bets": {},
        "prolific_total": None,
    }


def _scrape_group_page(group: str) -> dict:
    """Scrape one group wizard page. Returns {matches, pt_match_id}."""
    r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?group={group}&edit=1", timeout=TIMEOUT)
    html = r.text

    # Attribute-order-independent regex: match gCasa[ID]…value="…" within same tag
    home_raw = re.findall(r'gCasa\[(\d+)\][^>]*value="(\d*)"', html)
    away_raw = re.findall(r'gOspite\[(\d+)\][^>]*value="(\d*)"', html)
    team_names = re.findall(r'wizard-match-name[^>]*>(.*?)</span>', html)
    pt_checked = re.search(r'prolific_id[^>]*value="(\d+)"[^>]*checked', html)

    matches = []
    for i, (mid_str, h_val) in enumerate(home_raw):
        mid = int(mid_str)
        a_val = away_raw[i][1] if i < len(away_raw) else ""
        h_team = team_names[i * 2] if i * 2 < len(team_names) else "?"
        a_team = team_names[i * 2 + 1] if i * 2 + 1 < len(team_names) else "?"
        matches.append({
            "home": h_team,
            "away": a_team,
            "score": f"{h_val}-{a_val}" if h_val or a_val else None,
            "match_id": mid,
            "is_pt": pt_checked is not None and int(pt_checked.group(1)) == mid,
        })

    return {
        "matches": matches,
        "pt_match_id": int(pt_checked.group(1)) if pt_checked else None,
    }


def _get_username() -> str | None:
    """Extract the logged-in user's username from the page header."""
    try:
        r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?group=A&edit=1", timeout=TIMEOUT)
        m = re.search(r'teamName[^>]*>\s*(.*?)\s*</div>', r.text)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def _scrape_qualifications_from_player_page(username: str) -> dict:
    """Scrape all knockout qualification phases from the player's formation page.
    The wizard edit pages don't show qualifications when the formation is complete,
    so we fetch the player's public formation page instead."""
    quals = {}
    try:
        r = SESSION.get(
            f"{BASE_URL}/index_schedine_utente.php?user={username}", timeout=TIMEOUT
        )
        html = r.text
    except Exception:
        return quals

    # Phase names (Italian) mapped to fase numbers
    phase_names = [
        ("Sedicesimi", 16),
        ("Ottavi", 8),
        ("Quarti", 4),
        ("Semifinali", 2),
        ("Finale", 1),
        ("Finalisti", 1),  # fallback alternate name
    ]

    for phase_name, fase in phase_names:
        header_pos = html.find(f">{phase_name}<")
        if header_pos < 0:
            continue
        # Find the next phase header to delimit this section
        next_header = len(html)
        for other_name, _ in phase_names:
            if other_name == phase_name:
                continue
            other_pos = html.find(f">{other_name}<", header_pos + 1)
            if other_pos > header_pos and other_pos < next_header:
                next_header = other_pos
        section = html[header_pos:next_header]
        teams = re.findall(r'team-row-name[^>]*>(.*?)</span>', section)
        if teams:
            quals[str(fase)] = [t.strip() for t in teams]

    return quals


def _scrape_special_bets() -> dict:
    """Scrape special bets (winner, capocannoniere). Returns {winner?, capocannoniere?}."""
    bets = {}
    try:
        r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?special=1&edit=1", timeout=TIMEOUT)
        html = r.text
        winner_m = re.search(r'vincitrice[^>]*value="(\d+)"[^>]*checked', html)
        # Capocannoniere: could be <option selected> or <input checked>
        capo_m = re.search(r'<option[^>]*value="(\d+)"[^>]*selected', html)
        if not capo_m:
            capo_m = re.search(r'capocannoniere[^>]*value="(\d+)"[^>]*checked', html)
        if winner_m:
            bets["winner"] = TEAM_BY_ID.get(
                int(winner_m.group(1)), f"id:{winner_m.group(1)}"
            )
        if capo_m:
            bets["capocannoniere"] = PLAYER_BY_ID.get(
                int(capo_m.group(1)), f"id:{capo_m.group(1)}"
            )
    except Exception:
        pass
    return bets


def _scrape_prolific_total(username: str | None = None) -> dict | None:
    """Scrape the tournament-wide prolific total match (Pt).
    Strategy: scrape from own schedina page (reliable), fallback to wizard URLs.
    """
    # ── Primary: scrape Pt from own schedina page (shows pt-box indicator) ──
    if username:
        try:
            r = SESSION.get(
                f"{BASE_URL}/index_schedine_utente.php?user={username}", timeout=TIMEOUT
            )
            html = r.text
            for g in MATCHES:
                panel_m = re.search(rf'<div\s+class="group-panel"\s+data-group="{g}"', html)
                if not panel_m:
                    continue
                next_panel = re.search(
                    r'<div\s+class="group-panel"\s+data-group="', html[panel_m.start() + 1:]
                )
                section_end = panel_m.start() + 1 + next_panel.start() if next_panel else len(html)
                section = html[panel_m.start():section_end]

                if "pt-box" not in section:
                    continue

                tables = re.split(r'<table class="mcm-table[^"]*">', section)[1:]
                for match_idx, table_html in enumerate(tables):
                    table_end = table_html.find("</table>")
                    if table_end > 0:
                        table_html = table_html[:table_end]
                    if "pt-box" in table_html:
                        match_id = MATCHES[g][match_idx] if match_idx < len(MATCHES[g]) else None
                        if match_id:
                            return {"group": g, "match_index": match_idx, "match_id": match_id}
        except Exception:
            pass

    # ── Fallback: try wizard edit pages directly ──
    urls_to_try = [
        f"{BASE_URL}/wizard_scommesse.php?prolifico=1&edit=1",
        f"{BASE_URL}/wizard_scommesse.php?pt=1&edit=1",
        f"{BASE_URL}/wizard_scommesse.php?fase=0&edit=1",
    ]
    for url in urls_to_try:
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            pt = re.search(r'prolific_id[^>]*value="(\d+)"[^>]*checked', r.text)
            if pt:
                match_id = int(pt.group(1))
                for g, mids in MATCHES.items():
                    for i, mid in enumerate(mids):
                        if mid == match_id:
                            return {"group": g, "match_index": i, "match_id": match_id}
                return {"match_id": match_id, "group": None, "match_index": None}
        except Exception:
            continue
    return None


# ─── Main retrieval functions ────────────────────────────────────

def get_formation() -> dict:
    """Return logged-in user's complete formation. Continues past individual page errors."""
    auth = ensure_auth()
    if not auth["success"]:
        f = _empty_formation()
        f["error"] = auth["error"]
        return f

    f = _empty_formation()

    # 0) Get the logged-in username (needed for qualifications)
    username = _get_username()

    # 1) Group bets — 12 groups, keep going if any page fails
    for g in MATCHES:
        try:
            f["group_bets"][g] = _scrape_group_page(g)
        except Exception as e:
            f["group_bets"][g] = {"error": str(e), "matches": [], "pt_match_id": None}

    # 2) Qualifications — scraped from player formation page
    if username:
        try:
            f["qualifications"] = _scrape_qualifications_from_player_page(username)
        except Exception as e:
            f["qualifications"] = {"error": str(e)}

    # 3) Special bets (winner + capocannoniere)
    try:
        f["special_bets"] = _scrape_special_bets()
    except Exception as e:
        f["special_bets"] = {"error": str(e)}

    # 4) Prolific total (Pt) — best-effort, may not be retrievable
    try:
        pt = _scrape_prolific_total(username)
        if pt:
            f["prolific_total"] = pt
    except Exception:
        pass

    return f


def list_players() -> list[dict]:
    """Return leaderboard: list of {pos, username, display_name, points}."""
    auth = ensure_auth()
    if not auth["success"]:
        return [{"error": auth["error"]}]

    try:
        r = SESSION.get(f"{BASE_URL}/index_classifica.php", timeout=TIMEOUT)
    except requests.RequestException as e:
        return [{"error": f"Failed to fetch leaderboard: {e}"}]

    # Primary regex: handles medal HTML entities (&amp;#129351; etc) and class='pos-cell'
    rows = re.findall(
        r"<td[^>]*>(?:&#\d+;)?\s*(\d+°?)</td>\s*<td><a[^>]*user=([^'&\s]+)[^>]*>([^<]+)</a></td>\s*<td>(\d+)</td>",
        r.text,
    )
    # Fallback: no degree symbol
    if not rows:
        rows = re.findall(
            r"<td[^>]*>(?:&#\d+;)?\s*(\d+)</td>\s*<td><a[^>]*user=([^'&\s]+)[^>]*>([^<]+)</a></td>\s*<td>(\d+)</td>",
            r.text,
        )

    return [
        {"pos": pos, "username": user, "display_name": name.strip(), "points": int(pts)}
        for pos, user, name, pts in rows
    ]


def get_player_formation(username: str) -> dict:
    """Return another player's formation. Returns empty structure on auth failure."""
    auth = ensure_auth()
    if not auth["success"]:
        return {
            "username": username,
            "error": auth["error"],
            "group_bets": {},
            "qualifications": {},
            "special_bets": {},
        }

    f: dict = {"username": username, "group_bets": {}, "qualifications": {}, "special_bets": {}}

    try:
        r = SESSION.get(
            f"{BASE_URL}/index_schedine_utente.php?user={username}", timeout=TIMEOUT
        )
    except requests.RequestException as e:
        f["error"] = str(e)
        return f

    html = r.text

    # ── Group bets ──
    # New HTML structure: <div class="group-panel" data-group="A">
    # Each match is a <table class="mcm-table"> with:
    #   <td class="mcm-tl mcm-name">HOME</td>
    #   <td class="mcm-tr mcm-name">AWAY</td>
    #   <span class="mcm-bet-val">H - A</span>
    #   <span class="mcm-date">DATE</span>
    #   <span class="prolific-box pg-box">Pg</span> or <span class="prolific-box pt-box">Pt</span>
    for g in "ABCDEFGHIJKL":
        # Find the group-panel div for this group (skip the tab button)
        # Must match exact class "group-panel", not "group-panel-header"
        panel_start = None
        for m in re.finditer(r'<div\s+class="group-panel"\s+data-group="([^"]+)"', html):
            if m.group(1) == g:
                panel_start = m.start()
                break
        if panel_start is None:
            continue

        # Find the next group-panel div to delimit this section
        next_panel_m = re.search(r'<div\s+class="group-panel"\s+data-group="', html[panel_start + 1:])
        next_panel = panel_start + 1 + next_panel_m.start() if next_panel_m else len(html)

        section = html[panel_start:next_panel]

        matches = []
        # Find all mcm-table blocks
        tables = re.split(r'<table class="mcm-table[^"]*">', section)[1:]
        for table_html in tables:
            # Close at the first </table>
            table_end = table_html.find("</table>")
            if table_end > 0:
                table_html = table_html[:table_end]

            home_m = re.search(r'mcm-tl[^>]*mcm-name[^>]*>(.*?)</td>', table_html)
            away_m = re.search(r'mcm-tr[^>]*mcm-name[^>]*>(.*?)</td>', table_html)
            bet_m = re.search(r'mcm-bet-val[^>]*>\s*([\d?]+\s*-\s*[\d?]+)\s*</span>', table_html)
            date_m = re.search(r'mcm-date[^>]*>(.*?)</span>', table_html)
            is_pg = "pg-box" in table_html
            is_pt = "pt-box" in table_html

            matches.append({
                "home": home_m.group(1).strip() if home_m else "?",
                "away": away_m.group(1).strip() if away_m else "?",
                "bet": bet_m.group(1).strip() if bet_m else None,
                "date": date_m.group(1).strip() if date_m else None,
                "is_pg": is_pg,
                "is_pt": is_pt,
            })

        if matches:
            f["group_bets"][g] = matches

    # ── Qualifications ──
    # Same logic as _scrape_qualifications_from_player_page
    phase_names = [
        ("Sedicesimi", 16), ("Ottavi", 8), ("Quarti", 4),
        ("Semifinali", 2), ("Finale", 1), ("Finalisti", 1),
    ]
    quals = {}
    for phase_name, fase in phase_names:
        header_pos = html.find(f">{phase_name}<")
        if header_pos < 0:
            continue
        next_header = len(html)
        for other_name, _ in phase_names:
            if other_name == phase_name:
                continue
            other_pos = html.find(f">{other_name}<", header_pos + 1)
            if other_pos > header_pos and other_pos < next_header:
                next_header = other_pos
        section = html[header_pos:next_header]
        teams = re.findall(r'team-row-name[^>]*>(.*?)</span>', section)
        if teams:
            quals[str(fase)] = [t.strip() for t in teams]
    if quals:
        f["qualifications"] = quals

    # ── Special bets ──
    # New HTML structure: finale-section with finale-pick-name
    winner_ctx_start = html.find("Vincitrice del Mondiale")
    if winner_ctx_start > 0:
        ctx = html[winner_ctx_start:winner_ctx_start + 600]
        winner_m = re.search(r'finale-pick-name[^>]*>(.*?)</(?:span|div)>', ctx)
        if winner_m:
            f["special_bets"]["winner"] = winner_m.group(1).strip()

    capo_ctx_start = html.find("Capocannoniere</div>")
    if capo_ctx_start < 0:
        capo_ctx_start = html.find("Capocannoniere Section")
    if capo_ctx_start > 0:
        ctx = html[capo_ctx_start:capo_ctx_start + 600]
        capo_m = re.search(r'finale-pick-name[^>]*>(.*?)</(?:span|div)>', ctx)
        if capo_m:
            f["special_bets"]["capocannoniere"] = capo_m.group(1).strip()

    return f
