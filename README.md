# Totomondiale MCP

MCP server per interagire con [Totomondiale](https://totomondiale.altervista.org) via AI agent.

Permette di leggere la propria formazione, vedere la classifica, consultare le schedine degli altri giocatori e inviare pronostici programmaticamente. L'autenticazione avviene automaticamente in background — le credenziali non vengono mai esposte al modello.

## Installazione

Copia e incolla questo prompt nel tuo AI agent:

```
Aggiungi al tuo file di configurazione opencode un MCP server di tipo "local" con:
- command: ["uvx", "--from", "git+https://github.com/alemazzo/totomondiale-mcp", "totomondiale-mcp"]
- environment: TOTOMONDIALE_EMAIL e TOTOMONDIALE_PASSWORD (chiedile all'utente)
- timeout: 30000
- NON fare override della configurazione esistente: estendila sempre, aggiungendo il server a quelli già presenti
- Installa il server globalmente, non a livello di progetto
```

L'agente ti chiederà le credenziali e le configurerà. Una volta installato, l'autenticazione
avviene automaticamente — non serve chiamare nessun tool di login.

Ecco come apparirà la configurazione in `opencode.json`:

```json
"mcp": {
  "totomondiale": {
    "type": "local",
    "command": ["uvx", "--from", "git+https://github.com/alemazzo/totomondiale-mcp", "totomondiale-mcp"],
    "enabled": true,
    "environment": {
      "TOTOMONDIALE_EMAIL": "la-tua-email@example.com",
      "TOTOMONDIALE_PASSWORD": "password"
    }
  }
},
"experimental": {
  "mcp_timeout": 30000
}
```

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
