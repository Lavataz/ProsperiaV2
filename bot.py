"""
Prosperia V2 — entrypoint.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from core.account_config import AccountConfigReader
from core.account_manager import AccountManager
from core.api_client import ApiError, ProsperiaApiClient
from core.engine import Engine
from core.logging_setup import setup_logging
from core.strategy_config import StrategyConfigReader
from core.strategy_loader import StrategyLoader


def main() -> int:
    load_dotenv()
    setup_logging(level=os.getenv("PROSPERIA_LOG_LEVEL", "INFO"))

    required = ("PROSPERIA_API_URL", "PROSPERIA_API_USER", "PROSPERIA_API_PASS")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Ontbrekende env-variabelen: {', '.join(missing)}", file=sys.stderr)
        return 1

    api = ProsperiaApiClient(
        base_url=os.environ["PROSPERIA_API_URL"],
        username=os.environ["PROSPERIA_API_USER"],
        password=os.environ["PROSPERIA_API_PASS"],
    )

    account_reader = AccountConfigReader(api)
    account_manager = AccountManager()
    config_reader = StrategyConfigReader(api)
    loader = StrategyLoader(strategies_dir="strategies")

    try:
        api.login()
    except ApiError as exc:
        print(f"Login mislukt: {exc}", file=sys.stderr)
        return 2

    engine = Engine(
        api=api,
        account_reader=account_reader,
        account_manager=account_manager,
        config_reader=config_reader,
        loader=loader,
        poll_interval=float(os.getenv("PROSPERIA_POLL_INTERVAL", 5)),
        config_refresh_interval=float(os.getenv("PROSPERIA_CONFIG_REFRESH_INTERVAL", 30)),
    )
    try:
        engine.start()
    except Exception as e:
        print(f"Fout in de Engine: {e}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
