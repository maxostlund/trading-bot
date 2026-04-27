from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass
class RiskSettings:
    max_position_pct: float = 0.10          # max 10% av kontot i en position
    max_total_exposure_pct: float = 0.30    # max 30% av kontot investerat totalt
    max_risk_per_trade_pct: float = 0.01    # max 1% av kontot riskeras per trade
    stop_loss_pct: float = 0.02             # stop loss 2% under entry
    take_profit_pct: float = 0.04           # take profit 4% över entry
    max_daily_loss_pct: float = 0.03        # stoppa trading vid -3% daglig förlust
    max_open_positions: int = 3
    max_trades_per_day: int = 5
    cooldown_after_trade_minutes: int = 10
    cooldown_after_loss_minutes: int = 30
    min_cash_pct: float = 0.05              # behåll minst 5% cash
    max_price_age_seconds: int = 60


class RiskManager:
    def __init__(self, settings: RiskSettings | None = None):
        self.settings = settings or RiskSettings()
        self.trades_today = 0
        self.last_trade_time = None
        self.last_loss_time = None
        self.starting_equity_today = None

    def set_starting_equity(self, equity: float):
        if self.starting_equity_today is None:
            self.starting_equity_today = equity

    def market_is_open(self, client) -> bool:
        clock = client.get_clock()
        return bool(clock.is_open)

    def validate_price(self, price: float) -> bool:
        return price is not None and price > 0

    def validate_price_timestamp(self, price_timestamp: datetime | None) -> bool:
        if price_timestamp is None:
            return True

        now = datetime.now(timezone.utc)

        if price_timestamp.tzinfo is None:
            price_timestamp = price_timestamp.replace(tzinfo=timezone.utc)

        age = (now - price_timestamp).total_seconds()
        return age <= self.settings.max_price_age_seconds

    def get_equity(self, client) -> float:
        account = client.get_account()
        return float(account.equity)

    def get_cash(self, client) -> float:
        account = client.get_account()
        return float(account.cash)

    def get_daily_pnl_pct(self, current_equity: float) -> float:
        if self.starting_equity_today is None:
            self.starting_equity_today = current_equity
            return 0.0

        return (current_equity - self.starting_equity_today) / self.starting_equity_today

    def daily_loss_limit_hit(self, current_equity: float) -> bool:
        daily_pnl_pct = self.get_daily_pnl_pct(current_equity)
        return daily_pnl_pct <= -self.settings.max_daily_loss_pct

    def get_open_positions(self, client):
        return client.get_all_positions()

    def has_position(self, client, symbol: str) -> bool:
        positions = self.get_open_positions(client)
        return any(p.symbol == symbol for p in positions)

    def max_open_positions_hit(self, client) -> bool:
        positions = self.get_open_positions(client)
        return len(positions) >= self.settings.max_open_positions

    def get_total_exposure(self, client) -> float:
        positions = self.get_open_positions(client)

        total = 0.0
        for position in positions:
            total += abs(float(position.market_value))

        return total

    def total_exposure_limit_hit(self, client, new_position_value: float) -> bool:
        equity = self.get_equity(client)
        current_exposure = self.get_total_exposure(client)

        max_allowed = equity * self.settings.max_total_exposure_pct

        return current_exposure + new_position_value > max_allowed

    def cash_buffer_ok(self, client, new_position_value: float) -> bool:
        equity = self.get_equity(client)
        cash = self.get_cash(client)

        min_cash = equity * self.settings.min_cash_pct

        return cash - new_position_value >= min_cash

    def trade_limit_hit(self) -> bool:
        return self.trades_today >= self.settings.max_trades_per_day

    def in_cooldown(self) -> bool:
        now = datetime.now(timezone.utc)

        if self.last_loss_time is not None:
            loss_cooldown = timedelta(minutes=self.settings.cooldown_after_loss_minutes)
            if now - self.last_loss_time < loss_cooldown:
                return True

        if self.last_trade_time is not None:
            trade_cooldown = timedelta(minutes=self.settings.cooldown_after_trade_minutes)
            if now - self.last_trade_time < trade_cooldown:
                return True

        return False

    def calculate_position_size(self, account_equity: float, entry_price: float) -> int:
        max_position_value = account_equity * self.settings.max_position_pct
        qty = int(max_position_value / entry_price)
        return max(qty, 0)

    def calculate_position_size_by_risk(self, account_equity: float, entry_price: float, stop_loss_price: float) -> int:
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            return 0

        max_risk_dollars = account_equity * self.settings.max_risk_per_trade_pct
        qty = int(max_risk_dollars / risk_per_share)

        return max(qty, 0)

    def calculate_qty(self, account_equity: float, entry_price: float) -> int:
        stop_loss_price = self.get_stop_loss_price(entry_price)

        qty_by_position_size = self.calculate_position_size(account_equity, entry_price)
        qty_by_risk = self.calculate_position_size_by_risk(
            account_equity=account_equity,
            entry_price=entry_price,
            stop_loss_price=stop_loss_price
        )

        return min(qty_by_position_size, qty_by_risk)

    def get_stop_loss_price(self, entry_price: float) -> float:
        return round(entry_price * (1 - self.settings.stop_loss_pct), 2)

    def get_take_profit_price(self, entry_price: float) -> float:
        return round(entry_price * (1 + self.settings.take_profit_pct), 2)

    def approve_trade(self, client, symbol: str, price: float, price_timestamp: datetime | None = None):
        if not self.market_is_open(client):
            return False, "Market is closed"

        if not self.validate_price(price):
            return False, "Invalid price"

        if not self.validate_price_timestamp(price_timestamp):
            return False, "Price data is stale"

        equity = self.get_equity(client)
        self.set_starting_equity(equity)

        if self.daily_loss_limit_hit(equity):
            return False, "Daily loss limit hit"

        if self.trade_limit_hit():
            return False, "Max trades per day hit"

        if self.in_cooldown():
            return False, "Bot is in cooldown"

        if self.has_position(client, symbol):
            return False, f"Already have position in {symbol}"

        if self.max_open_positions_hit(client):
            return False, "Max open positions hit"

        qty = self.calculate_qty(equity, price)

        if qty <= 0:
            return False, "Calculated qty is 0"

        new_position_value = qty * price

        if self.total_exposure_limit_hit(client, new_position_value):
            return False, "Total exposure limit hit"

        if not self.cash_buffer_ok(client, new_position_value):
            return False, "Cash buffer too low"

        return True, {
            "symbol": symbol,
            "qty": qty,
            "entry_price": price,
            "stop_loss_price": self.get_stop_loss_price(price),
            "take_profit_price": self.get_take_profit_price(price),
            "position_value": new_position_value,
        }

    def record_trade(self, was_loss: bool = False):
        now = datetime.now(timezone.utc)
        self.trades_today += 1
        self.last_trade_time = now

        if was_loss:
            self.last_loss_time = now

    def reset_daily_counters(self):
        self.trades_today = 0
        self.starting_equity_today = None