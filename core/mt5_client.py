"""
MT5 Client wrapper voor Prosperia V2.

Verbindt via mt5linux met de MT5-terminal op een externe Windows-machine.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from mt5linux import MetaTrader5

logger = logging.getLogger(__name__)


class Mt5Error(Exception):
    """Fout bij communicatie met MT5."""


class Mt5Client:
    """Wrapper om de MT5-terminal via mt5linux."""

    # MT5 timeframe constanten (voor het gemak)
    TIMEFRAMES = {
        "M1": MetaTrader5.TIMEFRAME_M1,
        "M5": MetaTrader5.TIMEFRAME_M5,
        "M15": MetaTrader5.TIMEFRAME_M15,
        "M30": MetaTrader5.TIMEFRAME_M30,
        "H1": MetaTrader5.TIMEFRAME_H1,
        "H4": MetaTrader5.TIMEFRAME_H4,
        "D1": MetaTrader5.TIMEFRAME_D1,
    }

    def __init__(self, host: str, port: int = 18812) -> None:
        self.host = host
        self.port = port
        self._mt5: MetaTrader5 | None = None

    # ---------------------------------------------------------------- connect

    def connect(self) -> None:
        """Maak verbinding met de MT5-terminal via de bridge."""
        logger.info("Verbinden met MT5-bridge op %s:%d", self.host, self.port)
        self._mt5 = MetaTrader5(host=self.host, port=self.port)
        if not self._mt5.initialize():
            err = self._mt5.last_error()
            raise Mt5Error(f"MT5 initialize mislukt: {err}")

        info = self._mt5.terminal_info()
        logger.info(
            "Verbonden met MT5: %s (build %s), broker-connected=%s",
            info.name, info.build, info.connected,
        )

    def disconnect(self) -> None:
        """Sluit de verbinding netjes af."""
        if self._mt5:
            self._mt5.shutdown()
            logger.info("MT5 verbinding gesloten.")
        self._mt5 = None

    def _ensure_connected(self) -> MetaTrader5:
        if self._mt5 is None:
            raise Mt5Error("MT5 client is niet verbonden. Roep eerst connect() aan.")
        return self._mt5

    # ------------------------------------------------------------- market data

    def get_tick(self, symbol: str) -> dict[str, Any]:
        """Haal de laatste tick op voor een symbool."""
        mt5 = self._ensure_connected()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise Mt5Error(f"Geen tick voor {symbol}: {mt5.last_error()}")
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "time": tick.time,
        }

    def get_bars(self, symbol: str, timeframe: str, count: int = 100) -> list[dict[str, Any]]:
        """Haal de laatste N bars op voor een symbool en timeframe."""
        mt5 = self._ensure_connected()
        tf = self.TIMEFRAMES.get(timeframe)
        if tf is None:
            raise Mt5Error(f"Onbekend timeframe: {timeframe}")

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None or len(rates) == 0:
            raise Mt5Error(f"Geen bars voor {symbol} {timeframe}: {mt5.last_error()}")

        return [
            {
                "time": int(r["time"]),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
                "volume": int(r["tick_volume"]),
            }
            for r in rates
        ]

    # ---------------------------------------------------------------- orders

    def place_order(
        self,
        symbol: str,
        order_type: str,      # "buy" of "sell"
        volume: float,
        *,
        sl: float | None = None,
        tp: float | None = None,
        comment: str = "ProsperiaV2",
        magic: int = 0,
    ) -> dict[str, Any]:
        """Plaats een market order."""
        mt5 = self._ensure_connected()

        tick = self.get_tick(symbol)
        if order_type.lower() == "buy":
            price = tick["ask"]
            type_const = mt5.ORDER_TYPE_BUY
        elif order_type.lower() == "sell":
            price = tick["bid"]
            type_const = mt5.ORDER_TYPE_SELL
        else:
            raise Mt5Error(f"Onbekend order type: {order_type}")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": type_const,
            "price": float(price),
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        if sl:
            request["sl"] = float(sl)
        if tp:
            request["tp"] = float(tp)

        result = mt5.order_send(request)
        if result is None:
            raise Mt5Error(f"order_send gaf None: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            raise Mt5Error(f"Order mislukt: retcode={result.retcode}, comment={result.comment}")

        logger.info("Order geplaatst: %s %s %.2f @ %.5f (ticket %d)",
                    order_type.upper(), symbol, volume, price, result.order)
        return {
            "ticket": result.order,
            "price": result.price,
            "volume": result.volume,
            "retcode": result.retcode,
        }

    # ---------------------------------------------------------------- info

    def get_account_info(self) -> dict[str, Any]:
        mt5 = self._ensure_connected()
        info = mt5.account_info()
        if info is None:
            raise Mt5Error(f"Geen account info: {mt5.last_error()}")
        return {
            "login": info.login,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": info.margin_free,
            "currency": info.currency,
            "leverage": info.leverage,
        }

    def get_positions(self, symbol: str | None = None) -> list[dict[str, Any]]:
        mt5 = self._ensure_connected()
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        return [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "buy" if p.type == mt5.POSITION_TYPE_BUY else "sell",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "profit": p.profit,
                "comment": p.comment,
                "magic": p.magic,
            }
            for p in (positions or [])
        ]
