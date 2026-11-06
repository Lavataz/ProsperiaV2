"""
Prosperia V2 Engine.

Twee hot-reload-cycli:
1. Accounts (welke brokers zijn actief?)
2. Strategieën (welke plugins draaien op welk account?)

Marktdata wordt per account opgehaald via de bijbehorende Mt5Client.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Any

from core.account_config import AccountConfigReader
from core.account_manager import AccountManager
from core.api_client import ProsperiaApiClient
from core.strategy_config import StrategyConfig, StrategyConfigReader
from core.strategy_loader import StrategyLoader
from core.strategy_base import StrategyBase

logger = logging.getLogger(__name__)


class Engine:
    """De hoofdloop voor alle trading-strategieën."""

    def __init__(
        self,
        api: ProsperiaApiClient,
        account_reader: AccountConfigReader,
        account_manager: AccountManager,
        config_reader: StrategyConfigReader,
        loader: StrategyLoader,
        *,
        poll_interval: float = 5.0,
        config_refresh_interval: float = 30.0,
    ) -> None:
        self._api = api
        self._account_reader = account_reader
        self._account_manager = account_manager
        self._config_reader = config_reader
        self._loader = loader
        self._poll_interval = poll_interval
        self._config_refresh_interval = config_refresh_interval

        # (account_id, strategy_id) -> plugin instance
        self._active_plugins: Dict[tuple[int, int], StrategyBase] = {}
        # (account_id, symbol) -> laatste bar-timestamp (per timeframe)
        self._last_bar_time: Dict[tuple[int, str, str], int] = {}

        self._running = False
        self._last_config_refresh = time.time()

    # -------------------------------------------------------------- start/stop

    def start(self) -> None:
        logger.info("Engine start...")
        self._running = True
        self._sync_all(force=True)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Engine gestopt door gebruiker (Ctrl+C).")
        finally:
            self.stop()

    def stop(self) -> None:
        if not self._running:
            return
        logger.info("Engine stopt...")
        self._running = False
        for key, plugin in list(self._active_plugins.items()):
            try:
                plugin.shutdown()
            except Exception as e:
                logger.error("Fout bij afsluiten plugin %s: %s", plugin.config.name, e)
        self._active_plugins.clear()
        self._account_manager.shutdown_all()

    # -------------------------------------------------------------- main loop

    def _main_loop(self) -> None:
        while self._running:
            now = time.time()

            if now - self._last_config_refresh >= self._config_refresh_interval:
                self._sync_all()
                self._last_config_refresh = now

            self._poll_market_data()
            time.sleep(self._poll_interval)

    # -------------------------------------------------------------- sync

    def _sync_all(self, force: bool = False) -> None:
        # 1. Accounts
        if not force:
            logger.debug("Checking account updates...")
        accounts = self._account_reader.get_all(force=True)
        self._account_manager.sync(accounts)

        # 2. Strategieën
        self._sync_strategies()

    def _sync_strategies(self) -> None:
        configs = self._config_reader.get_all(force=True)
        enabled_configs = [c for c in configs if c.enabled]

        # Alleen strategieën met een geldig, online account
        valid: list[StrategyConfig] = []
        for cfg in enabled_configs:
            if cfg.account_id is None:
                logger.warning("Strategie '%s' heeft geen account_id, overslaan.", cfg.name)
                continue
            if self._account_manager.get(cfg.account_id) is None:
                logger.warning("Strategie '%s' verwijst naar offline account %d, overslaan.",
                               cfg.name, cfg.account_id)
                continue
            valid.append(cfg)

        target_keys = {(cfg.account_id, cfg.id) for cfg in valid}
        active_keys = set(self._active_plugins.keys())

        # Stoppen
        for key in active_keys - target_keys:
            plugin = self._active_plugins.pop(key)
            logger.info("Hot-Reload: strategie '%s' gestopt.", plugin.config.name)
            try:
                plugin.shutdown()
            except Exception as e:
                logger.error("Fout bij stoppen plugin %s: %s", plugin.config.name, e)

        # Starten
        for cfg in valid:
            key = (cfg.account_id, cfg.id)
            if key not in self._active_plugins:
                self._start_plugin(cfg)

        # Updaten (params gewijzigd)
        for cfg in valid:
            key = (cfg.account_id, cfg.id)
            plugin = self._active_plugins.get(key)
            if plugin and plugin.config.params != cfg.params:
                logger.info("Hot-Reload: configuratie van '%s' gewijzigd.", cfg.name)
                try:
                    plugin.on_config_update(cfg)
                except Exception as e:
                    logger.error("Fout bij update plugin %s: %s", cfg.name, e)

    def _start_plugin(self, config: StrategyConfig) -> None:
        mt5 = self._account_manager.get(config.account_id)
        if mt5 is None:
            logger.error("Geen Mt5Client voor account %d", config.account_id)
            return

        instance = self._loader.create_instance(config, mt5)
        if instance:
            try:
                instance.initialize()
                self._active_plugins[(config.account_id, config.id)] = instance
            except Exception as e:
                logger.error("Fout bij initialiseren plugin '%s': %s", config.name, e)

    # -------------------------------------------------------------- market data

    def _poll_market_data(self) -> None:
        # Groepeer plugins per account
        by_account: Dict[int, list[StrategyBase]] = {}
        for (aid, _sid), plugin in self._active_plugins.items():
            by_account.setdefault(aid, []).append(plugin)

        for account_id, plugins in by_account.items():
            mt5 = self._account_manager.get(account_id)
            if mt5 is None:
                continue

            # Unieke symbolen voor dit account
            symbols = {p.config.symbol for p in plugins if p.config.symbol}

            for symbol in symbols:
                try:
                    tick = mt5.get_tick(symbol)
                    for plugin in plugins:
                        if plugin.config.symbol == symbol:
                            try:
                                plugin.on_tick(tick)
                            except Exception as e:
                                logger.error("Plugin '%s' crashte in on_tick: %s",
                                             plugin.config.name, e)

                    timeframes = {p.config.timeframe for p in plugins
                                  if p.config.symbol == symbol}
                    for tf in timeframes:
                        bars = mt5.get_bars(symbol, tf, count=2)
                        if len(bars) < 2:
                            continue
                        closed = bars[-2]
                        key = (account_id, symbol, tf)
                        if closed["time"] > self._last_bar_time.get(key, 0):
                            self._last_bar_time[key] = closed["time"]
                            for plugin in plugins:
                                if (plugin.config.symbol == symbol and
                                    plugin.config.timeframe == tf):
                                    try:
                                        plugin.on_bar(closed)
                                    except Exception as e:
                                        logger.error("Plugin '%s' crashte in on_bar: %s",
                                                     plugin.config.name, e)
                except Exception as e:
                    logger.error("Fout bij marktdata voor account %d / %s: %s",
                                 account_id, symbol, e)
