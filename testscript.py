from config import get_trading_client

from data.market_data import (
    get_historical_bars,
    get_latest_price_with_timestamp,
)

from strategy.rsi_bollinger import (
    add_indicators,
    generate_signal,
)

from risk.risk_manager import RiskManager, RiskSettings


SYMBOL = "SPY"


def print_section(title: str):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def test_trading_client():
    print_section("1. TESTAR TRADING CLIENT / ACCOUNT")

    client = get_trading_client()
    account = client.get_account()
    clock = client.get_clock()

    print(f"Account status: {account.status}")
    print(f"Equity: {account.equity}")
    print(f"Cash: {account.cash}")
    print(f"Market open: {clock.is_open}")
    print(f"Next open: {clock.next_open}")
    print(f"Next close: {clock.next_close}")

    return client


def test_market_data():
    print_section("2. TESTAR HISTORISKA BARS")

    bars = get_historical_bars(
        symbol=SYMBOL,
        limit=100,
    )

    print(f"Antal bars: {len(bars)}")
    print(f"Kolumner: {list(bars.columns)}")

    print("\nFörsta 3 bars:")
    print(bars[["timestamp", "open", "high", "low", "close", "volume"]].head(3))

    print("\nSenaste 3 bars:")
    print(bars[["timestamp", "open", "high", "low", "close", "volume"]].tail(3))

    first_time = bars.iloc[0]["timestamp"]
    last_time = bars.iloc[-1]["timestamp"]

    print(f"\nFörsta timestamp: {first_time}")
    print(f"Senaste timestamp: {last_time}")
    print(f"Data sorterad rätt: {first_time < last_time}")

    return bars


def test_latest_price():
    print_section("3. TESTAR LATEST PRICE")

    latest = get_latest_price_with_timestamp(SYMBOL)

    print(f"Symbol: {latest['symbol']}")
    print(f"Price: {latest['price']}")
    print(f"Timestamp: {latest['timestamp']}")

    return latest


def test_strategy(bars):
    print_section("4. TESTAR STRATEGI / INDIKATORER")

    df = add_indicators(bars)
    latest_row = df.iloc[-1]

    print("Senaste indikatorrad:")
    print(
        latest_row[
            [
                "timestamp",
                "close",
                "rsi",
                "bb_lower",
                "bb_middle",
                "bb_upper",
            ]
        ]
    )

    signal = generate_signal(bars)

    print("\nSignal:")
    print(signal)

    return signal


def test_risk_manager(client, latest):
    print_section("5. TESTAR RISK MANAGER UTAN ATT LÄGGA ORDER")

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

    price = latest["price"]
    timestamp = latest["timestamp"]

    print(f"Testar approve_trade för {SYMBOL}")
    print(f"Price: {price}")
    print(f"Timestamp: {timestamp}")

    approved, result = risk.approve_trade(
        client=client,
        symbol=SYMBOL,
        price=price,
        price_timestamp=timestamp,
    )

    print(f"\nApproved: {approved}")
    print("Result:")
    print(result)

    if approved:
        print("\nTolkning:")
        print(f"RiskManager hade tillåtit köp av {result['qty']} aktier.")
        print(f"Entry: {result['entry_price']}")
        print(f"Stop loss: {result['stop_loss_price']}")
        print(f"Take profit: {result['take_profit_price']}")
        print(f"Position value: {result['position_value']}")
    else:
        print("\nTolkning:")
        print("RiskManager nekade trade. Det är ofta normalt om marknaden är stängd, datan är gammal, eller du redan har position.")


def main():
    print_section("STARTAR KOMPONENTTEST")
    print(f"Symbol: {SYMBOL}")

    client = test_trading_client()
    bars = test_market_data()
    latest = test_latest_price()
    test_strategy(bars)
    test_risk_manager(client, latest)

    print_section("TEST KLART")
    print("Om du kom hit utan traceback funkar grundkopplingen.")


if __name__ == "__main__":
    main()