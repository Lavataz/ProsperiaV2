# Prosperia V2

Modulair trading-systeem met plugin-strategieën, database-gedreven configuratie en hot-reload.

## Structuur
- `core/` — bot-engine
- `strategies/` — plugins (alleen code)
- `api/` — API voor website
- `installer/` — installatie & migratie
- `tests/` — unit + integratie
- `config/` — alleen DB-credentials

## Quick start
```bash
cd /opt/ProsperiaV2
source venv313/bin/activate
python -m core.engine
Documentatie
Zie CHANGELOG.md voor versiehistorie.
