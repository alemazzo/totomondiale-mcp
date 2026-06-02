"""Totomondiale HTTP client: login, fetch, submit all bet types."""
import os
import re
from typing import Union
import requests
from src.models import MATCHES, TEAMS, PLAYERS, TEAM_BY_ID, PLAYER_BY_ID, QUALIFICATION_REQUIRED

BASE_URL = "https://totomondiale.altervista.org"
SESSION = requests.Session()
_logged_in = False


def _get_csrf_token(html: str) -> str:
    m = re.search(r'csrf_token"\s+value="([^"]+)"', html)
    return m.group(1) if m else ""


def _get_fresh_csrf() -> str:
    r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?group=A&edit=1")
    return _get_csrf_token(r.text)


def login(email: str, password: str) -> dict:
    global _logged_in
    SESSION.cookies.clear()
    _logged_in = False
    r = SESSION.get(f"{BASE_URL}/index_scommesse.php", allow_redirects=True)
    csrf = _get_csrf_token(r.text)
    if not csrf:
        return {"success": False, "error": "Could not get CSRF token"}
    r = SESSION.post(
        f"{BASE_URL}/processaAccesso.php",
        data={"csrf_token": csrf, "email": email, "password": password, "login": "1"},
        allow_redirects=True,
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
        return {"success": False, "error": "Not logged in. Set TOTOMONDIALE_EMAIL and TOTOMONDIALE_PASSWORD env vars, or call login first."}
    return login(email, password)


def _post(data: Union[dict, list]) -> dict:
    auth = ensure_auth()
    if not auth["success"]:
        return auth
    csrf = _get_fresh_csrf()
    if isinstance(data, dict):
        data["csrf_token"] = csrf
        data["redirect"] = "scommesse"
        r = SESSION.post(f"{BASE_URL}/processaWizard.php", data=data, allow_redirects=True)
    else:
        data_list = [("csrf_token", csrf)] + list(data)
        r = SESSION.post(f"{BASE_URL}/processaWizard.php", data=data_list, allow_redirects=True)

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
    return {"success": False, "error": f"Unexpected response (status {r.status_code}, url={r.url}, text={snippet})"}


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
        return {"success": False, "error": f"Fase {fase} requires exactly {expected} teams, got {len(team_names)}"}
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


def get_formation() -> dict:
    auth = ensure_auth()
    if not auth["success"]:
        return auth
    f = {"group_bets": {}, "qualifications": {}, "special_bets": {}, "prolific_total": None}

    for g in MATCHES:
        r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?group={g}&edit=1")
        home = re.findall(r'name="gCasa\[(\d+)\]"[^>]*value="(\d*)"', r.text)
        away = re.findall(r'name="gOspite\[(\d+)\]"[^>]*value="(\d*)"', r.text)
        team_names = re.findall(r'class="wizard-match-name">(.*?)</span>', r.text)
        pt_checked = re.search(r'name="prolific_id"\s+value="(\d+)"\s+checked', r.text)

        matches = []
        for i, (mid_h, h_val) in enumerate(home):
            mid = int(mid_h)
            a_val = away[i][1] if i < len(away) else ""
            h_team = team_names[i * 2] if i * 2 < len(team_names) else "?"
            a_team = team_names[i * 2 + 1] if i * 2 + 1 < len(team_names) else "?"
            matches.append({
                "home": h_team, "away": a_team,
                "score": f"{h_val}-{a_val}" if h_val and a_val else None,
                "match_id": mid,
                "is_pt": pt_checked and int(pt_checked.group(1)) == mid,
            })
        f["group_bets"][g] = {
            "matches": matches,
            "pt_match_id": int(pt_checked.group(1)) if pt_checked else None,
        }

    r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php")
    for fase in [16, 8, 4, 2, 1]:
        r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?fase={fase}&edit=1")
        checked = re.findall(r'name="qualificate\[\]"\s+value="(\d+)"\s+checked', r.text)
        if checked:
            f["qualifications"][str(fase)] = [TEAM_BY_ID.get(int(tid), f"id:{tid}") for tid in checked]

    r = SESSION.get(f"{BASE_URL}/wizard_scommesse.php?special=1&edit=1")
    winner_m = re.search(r'name="vincitrice"\s+value="(\d+)"\s+checked', r.text)
    capo_m = re.search(r'<option[^>]*value="(\d+)"[^>]*selected', r.text)
    if winner_m:
        f["special_bets"]["winner"] = TEAM_BY_ID.get(int(winner_m.group(1)), f"id:{winner_m.group(1)}")
    if capo_m:
        f["special_bets"]["capocannoniere"] = PLAYER_BY_ID.get(int(capo_m.group(1)), f"id:{capo_m.group(1)}")

    return f


def list_players() -> list[dict]:
    auth = ensure_auth()
    if not auth["success"]:
        return auth
    r = SESSION.get(f"{BASE_URL}/index_classifica.php")
    rows = re.findall(
        r"<tr[^>]*>\s*<td>(\d+°)</td>\s*<td><a href='index_schedine_utente\.php\?user=([^']+)'[^>]*>([^<]+)</a></td>\s*<td>(\d+)</td>",
        r.text,
    )
    return [
        {"pos": pos, "username": user, "display_name": name.strip(), "points": int(pts)}
        for pos, user, name, pts in rows
    ]


def get_player_formation(username: str) -> dict:
    auth = ensure_auth()
    if not auth["success"]:
        return auth
    r = SESSION.get(f"{BASE_URL}/index_schedine_utente.php?user={username}")

    f: dict = {"username": username, "group_bets": {}, "qualifications": {}, "special_bets": {}}

    for g in "ABCDEFGHIJKL":
        letter_pos = r.text.find(f">Girone {g}<")
        if letter_pos < 0:
            continue
        # Find the group-body div opening tag after the group letter
        body_div_start = r.text.find('<div class="group-body"', letter_pos)
        if body_div_start < 0:
            continue
        body_start = r.text.find(">", body_div_start) + 1  # first char after the opening tag
        # Count nesting from INSIDE the group-body div
        body_end = body_start
        depth = 1
        pos = body_start
        while depth > 0 and pos < len(r.text):
            next_open = r.text.find("<div", pos)
            next_close = r.text.find("</div>", pos)
            if next_close < 0:
                break
            if next_open >= 0 and next_open < next_close:
                depth += 1
                pos = next_open + 4
            else:
                depth -= 1
                if depth == 0:
                    body_end = next_close
                    break
                pos = next_close + 6

        body_html = r.text[body_start:body_end]

        matches = []
        # Split on match-row-compact opening tags
        rows_html = re.split(r'<div class="match-row-compact[^"]*">', body_html)[1:]
        for row_html in rows_html:
            # Find the matching closing </div> by counting nesting
            depth = 1
            pos = 0
            while depth > 0:
                next_open = row_html.find("<div", pos)
                next_close = row_html.find("</div>", pos)
                if next_close < 0:
                    break
                if next_open >= 0 and next_open < next_close:
                    depth += 1
                    pos = next_open + 4
                else:
                    depth -= 1
                    if depth == 0:
                        row_html = row_html[:next_close]
                        break
                    pos = next_close + 6

            teams = re.findall(r'class="team-name">(.*?)</span>', row_html)
            bet = re.search(r'class="bet-score[^"]*">\s*([\d?]+-[\d?]+)\s*</span>', row_html)
            is_pg = "bet-badge pg" in row_html
            date = re.search(r'class="match-date">(.*?)</span>', row_html)
            matches.append({
                "home": teams[0].strip() if teams else "?",
                "away": teams[1].strip() if len(teams) > 1 else "?",
                "bet": bet.group(1).strip() if bet else None,
                "is_pg": is_pg,
                "date": date.group(1).strip() if date else None,
            })
        if matches:
            f["group_bets"][g] = matches

    # Qualifications
    qual_section = re.search(
        r'id=["\']qualificazioni["\'].*?</div>\s*</div>\s*</div>',
        r.text, re.DOTALL,
    )
    if qual_section:
        teams = re.findall(r'class="team-name">(.*?)</span>', qual_section.group())
        if teams:
            f["qualifications"] = {"teams": [t.strip() for t in teams]}

    # Special bets (finali tab)
    finali_section = re.search(
        r'id=["\']finali["\'].*?</div>\s*</div>\s*</div>',
        r.text, re.DOTALL,
    )
    if finali_section:
        sec = finali_section.group()
        winner_m = re.search(r"Vincitrice.*?class=\"team-name\">(.*?)</span>", sec, re.DOTALL)
        capo_m = re.search(r"Capocannoniere.*?class=\"team-name\">(.*?)</span>", sec, re.DOTALL)
        if winner_m:
            f["special_bets"]["winner"] = winner_m.group(1).strip()
        if capo_m:
            f["special_bets"]["capocannoniere"] = capo_m.group(1).strip()

    return f
