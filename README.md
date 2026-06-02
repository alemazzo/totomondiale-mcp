# Totomondiale MCP

MCP server per interagire con [Totomondiale](https://totomondiale.altervista.org) via AI agent (Claude, Codex, etc).

Permette di leggere la propria formazione, vedere la classifica, consultare le schedine degli altri giocatori e inviare pronostici programmaticamente.

## Installazione

```bash
git clone <repo-url>
cd totomondiale-mcp
uv sync
```

## Configurazione MCP

```json
{
  "mcpServers": {
    "totomondiale": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/alemazzo/totomondiale-mcp", "python", "server.py"]
    }
  }
}
```

## Tool disponibili

| Tool | Descrizione |
|------|-------------|
| `totomondiale_login` | Autenticazione (email + password) |
| `totomondiale_get_formation` | Leggi la tua formazione completa |
| `totomondiale_list_matches` | Elenca match ID per ogni girone |
| `totomondiale_list_teams` | Elenca tutte le squadre con ID |
| `totomondiale_list_players` | Classifica giocatori con rank e punti |
| `totomondiale_get_player_formation` | Leggi la formazione di un altro giocatore |
| `totomondiale_submit_group_bets` | Invia pronostici per un girone (6 risultati + prolifico) |
| `totomondiale_submit_qualification` | Invia squadre qualificate per una fase |
| `totomondiale_submit_special_bets` | Invia vincitore e capocannoniere |
| `totomondiale_submit_prolific_total` | Invia la partita più prolifica del torneo (Pt) |

## Esempi

```
> fai il login su totomondiale con mcp-test@gmail.com

> qual è la mia formazione?

> invia i pronostici per il girone A: 2-1, 1-1, 3-0, 0-2, 1-0, 2-2 con prolifico match 2

> chi è in testa alla classifica?

> fammi vedere la formazione di ArtuMazz
```

## Test

```bash
uv run python -m tests.test_client
```

I test usano le credenziali `mcp-test@gmail.com` / `password` definite in `tests/test_client.py`.

## Struttura

```
totomondiale-mcp/
├── server.py          # MCP server entry point
├── src/
│   ├── client.py      # HTTP client: login, submit, read
│   └── models.py      # Data: matches, teams, players
├── tests/
│   └── test_client.py # 20 test end-to-end
└── pyproject.toml
```
