# Prosperia V2

Modulair trading-systeem met plugin-strategieën, database-gedreven configuratie en hot-reload.

## Structuur
- `core/` — bot-engine
- `strategies/` — plugins (alleen code)
- `api/` — API voor website
- `installer/` — installatie & migratie
- `tests/` — unit + integratie
- `config/` — alleen DB-credentials

## Installatie (Raspberry Pi / VPS / WSL)

1. Clone de repository:
   `git clone https://github.com/Lavataz/ProsperiaV2.git /opt/ProsperiaV2`

2. Ga naar de map en voer het installatiescript uit:
   `cd /opt/ProsperiaV2`
   `chmod +x installer/install.sh`
   `./installer/install.sh`

3. Configureer de database:
   Pas de inloggegevens aan in `api/config/database.php` (of stel de omgevingsvariabelen `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS` in).

## Quick start (Bot starten)

`cd /opt/ProsperiaV2`
`source venv313/bin/activate`
`python -m core.engine`

## Documentatie
Zie `CHANGELOG.md` voor versiehistorie.
