"""
Abstracte basisklasse voor alle Prosperia V2 trading-plugins.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from core.mt5_client import Mt5Client
from core.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """De blauwdruk voor elke trading-strategie."""

    def __init__(self, config: StrategyConfig, mt5: Mt5Client) -> None:
        self.config = config
        self.mt5 = mt5
        self.logger = logging.getLogger(f"plugin.{self.config.plugin}.{self.config.id}")
        self.is_active = False

    def initialize(self) -> None:
        self.logger.info("Plugin geïnitialiseerd voor %s %s (account %d)",
                         self.config.symbol, self.config.timeframe,
                         self.config.account_id or 0)
        self.is_active = True

    def shutdown(self) -> None:
        self.logger.info("Plugin gestopt.")
        self.is_active = False

    @abstractmethod
    def on_tick(self, tick: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def on_bar(self, bar: Dict[str, Any]) -> None:
        pass

    def on_config_update(self, new_config: StrategyConfig) -> None:
        self.logger.info("Configuratie bijgewerkt via hot-reload.")
        self.config = new_config
