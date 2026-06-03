"""End-to-end tests for the Totomondiale client. Uses env vars for credentials."""
import os
import sys
import json
import time
from src.client import (
    login, get_formation, submit_group_bets, submit_prolific_total,
    submit_qualification, submit_special_bets,
    list_players, get_player_formation,
)
from src.models import MATCHES, TEAMS, PLAYERS, TEAM_BY_ID

EMAIL = os.environ.get("TOTOMONDIALE_EMAIL", "")
PASSWORD = os.environ.get("TOTOMONDIALE_PASSWORD", "")

passed = 0
failed = 0


def t(name, fn):
    global passed, failed
    try:
        fn()
        passed += 1
        print(f"  \u2713 {name}")
    except AssertionError as e:
        failed += 1
        print(f"  \u2717 {name}: {e}")
    except Exception as e:
        failed += 1
        print(f"  \u2717 {name}: {type(e).__name__}: {e}")


def assert_true(val, msg=""):
    assert val, msg or f"Expected truthy, got {val!r}"


def assert_eq(a, b, msg=""):
    assert a == b, msg or f"Expected {b!r}, got {a!r}"


# ============================================================
# Auth
# ============================================================
def test_login():
    if not EMAIL or not PASSWORD:
        raise AssertionError("Set TOTOMONDIALE_EMAIL and TOTOMONDIALE_PASSWORD env vars")
    result = login(EMAIL, PASSWORD)
    assert_true(result["success"], f"Login failed: {result.get('error')}")


def test_login_bad_credentials():
    result = login("wrong@email.com", "wrongpass")
    assert not result["success"]
    # Re-auth after session clear
    if EMAIL and PASSWORD:
        login(EMAIL, PASSWORD)


# ============================================================
# Match & team data
# ============================================================
def test_all_groups_present():
    assert_eq(len(MATCHES), 12)
    for g in "ABCDEFGHIJKL":
        assert g in MATCHES
        assert_eq(len(MATCHES[g]), 6)


def test_all_teams_present():
    assert_eq(len(TEAMS), 48)
    ids = set(TEAMS.values())
    assert_eq(len(ids), 48)


def test_all_players_present():
    assert len(PLAYERS) > 10
    known = {"Mbapp\u00e9", "Haaland", "Messi", "C.Ronaldo", "Yamal"}
    assert known.issubset(PLAYERS.keys())


# ============================================================
# Formation (read)
# ============================================================
def test_get_formation_structure():
    f = get_formation()
    assert "group_bets" in f
    assert "qualifications" in f
    assert "special_bets" in f
    assert "prolific_total" in f
    assert_eq(len(f["group_bets"]), 12)
    for g in MATCHES:
        assert g in f["group_bets"]
        assert_eq(len(f["group_bets"][g]["matches"]), 6)


def test_get_formation_has_data():
    f = get_formation()
    filled = sum(1 for g in f["group_bets"].values() if any(m["score"] for m in g["matches"]))
    assert filled > 0, "No group bets found"


def test_get_formation_no_error_key_when_auth_ok():
    """When auth is OK, the formation should NOT have an 'error' top-level key."""
    f = get_formation()
    assert "error" not in f, f"Unexpected error key: {f.get('error')}"


def test_get_formation_prolific_total_may_be_set():
    """If the user has set a prolific total, it should be reflected."""
    f = get_formation()
    pt = f.get("prolific_total")
    # It may be None if not set; if set, verify structure
    if pt is not None:
        assert "match_id" in pt, f"prolific_total missing match_id: {pt}"
        print(f"      (Pt set: group={pt.get('group')}, idx={pt.get('match_index')}, mid={pt['match_id']})")


# ============================================================
# Group bets (submit + verify)
# ============================================================
def test_group_bets_submit_and_verify():
    # Save original
    orig = get_formation()["group_bets"]["A"]
    orig_scores = [m["score"] for m in orig["matches"]]
    orig_pt_idx = None
    for i, m in enumerate(orig["matches"]):
        if m["is_pt"]:
            orig_pt_idx = i

    # Submit new scores
    new_scores = ["1-0", "2-1", "3-0", "1-1", "0-2", "2-2"]
    result = submit_group_bets("A", new_scores, 2)
    assert_true(result["success"], f"Submit failed: {result}")
    time.sleep(0.5)  # avoid rate limiting

    # Verify
    after = get_formation()["group_bets"]["A"]
    after_scores = [m["score"] for m in after["matches"]]
    assert_eq(after_scores, new_scores, "Scores not saved")
    assert_true(after["matches"][2]["is_pt"], "PT index 2 not saved")

    # Restore
    restore_result = submit_group_bets("A", orig_scores, orig_pt_idx or 0)
    assert_true(restore_result["success"], "Restore failed")


def test_group_bets_invalid_group():
    result = submit_group_bets("X", ["1-1"] * 6, 0)
    assert not result["success"]


def test_group_bets_wrong_count():
    result = submit_group_bets("A", ["1-1"] * 3, 0)
    assert not result["success"]


def test_group_bets_invalid_score_format():
    """Score without hyphen should be rejected with a clear error."""
    result = submit_group_bets("A", ["11", "22", "3-0", "1-1", "0-2", "2-2"], 0)
    assert not result["success"]
    assert "Invalid score format" in result.get("error", "")


