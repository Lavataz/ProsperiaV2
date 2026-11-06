"""
Leest strategy_configs uit de database (via de API) en stelt ze beschikbaar
aan de engine en de strategy loader.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from core.api_client import ApiError, ProsperiaApiClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyConfig:
    """Één strategie-record uit de database."""

    id: int
    name: str
    plugin: str
    enabled: bool
    symbol: str
    timeframe: str
    params: dict[str, Any] = field(default_factory=dict)
    account_id: int | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "StrategyConfig":
        params = data.get("params") or data.get("config") or data.get("parameters") or {}
        if isinstance(params, str):
            try:
                params = json.loads(params)
            except json.JSONDecodeError:
                logger.warning("Kon params van strategie %s niet parsen", data.get("id"))
                params = {}

        plugin = data.get("plugin") or data.get("strategy_type") or data.get("type") or ""

        return cls(
            id=int(data["id"]),
            name=data.get("name") or f"strategy-{data.get('id')}",
            plugin=plugin,
            enabled=bool(data.get("enabled", True)),
            symbol=data.get("symbol", ""),
            timeframe=data.get("timeframe", ""),
            params=params,
            account_id=data.get("account_id"),
            raw=data,
        )


class StrategyConfigReader:
    """Haalt strategy_configs op via de API, met korte cache voor hot-reload."""

    def __init__(self, api: ProsperiaApiClient, *, cache_ttl: float = 30.0) -> None:
        self._api = api
        self._cache_ttl = cache_ttl
        self._cache: list[StrategyConfig] | None = None
        self._cache_at: float = 0.0

    def get_all(self, *, force: bool = False) -> list[StrategyConfig]:
        if not force and self._is_cache_valid():
            return list(self._cache or [])

        try:
            # FIX: Gebruik POST in plaats van GET, omdat index.php JSON-bodies verwacht
            raw = self._api.post("/index.php", payload={"action": "list"})
        except ApiError as exc:
            logger.error("Kon strategieën niet ophalen: %s", exc)
            return list(self._cache or [])

        items = raw.get("strategies", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            logger.error("Onverwacht API-antwoord voor strategieën: %r", raw)
            return list(self._cache or [])

        configs = [StrategyConfig.from_api(item) for item in items]
        self._cache = configs
        self._cache_at = time.time()
        logger.debug("%d strategieën geladen", len(configs))
        return list(configs)

    def get_enabled(self, *, force: bool = False) -> list[StrategyConfig]:
        return [c for c in self.get_all(force=force) if c.enabled]

    def get_by_id(self, strategy_id: int) -> StrategyConfig | None:
        for cfg in self.get_all():
            if cfg.id == strategy_id:
                return cfg
        return None

    def iter_plugins(self) -> Iterator[StrategyConfig]:
        yield from self.get_enabled()

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and (time.time() - self._cache_at) < self._cache_ttl
