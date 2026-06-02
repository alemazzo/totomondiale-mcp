"""Totomondiale data models: matches, teams, players."""

MATCHES: dict[str, list[int]] = {
    "A": [537327, 537328, 537329, 537330, 537331, 537332],
    "B": [537333, 537334, 537335, 537336, 537337, 537338],
    "C": [537339, 537340, 537342, 537341, 537343, 537344],
    "D": [537345, 537346, 537348, 537347, 537349, 537350],
    "E": [537351, 537352, 537353, 537354, 537355, 537356],
    "F": [537357, 537358, 537359, 537360, 537361, 537362],
    "G": [537363, 537364, 537365, 537366, 537367, 537368],
    "H": [537369, 537370, 537371, 537372, 537373, 537374],
    "I": [537391, 537392, 537393, 537394, 537395, 537396],
    "J": [537397, 537398, 537399, 537400, 537401, 537402],
    "K": [537403, 537404, 537405, 537406, 537407, 537408],
    "L": [537409, 537410, 537411, 537412, 537413, 537414],
}

TEAMS: dict[str, int] = {
    "Algeria": 778, "Argentina": 762, "Australia": 779, "Austria": 816,
    "Belgium": 805, "Bosnia Herz.": 1060, "Brazil": 764, "Canada": 828,
    "Capo Verde": 1930, "Colombia": 818, "Congo DR": 1934, "Croatia": 799,
    "Curaçao": 9460, "Cechia": 798, "Ecuador": 791, "Egypt": 825,
    "Inghilterra": 770, "France": 773, "Germany": 759, "Ghana": 763,
    "Haiti": 836, "Iran": 840, "Iraq": 8062, "Costa Avorio": 1935,
    "Japan": 766, "Jordan": 8049, "Mexico": 769, "Morocco": 815,
    "Olanda": 8601, "Nuova Zel.": 783, "Norway": 8872, "Panama": 1836,
    "Paraguay": 761, "Portugal": 765, "Qatar": 8030, "Arabia Saud.": 801,
    "Scotland": 8873, "Senegal": 804, "Sudafrica": 774, "Corea Sud": 772,
    "Spain": 760, "Sweden": 792, "Svizzera": 788, "Tunisia": 802,
    "Turkey": 803, "USA": 771, "Uruguay": 758, "Uzbekistan": 8070,
}

PLAYERS: dict[str, int] = {
    "Mbappé": 3374, "Haaland": 38101, "Messi": 3218, "C.Ronaldo": 44,
    "Yamal": 202283, "Vinícius Jr": 3712, "Salah": 3754, "Kane": 8004,
    "Bellingham": 125010, "Gakpo": 7459, "Musiala": 144393, "Leão": 15892,
    "Lautaro Martínez": 3220, "Julián Álvarez": 98571,
}

TEAM_BY_ID: dict[int, str] = {v: k for k, v in TEAMS.items()}
PLAYER_BY_ID: dict[int, str] = {v: k for k, v in PLAYERS.items()}

QUALIFICATION_REQUIRED: dict[int, int] = {
    16: 32,  # Sedicesimi: pick 32 teams advancing from groups
    8: 16,   # Ottavi
    4: 8,    # Quarti
    2: 4,    # Semifinali
    1: 2,    # Finalisti
}
