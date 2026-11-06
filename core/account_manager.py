"""
Account Manager voor Prosperia V2.

Beheert de Mt5Client-verbindingen per account. Synchroniseert met de database:
- Nieuwe accounts → verbinden
- Uitgezette accounts → verbreken
- Gewijzigde host/poort → reconnect
"""

from __future__ import annotations

import logging

from core.account_config import AccountConfig
from core.mt5_client import Mt5Client, Mt5Error

logger = logging.getLogger(__name__)


class AccountManager:
    """Beheert alle actieve Mt5Client-verbindingen."""

    def __init__(self) -> None:
        self._clients: dict[int, Mt5Client] = {}       # account_id -> Mt5Client
        self._configs: dict[int, AccountConfig] = {}   # account_id -> laatste config

    # ------------------------------------------------------------------ sync

    def sync(self, accounts: list[AccountConfig]) -> None:
        """
        Synchroniseert de actieve verbindingen met de opgegeven account-lijst.
        Wordt aangeroepen bij elke hot-reload cyclus.
        """
        target = {a.id: a for a in accounts if a.enabled}
        active_ids = set(self._clients.keys())
        target_ids = set(target.keys())

        # 1. Verbroken accounts (uitgezet of verwijderd)
        for aid in active_ids - target_ids:
            self._disconnect(aid)

        # 2. Nieuwe accounts
        for aid in target_ids - active_ids:
            self._connect(target[aid])

        # 3. Gewijzigde accounts (host/poort veranderd)
        for aid in active_ids & target_ids:
            old = self._configs.get(aid)
            new = target[aid]
            if old and (old.bridge_host != new.bridge_host or old.bridge_port != new.bridge_port):
                logger.info("Account '%s' bridge is gewijzigd, reconnect...", new.name)
                self._disconnect(aid)
                self._connect(new)

    # -------------------------------------------------------------- internals

    def _connect(self, config: AccountConfig) -> None:
      try:
          client = Mt5Client(host=config.bridge_host, port=config.bridge_port)
          client.connect()
          self._clients[config.id] = client
          self._configs[config.id] = config
      except Mt5Error as e:
          logger.error("DEBUG: Kon account '%s' niet verbinden: %s", config.name, e)

    def _disconnect(self, account_id: int) -> None:
        client = self._clients.pop(account_id, None)
        cfg = self._configs.pop(account_id, None)
        if client:
            logger.info("Account '%s' verbreken...", cfg.name if cfg else account_id)
            try:
                client.disconnect()
            except Exception as e:
                logger.error("Fout bij verbreken account %s: %s", account_id, e)

    # ------------------------------------------------------------------ access

    def get(self, account_id: int) -> Mt5Client | None:
        """Geeft de actieve Mt5Client voor een account, of None."""
        return self._clients.get(account_id)

    def all_clients(self) -> dict[int, Mt5Client]:
        """Alle actieve clients, keyed by account_id."""
        return dict(self._clients)

    def get_config(self, account_id: int) -> AccountConfig | None:
        """Geeft de laatste bekende config voor een account."""
        return self._configs.get(account_id)

    def list_active(self) -> list[AccountConfig]:
        """Geeft de configs van alle actief verbonden accounts."""
        return list(self._configs.values())

    def shutdown_all(self) -> None:
        """Verbindt alle clients netjes."""
        for aid in list(self._clients.keys()):
            self._disconnect(aid)
