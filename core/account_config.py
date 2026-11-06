"""
Leest account-configuraties uit de database (via de API) en stelt ze
beschikbaar aan de AccountManager.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator

from core.api_client import ApiError, ProsperiaApiClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AccountConfig:
    """Één broker/prop-account uit de database."""

    id: int
    name: str
    mt5_login: int
    mt5_server: str
    bridge_host: str
    bridge_port: int
    enabled: bool
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "AccountConfig":
        return cls(
            id=int(data["id"]),
            name=data.get("name") or f"account-{data.get('id')}",
            mt5_login=int(data.get("mt5_login", 0)),
            mt5_server=data.get("mt5_server", ""),
            bridge_host=data.get("bridge_host", "127.0.0.1"),
            bridge_port=int(data.get("bridge_port", 18812)),
            enabled=bool(data.get("enabled", True)),
            raw=data,
        )


class AccountConfigReader:
    """Haalt account_configs op via de API, met korte cache."""

    def __init__(self, api: ProsperiaApiClient, *, cache_ttl: float = 30.0) -> None:
        self._api = api
        self._cache_ttl = cache_ttl
        self._cache: list[AccountConfig] | None = None
        self._cache_at: float = 0.0

    def get_all(self, *, force: bool = False) -> list[AccountConfig]:
        if not force and self._is_cache_valid():
            return list(self._cache or [])

        try:
            raw = self._api.post("/index.php", payload={"action": "accounts_list"})
        except ApiError as exc:
            logger.error("Kon accounts niet ophalen: %s", exc)
            return list(self._cache or [])

        items = raw.get("accounts", raw) if isinstance(raw, dict) else raw
        if not isinstance(items, list):
            logger.error("Onverwacht API-antwoord voor accounts: %r", raw)
            return list(self._cache or [])

        configs = [AccountConfig.from_api(item) for item in items]
        self._cache = configs
        self._cache_at = time.time()
        logger.debug("%d accounts geladen", len(configs))
        return list(configs)

    def get_enabled(self, *, force: bool = False) -> list[AccountConfig]:
        return [a for a in self.get_all(force=force) if a.enabled]

    def get_by_id(self, account_id: int) -> AccountConfig | None:
        for cfg in self.get_all():
            if cfg.id == account_id:
                return cfg
        return None

    def iter_accounts(self) -> Iterator[AccountConfig]:
        yield from self.get_enabled()

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and (time.time() - self._cache_at) < self._cache_ttl
