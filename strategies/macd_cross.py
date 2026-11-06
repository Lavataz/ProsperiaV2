"""
MACD Cross Strategy voor Prosperia V2.

Signaal: MACD-lijn kruist signaallijn.
- Bullish cross (MACD > Signal) → BUY
- Bearish cross (MACD < Signal) → SELL

Risk management:
- 1% van balance per trade
- SL = 1.5 × ATR(14)
- TP = 2 × SL (Risk:Reward = 1:2)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from core.strategy_base import StrategyBase


class MacdCrossStrategy(StrategyBase):
    """MACD Cross trading-strategie."""

    def __init__(self, config, mt5) -> None:
        super().__init__(config, mt5)

        # MACD parameters
        self.fast_period: int = int(self.config.params.get("fast", 12))
        self.slow_period: int = int(self.config.params.get("slow", 26))
        self.signal_period: int = int(self.config.params.get("signal", 9))

        # ATR parameter
        self.atr_period: int = int(self.config.params.get("atr_period", 14))

        # Risk management parameters
        self.risk_percent: float = float(self.config.params.get("risk_percent", 1.0))
        self.sl_atr_multiplier: float = float(self.config.params.get("sl_atr_multiplier", 1.5))
        self.tp_atr_multiplier: float = float(self.config.params.get("tp_atr_multiplier", 3.0))
        self.magic: int = int(self.config.params.get("magic", 1001))
        
        # Veiligheidslimieten
        self.max_volume: float = float(self.config.params.get("max_volume", 2.0))
        self.min_sl_pips: float = float(self.config.params.get("min_sl_pips", 10.0))

        # Interne state
        self._last_bar_time: Optional[int] = None
        self._last_signal: Optional[str] = None  # 'buy', 'sell' of None

    def initialize(self) -> None:
        super().initialize()
        self.logger.info(
            "MACD Cross gestart: fast=%d, slow=%d, signal=%d, ATR=%d, risk=%.2f%%",
            self.fast_period, self.slow_period, self.signal_period,
            self.atr_period, self.risk_percent,
        )
        # Controleer of we al een open positie hebben voor deze magic
        positions = self.mt5.get_positions(self.config.symbol)
        ours = [p for p in positions if p.get("magic") == self.magic]
        if ours:
            self.logger.info("Bestaande positie(s) gevonden: %d", len(ours))

    def on_tick(self, tick: Dict[str, Any]) -> None:
        # We handelen alleen op bar-close
        pass

    def on_bar(self, bar: Dict[str, Any]) -> None:
        """Wordt aangeroepen bij elke afgesloten candle."""
        bar_time = int(bar["time"])
        if self._last_bar_time is not None and bar_time <= self._last_bar_time:
            return  # Al verwerkt
        self._last_bar_time = bar_time

        # 1. Haal voldoende bars op voor MACD + ATR
        needed = max(self.slow_period, self.atr_period) + 20
        bars = self.mt5.get_bars(self.config.symbol, self.config.timeframe, count=needed)
        if len(bars) < self.slow_period + self.signal_period + 2:
            self.logger.warning("Onvoldoende bars: %d", len(bars))
            return

        # 2. Bereken indicatoren
        df = pd.DataFrame(bars)
        df["macd"], df["signal"] = self._calc_macd(df["close"])
        df["atr"] = self._calc_atr(df, self.atr_period)

        # 3. Detecteer cross (laatste twee bars)
        if len(df) < 3:
            return
        prev = df.iloc[-3]  # bar vóór laatste
        last = df.iloc[-2]  # laatste afgesloten bar

        if pd.isna(prev["macd"]) or pd.isna(prev["signal"]):
            return

        bullish_cross = prev["macd"] <= prev["signal"] and last["macd"] > last["signal"]
        bearish_cross = prev["macd"] >= prev["signal"] and last["macd"] < last["signal"]

         # TIJDELIJK VOOR TEST
 #       bullish_cross = False
 #       bearish_cross = True
        
        # 4. Check of we al een positie hebben
        positions = self.mt5.get_positions(self.config.symbol)
        ours = [p for p in positions if p.get("magic") == self.magic]
        if ours:
            self.logger.debug("Open positie aanwezig, geen nieuwe entry.")
            return

        # 5. Genereer signaal
        if bullish_cross:
            self.logger.info("BULLISH CROSS: MACD=%.5f > Signal=%.5f", last["macd"], last["signal"])
            self._open_trade("buy", float(last["atr"]), float(last["close"]))
        elif bearish_cross:
            self.logger.info("BEARISH CROSS: MACD=%.5f < Signal=%.5f", last["macd"], last["signal"])
            self._open_trade("sell", float(last["atr"]), float(last["close"]))

    # --------------------------------------------------------------- helpers

    @staticmethod
    def _calc_macd(closes: pd.Series) -> tuple[pd.Series, pd.Series]:
        """Berekent MACD-lijn en signaallijn."""
        ema_fast = closes.ewm(span=12, adjust=False).mean()
        ema_slow = closes.ewm(span=26, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    @staticmethod
    def _calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
        """Berekent Average True Range."""
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=period, adjust=False).mean()

    def _open_trade(self, direction: str, atr: float, price: float) -> None:
        """Berekent lotgrootte op basis van risico, en plaatst de order."""
        if atr <= 0:
            self.logger.warning("ATR is 0, geen trade.")
            return

        # SL/TP afstanden in prijs
 #       sl_distance = atr * self.sl_atr_multiplier
 #       tp_distance = atr * self.tp_atr_multiplier

        # Minimum SL-afstand (in prijs) om te voorkomen dat trades te krap worden
        min_sl_distance = self.min_sl_pips / 10000.0
        
        sl_distance = max(atr * self.sl_atr_multiplier, min_sl_distance)
        tp_distance = sl_distance * 2.0  # Risk:Reward = 1:2

        # SL/TP prijzen
        if direction == "buy":
            sl = price - sl_distance
            tp = price + tp_distance
        else:
            sl = price + sl_distance
            tp = price - tp_distance

        # Bereken lotgrootte op basis van risico %
        account = self.mt5.get_account_info()
        balance = float(account["balance"])
        risk_amount = balance * (self.risk_percent / 100.0)

        # Pip-waarde bepalen (vereenvoudigd voor EURUSD: 1 lot = $10 per pip)
        # sl_distance in prijs -> pips = sl_distance * 10000 (voor 4-decimal paren)
        sl_pips = sl_distance * 10000
        if sl_pips <= 0:
            self.logger.warning("SL-afstand is 0, geen trade.")
            return

        # Lot = risk_amount / (sl_pips * pip_value_per_lot)
        # Voor EURUSD: pip_value ≈ $10 per lot
        pip_value = 10.0
        volume = risk_amount / (sl_pips * pip_value)

        # Afronden op 0.01 lot
        volume = round(volume, 2)

        # Minimum/maximum controle
        if volume < 0.01:
            self.logger.warning("Berekende volume te klein: %.4f (SL pips: %.1f)", volume, sl_pips)
            return
        if volume > self.max_volume:
            self.logger.warning("Volume gekapt op %.2f lot (was %.2f)", self.max_volume, volume)
            volume = self.max_volume

        # Plaats order
        try:
            result = self.mt5.place_order(
                symbol=self.config.symbol,
                order_type=direction,
                volume=volume,
                sl=sl,
                tp=tp,
                comment=f"MACD {direction.upper()}",
                magic=self.magic,
            )
            self.logger.info(
                "ORDER GEOPEND: %s %.2f lot @ %.5f (SL=%.5f, TP=%.5f, ticket=%d)",
                direction.upper(), volume, price, sl, tp, result["ticket"],
            )
            self._last_signal = direction
        except Exception as e:
            self.logger.error("Fout bij plaatsen order: %s", e)

        def on_config_update(self, new_config) -> None:
            super().on_config_update(new_config)
            # Herbereken parameters uit de nieuwe config
            self.fast_period = int(self.config.params.get("fast", 12))
            self.slow_period = int(self.config.params.get("slow", 26))
            self.signal_period = int(self.config.params.get("signal", 9))
            self.atr_period = int(self.config.params.get("atr_period", 14))
            self.risk_percent = float(self.config.params.get("risk_percent", 1.0))
            self.sl_atr_multiplier = float(self.config.params.get("sl_atr_multiplier", 1.5))
            self.tp_atr_multiplier = float(self.config.params.get("tp_atr_multiplier", 3.0))
            self.max_volume = float(self.config.params.get("max_volume", 2.0))
            self.min_sl_pips = float(self.config.params.get("min_sl_pips", 10.0))
            self.logger.info("MACD Cross config bijgewerkt.")