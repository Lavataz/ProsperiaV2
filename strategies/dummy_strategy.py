"""Test plugin om de StrategyLoader te valideren."""
from typing import Any, Dict
from core.strategy_base import StrategyBase


class DummyStrategy(StrategyBase):
    def initialize(self) -> None:
        super().initialize()
        self.logger.info("DummyStrategy klaar. Params: %s", self.config.params)

    def on_tick(self, tick: Dict[str, Any]) -> None:
        pass

    def on_bar(self, bar: Dict[str, Any]) -> None:
        pass