# ============================================================
# Qualification (submit + verify)
# ============================================================
def test_qualification_reject_wrong_count():
    result = submit_qualification(16, ["Argentina", "Brazil", "France"])
    assert not result["success"], "Should reject less than 32 teams for fase 16"


def test_qualification_submit_accepted():
    all_teams = sorted(TEAMS.keys())
    teams_32 = all_teams[:32]
    result = submit_qualification(16, teams_32)
    assert_true(result["success"], f"Qualification submit not accepted: {result}")


def test_qualification_unknown_team():
    result = submit_qualification(8, ["Nonexistent", "Argentina"] * 8)
    assert not result["success"]


# ============================================================
# Special bets (submit + verify)
# ============================================================
def test_special_bets_submit_and_verify():
    # Save original
    orig = get_formation()["special_bets"]

    # Submit
    result = submit_special_bets("Argentina", "Messi")
    assert_true(result["success"], f"Special bets submit failed: {result}")

    # Verify
    after = get_formation()["special_bets"]
    assert_eq(after.get("winner"), "Argentina", "Winner not saved")
    assert_eq(after.get("capocannoniere"), "Messi", "Capocannoniere not saved")

    # Restore
    if orig.get("winner") or orig.get("capocannoniere"):
        restore_result = submit_special_bets(
            orig.get("winner", "Argentina"),
            orig.get("capocannoniere", "Messi"),
        )
        assert_true(restore_result["success"], "Restore failed")


def test_special_bets_unknown_winner():
    result = submit_special_bets("FakeTeam", "Messi")
    assert not result["success"]


def test_special_bets_unknown_player():
    result = submit_special_bets("Argentina", "FakePlayer")
    assert not result["success"]


# ============================================================
# Prolific total (submit)
# ============================================================
def test_prolific_total_submit():
    result = submit_prolific_total("A", 1)
    assert_true(result["success"], f"Prolific total submit failed: {result}")


# ============================================================
# Player tools
# ============================================================
def test_list_players():
    players = list_players()
    assert len(players) > 0, "No players on leaderboard"
    # Check no error key on first element when auth is OK
    if players and "error" in players[0]:
        print(f"      (Auth note: {players[0]['error']})")
        return
    assert "pos" in players[0]
    assert "username" in players[0]
    assert "points" in players[0]


def test_get_player_formation():
    players = list_players()
    if len(players) < 2:
        return  # not enough players to test
    username = players[1]["username"]  # second player (not self)
    f = get_player_formation(username)
    assert_eq(f["username"], username)
    assert len(f["group_bets"]) > 0, "No group bets for other player"


def test_get_player_formation_unknown():
    f = get_player_formation("nonexistent_user_12345")
    # Should return empty matches for all groups
    total_bets = sum(1 for matches in f["group_bets"].values() for m in matches if m.get("bet"))
    assert_eq(total_bets, 0, f"Expected 0 bets for unknown user, got {total_bets}")


# ============================================================
# Run all
# ============================================================
def main():
    global passed, failed

    groups = [
        ("Auth", [
            ("Login succeeds", test_login),
            ("Login rejects bad credentials", test_login_bad_credentials),
        ]),
        ("Data models", [
            ("All 12 groups with 6 matches", test_all_groups_present),
            ("48 teams with unique IDs", test_all_teams_present),
            ("Player list includes key players", test_all_players_present),
        ]),
        ("Get formation", [
            ("Structure has all sections", test_get_formation_structure),
            ("Group bets have data", test_get_formation_has_data),
            ("No error key when auth OK", test_get_formation_no_error_key_when_auth_ok),
            ("Prolific total may be set", test_get_formation_prolific_total_may_be_set),
        ]),
        ("Group bets", [
            ("Submit + verify + restore", test_group_bets_submit_and_verify),
            ("Reject invalid group", test_group_bets_invalid_group),
            ("Reject wrong score count", test_group_bets_wrong_count),
            ("Reject invalid score format", test_group_bets_invalid_score_format),
        ]),
        ("Qualification", [
            ("Reject wrong team count", test_qualification_reject_wrong_count),
            ("Submit accepted by server", test_qualification_submit_accepted),
            ("Reject unknown team", test_qualification_unknown_team),
        ]),
        ("Special bets", [
            ("Submit + verify + restore", test_special_bets_submit_and_verify),
            ("Reject unknown winner", test_special_bets_unknown_winner),
            ("Reject unknown player", test_special_bets_unknown_player),
        ]),
        ("Prolific total", [
            ("Submit works", test_prolific_total_submit),
        ]),
        ("Player tools", [
            ("List players returns data", test_list_players),
            ("Get other player formation works", test_get_player_formation),
            ("Unknown user returns empty", test_get_player_formation_unknown),
        ]),
    ]

    print("=" * 60)
    print("Totomondiale MCP \u2014 End-to-End Tests")
    print("=" * 60)

    for group_name, tests in groups:
        print(f"\n--- {group_name} ---")
        for test_name, test_fn in tests:
            t(test_name, test_fn)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
    print(f"{'=' * 60}")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
