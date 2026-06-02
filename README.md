# Totomondiale MCP

MCP server per interagire con [Totomondiale](https://totomondiale.altervista.org) via AI agent (Claude, Codex, etc).

Permette di leggere la propria formazione, vedere la classifica, consultare le schedine degli altri giocatori e inviare pronostici programmaticamente.

## Installazione

```bash
git clone git@github.com:alemazzo/totomondiale-mcp.git
cd totomondiale-mcp
uv sync
```

## Configurazione MCP

### Opzione 1: Prompt per LLM

Copia e incolla nel tuo AI agent:

```
aggiungi l'mcp totomondiale da git+https://github.com/alemazzo/totomondiale-mcp
con env TOTOMONDIALE_EMAIL=mcp-test@gmail.com e TOTOMONDIALE_PASSWORD=password
```

### Opzione 2: Config manuale

Aggiungi le credenziali via env — il modello non le vedrà mai:

```json
{
  "mcpServers": {
    "totomondiale": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/alemazzo/totomondiale-mcp", "python", "server.py"],
      "env": {
        "TOTOMONDIALE_EMAIL": "mcp-test@gmail.com",
        "TOTOMONDIALE_PASSWORD": "password"
      }
    }
  }
}
```

L'MCP fa auto-login al primo tool chiamato. Nessuna necessità di passare credenziali al modello.

## Tool disponibili

| Tool | Descrizione |
|------|-------------|
| `totomondiale_get_formation` | Leggi la tua formazione completa |
| `totomondiale_list_matches` | Elenca match ID per ogni girone |
| `totomondiale_list_teams` | Elenca tutte le squadre con ID |
| `totomondiale_list_players` | Classifica giocatori con rank e punti |
| `totomondiale_get_player_formation` | Leggi la formazione di un altro giocatore |
| `totomondiale_submit_group_bets` | Invia pronostici per un girone (6 risultati + prolifico) |
| `totomondiale_submit_qualification` | Invia squadre qualificate per una fase |
| `totomondiale_submit_special_bets` | Invia vincitore e capocannoniere |
| `totomondiale_submit_prolific_total` | Invia la partita più prolifica del torneo (Pt) |

Il tool `totomondiale_login` è disponibile come fallback se non vuoi usare le env vars.

## Esempi

```
> qual è la mia formazione?

> invia i pronostici per il girone A: 2-1, 1-1, 3-0, 0-2, 1-0, 2-2 con prolifico match 2

> chi è in testa alla classifica?

> fammi vedere la formazione di ArtuMazz
```

## Test

```bash
TOTOMONDIALE_EMAIL=mcp-test@gmail.com TOTOMONDIALE_PASSWORD=password uv run python -m tests.test_client
```

## Struttura

```
totomondiale-mcp/
├── server.py          # MCP server entry point
├── src/
│   ├── client.py      # HTTP client: login, submit, read (auto-auth via env)
│   └── models.py      # Data: matches, teams, players
├── tests/
│   └── test_client.py # 20 test end-to-end
└── pyproject.toml
```
