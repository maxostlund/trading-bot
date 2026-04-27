from config import get_trading_client

from data.market_data import (
    get_historical_bars,
    get_latest_price_with_timestamp,
)

from strategy.rsi_bollinger import generate_signal

from risk.risk_manager import RiskManager, RiskSettings

from alpaca.trading.requests import (
    MarketOrderRequest,
    TakeProfitRequest,
    StopLossRequest,
)

from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderClass,
)


SYMBOL = "SPY"


def buy_with_bracket_order(client, trade_plan):
    order = MarketOrderRequest(
        symbol=trade_plan["symbol"],
        qty=trade_plan["qty"],
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
        order_class=OrderClass.BRACKET,
        take_profit=TakeProfitRequest(
            limit_price=trade_plan["take_profit_price"]
        ),
        stop_loss=StopLossRequest(
            stop_price=trade_plan["stop_loss_price"]
        ),
    )

    return client.submit_order(order)


def close_position_if_exists(client, symbol: str):
    try:
        positions = client.get_all_positions()
        has_position = any(position.symbol == symbol for position in positions)

        if not has_position:
            return False, f"Ingen öppen position i {symbol}"

        response = client.close_position(symbol)
        return True, response

    except Exception as e:
        return False, str(e)


def main():
    trading_client = get_trading_client()

    risk = RiskManager(
        RiskSettings(
            max_position_pct=0.10,
            max_total_exposure_pct=0.30,
            max_risk_per_trade_pct=0.01,
            stop_loss_pct=0.02,
            take_profit_pct=0.04,
            max_daily_loss_pct=0.03,
            max_open_positions=3,
            max_trades_per_day=5,
            cooldown_after_trade_minutes=10,
            cooldown_after_loss_minutes=30,
            min_cash_pct=0.05,
            max_price_age_seconds=300,
        )
    )

    print(f"\n=== STARTAR BOT FÖR {SYMBOL} ===")

    try:
        print(f"\nHämtar historiska bars för {SYMBOL}...")
        bars = get_historical_bars(
            symbol=SYMBOL,
            limit=100,
        )

        print(f"Hämtade {len(bars)} bars.")
        print(f"Första bar: {bars.iloc[0]['timestamp']}")
        print(f"Senaste bar: {bars.iloc[-1]['timestamp']}")

    except Exception as e:
        print(f"Kunde inte hämta market data: {e}")
        return

    signal = generate_signal(bars)

    print("\nStrategisignal:")
    print(signal)

    try:
        latest = get_latest_price_with_timestamp(SYMBOL)
        latest_price = latest["price"]
        latest_timestamp = latest["timestamp"]

        print(f"\nSenaste pris för {SYMBOL}: {latest_price}")
        print(f"Timestamp: {latest_timestamp}")

    except Exception as e:
        print(f"Kunde inte hämta latest price: {e}")
        return

    if signal["signal"] == "BUY":
        print("\nBUY-signal. Frågar RiskManager...")

        approved, result = risk.approve_trade(
            client=trading_client,
            symbol=SYMBOL,
            price=latest_price,
            price_timestamp=latest_timestamp,
        )

        if not approved:
            print(f"Trade nekad av RiskManager: {result}")
            return

        print("\nTrade godkänd av RiskManager:")
        print(result)

        try:
            response = buy_with_bracket_order(trading_client, result)
            risk.record_trade()

            print("\nBUY-order skickad:")
            print(response)

        except Exception as e:
            print(f"Kunde inte skicka BUY-order: {e}")

    elif signal["signal"] == "SELL":
        print(f"\nSELL-signal för {SYMBOL}. Kollar om position finns...")

        success, response = close_position_if_exists(trading_client, SYMBOL)

        if success:
            risk.record_trade()
            print("\nPosition stängd:")
            print(response)
        else:
            print("\nIngen position stängdes:")
            print(response)

    else:
        print("\nIngen trade. HOLD.")


if __name__ == "__main__":
    main()