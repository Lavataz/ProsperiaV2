"""
Status Reporter voor Prosperia V2.
Stuurt periodiek een hartslag en status naar de API.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING

from core.api_client import ApiError, ProsperiaApiClient

if TYPE_CHECKING:
    from core.engine import Engine

logger = logging.getLogger(__name__)


class StatusReporter:
    def __init__(self, api: ProsperiaApiClient, engine: "Engine", *, interval: float = 60.0, warmup_delay: float = 15.0):
        self._api = api
        self._engine = engine
        self._interval = interval
        self._warmup_delay = warmup_delay  # Wacht 15s na start, tot engine klaar is
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="StatusReporter")
        self._thread.start()
        logger.info("StatusReporter gestart (interval=%ds, warmup=%ds)", self._interval, self._warmup_delay)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("StatusReporter gestopt.")

    def _loop(self) -> None:
        # Wacht tot de engine klaar is met opstarten
        logger.debug("StatusReporter wacht %.0fs op engine-warmup...", self._warmup_delay)
        for _ in range(int(self._warmup_delay)):
            if not self._running:
                return
            time.sleep(1)

        while self._running:
            try:
                self._report()
            except Exception as e:
                logger.error("Fout bij status-report: %s", e)
            
            for _ in range(int(self._interval)):
                if not self._running:
                    return
                time.sleep(1)

    def _report(self) -> None:
        # Tel actieve plugins
        active_plugins = len(self._engine._active_plugins)
        
        # Tel open posities over alle accounts
        open_positions = 0
        total_balance = 0.0
        total_equity = 0.0
        accounts_counted = 0

        for client in self._engine._account_manager.all_clients().values():
            try:
                positions = client.get_positions()
                open_positions += len(positions)
                
                acc_info = client.get_account_info()
                total_balance += float(acc_info["balance"])
                total_equity += float(acc_info["equity"])
                accounts_counted += 1
            except Exception as e:
                logger.debug("Kon account-info niet ophalen: %s", e)

        payload = {
            "action": "status_update",
            "active_strategies": active_plugins,
            "open_positions": open_positions,
            "account_balance": total_balance if accounts_counted > 0 else None,
            "account_equity": total_equity if accounts_counted > 0 else None,
        }

        try:
            self._api.post("/index.php", payload=payload)
            logger.info("Status gerapporteerd: %d plugins, %d posities, saldo $%.2f", 
                        active_plugins, open_positions, total_balance)
        except ApiError as e:
            logger.warning("Kon status niet naar API sturen: %s", e)
