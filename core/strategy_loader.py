"""
Dynamische plugin loader voor Prosperia V2.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Type

from core.mt5_client import Mt5Client
from core.strategy_base import StrategyBase
from core.strategy_config import StrategyConfig

logger = logging.getLogger(__name__)


class StrategyLoader:
    def __init__(self, strategies_dir: str | Path = "strategies") -> None:
        self.strategies_dir = Path(strategies_dir)
        if not self.strategies_dir.exists():
            logger.warning("Strategies map '%s' bestaat niet. Deze wordt aangemaakt.", self.strategies_dir)
            self.strategies_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Type[StrategyBase]] = {}

    def load_class(self, plugin_name: str) -> Type[StrategyBase] | None:
        plugin_name = plugin_name.strip().lower()
        if plugin_name in self._cache:
            return self._cache[plugin_name]

        file_path = self.strategies_dir / f"{plugin_name}.py"
        if not file_path.exists():
            logger.error("Plugin bestand niet gevonden: %s", file_path)
            return None

        module_name = f"strategies.{plugin_name}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            logger.error("Kon module niet laden: %s", file_path)
            return None

        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as e:
            logger.exception("Fout bij inladen van plugin '%s': %s", plugin_name, e)
            return None

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, StrategyBase) and
                attr is not StrategyBase):
                self._cache[plugin_name] = attr
                logger.debug("Plugin klasse '%s' succesvol geladen.", attr.__name__)
                return attr

        logger.error("Geen geldige StrategyBase-subklasse gevonden in %s", file_path)
        return None

    def create_instance(self, config: StrategyConfig, mt5: Mt5Client) -> StrategyBase | None:
        if not config.plugin or config.plugin == "unknown":
            logger.error("Strategie '%s' heeft geen geldige plugin-naam in de database.", config.name)
            return None

        cls = self.load_class(config.plugin)
        if cls is None:
            return None

        try:
            return cls(config, mt5)
        except Exception as e:
            logger.exception("Fout bij aanmaken plugin instantie '%s': %s", config.plugin, e)
            return None
