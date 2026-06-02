# Totomondiale MCP

MCP server per interagire con [Totomondiale](https://totomondiale.altervista.org) via AI agent.

Permette di leggere la propria formazione, vedere la classifica, consultare le schedine degli altri giocatori e inviare pronostici programmaticamente. L'autenticazione avviene automaticamente in background — le credenziali non vengono mai esposte al modello.

## Installazione

Copia e incolla questo prompt nel tuo AI agent:

```
Aggiungi un MCP server al file opencode.json (o ~/.config/opencode/opencode.json) sotto la chiave "mcp" con queste impostazioni:

"totomondiale": {
  "type": "local",
  "command": ["uvx", "--from", "git+https://github.com/alemazzo/totomondiale-mcp", "totomondiale-mcp"],
  "enabled": true,
  "timeout": 30000,
  "environment": {
    "TOTOMONDIALE_EMAIL": "<email>",
    "TOTOMONDIALE_PASSWORD": "<password>"
  }
}

Chiedi all'utente email e password del suo account Totomondiale e sostituiscile in <email> e <password>.
```

L'agente ti chiederà le credenziali e le configurerà. Una volta installato, l'autenticazione
avviene automaticamente — non serve chiamare nessun tool di login.

## Tool disponibili

| Tool | Descrizione |
|------|-------------|
| `totomondiale_get_formation` | Leggi la tua formazione completa (gironi, qualificazioni, special bets, Pt) |
| `totomondiale_list_matches` | Elenca tutti i match ID organizzati per girone |
| `totomondiale_list_teams` | Elenca tutte le squadre con nome e ID |
| `totomondiale_list_players` | Classifica giocatori con posizione e punti |
| `totomondiale_get_player_formation` | Leggi la schedina di un altro giocatore (username dalla classifica) |
| `totomondiale_submit_group_bets` | Invia pronostici per un girone (6 risultati + prolifico) |
| `totomondiale_submit_qualification` | Invia le squadre qualificate per una fase a eliminazione |
| `totomondiale_submit_special_bets` | Invia pronostici speciali (vincitore + capocannoniere) |
| `totomondiale_submit_prolific_total` | Invia la partita più prolifica del torneo (Pt) |

## Esempi di utilizzo

```
> qual è la mia formazione attuale?

> invia i pronostici per il girone A: 2-1, 1-1, 3-0, 0-2, 1-0, 2-2 con prolifico match 2

> chi è in testa alla classifica?

> fammi vedere la schedina di ArtuMazz
```
