import sys
from pathlib import Path

# Gör så att scriptet hittar projektroten även om det körs från scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from data.market_data import get_historical_bars
from strategy.rsi_bollinger import generate_signals_for_dataframe


SYMBOL = "SPY"

LIMIT = 200

STOP_LOSS_PCT = 0.02
TAKE_PROFIT_PCT = 0.04
MAX_HOLD_BARS = 30


def simulate_trade_outcomes(
    df,
    stop_loss_pct: float = STOP_LOSS_PCT,
    take_profit_pct: float = TAKE_PROFIT_PCT,
    max_hold_bars: int = MAX_HOLD_BARS,
):
    """
    Enkel mini-backtest:

    För varje BUY-signal:
    - entry = close på BUY-candlen
    - stop loss = entry * (1 - stop_loss_pct)
    - take profit = entry * (1 + take_profit_pct)
    - kollar kommande candles:
        - om low <= stop loss => LOSS
        - om high >= take profit => WIN
        - om inget händer inom max_hold_bars => TIME_EXIT

    Obs:
    Om både stop loss och take profit träffas i samma candle vet vi inte vad som hände först.
    Då markerar vi AMBIGUOUS.
    """

    df = df.copy()

    df["trade_outcome"] = None
    df["exit_index"] = None
    df["exit_price"] = None
    df["entry_price"] = None
    df["stop_loss_price"] = None
    df["take_profit_price"] = None

    buy_indices = df.index[df["signal"] == "BUY"].tolist()

    for entry_index in buy_indices:
        entry_price = float(df.loc[entry_index, "close"])
        stop_loss_price = entry_price * (1 - stop_loss_pct)
        take_profit_price = entry_price * (1 + take_profit_pct)

        df.loc[entry_index, "entry_price"] = entry_price
        df.loc[entry_index, "stop_loss_price"] = stop_loss_price
        df.loc[entry_index, "take_profit_price"] = take_profit_price

        outcome = "TIME_EXIT"
        exit_index = min(entry_index + max_hold_bars, df.index[-1])
        exit_price = float(df.loc[exit_index, "close"])

        for future_index in range(entry_index + 1, min(entry_index + max_hold_bars + 1, len(df))):
            high = float(df.loc[future_index, "high"])
            low = float(df.loc[future_index, "low"])

            hit_stop = low <= stop_loss_price
            hit_take_profit = high >= take_profit_price

            if hit_stop and hit_take_profit:
                outcome = "AMBIGUOUS"
                exit_index = future_index
                exit_price = float(df.loc[future_index, "close"])
                break

            if hit_stop:
                outcome = "LOSS"
                exit_index = future_index
                exit_price = stop_loss_price
                break

            if hit_take_profit:
                outcome = "WIN"
                exit_index = future_index
                exit_price = take_profit_price
                break

        df.loc[entry_index, "trade_outcome"] = outcome
        df.loc[entry_index, "exit_index"] = exit_index
        df.loc[entry_index, "exit_price"] = exit_price

    return df


def print_trade_summary(df):
    buys = df[df["signal"] == "BUY"]

    print("\n==============================")
    print("TRADE SUMMARY")
    print("==============================")
    print(f"Antal BUY-signaler: {len(buys)}")

    if buys.empty:
        print("Inga BUY-signaler hittades med nuvarande regler.")
        return

    outcome_counts = buys["trade_outcome"].value_counts(dropna=False)

    print("\nUtfall:")
    print(outcome_counts)

    print("\nSenaste BUY-signaler:")
    columns = [
        "timestamp",
        "close",
        "rsi",
        "bb_lower",
        "bb_upper",
        "trade_outcome",
        "entry_price",
        "stop_loss_price",
        "take_profit_price",
        "exit_price",
    ]

    print(buys[columns].tail(10).to_string(index=False))


def plot_candles(ax, df):
    """
    Enkel egen candlestick-plot med matplotlib.
    """

    candle_width = 0.6

    for i, row in df.iterrows():
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])

        if close_price >= open_price:
            color = "green"
        else:
            color = "red"

        # Wick
        ax.plot([i, i], [low_price, high_price], color=color, linewidth=1)

        # Body
        lower = min(open_price, close_price)
        height = abs(close_price - open_price)

        if height == 0:
            height = 0.01

        rectangle = Rectangle(
            (i - candle_width / 2, lower),
            candle_width,
            height,
            color=color,
            alpha=0.5,
        )

        ax.add_patch(rectangle)


def visualize(df):
    fig, (price_ax, rsi_ax) = plt.subplots(
        2,
        1,
        figsize=(16, 10),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
    )

    plot_candles(price_ax, df)

    price_ax.plot(df.index, df["bb_upper"], label="Bollinger Upper", linewidth=1)
    price_ax.plot(df.index, df["bb_middle"], label="Bollinger Middle", linewidth=1)
    price_ax.plot(df.index, df["bb_lower"], label="Bollinger Lower", linewidth=1)

    buy_df = df[df["signal"] == "BUY"]
    sell_df = df[df["signal"] == "SELL"]

    price_ax.scatter(
        buy_df.index,
        buy_df["close"],
        marker="^",
        s=120,
        label="BUY signal",
        color="green",
        zorder=5,
    )

    price_ax.scatter(
        sell_df.index,
        sell_df["close"],
        marker="v",
        s=80,
        label="SELL signal",
        color="red",
        zorder=5,
    )

    # Markera trade outcome från BUY-signaler
    for entry_index, row in buy_df.iterrows():
        outcome = row["trade_outcome"]
        exit_index = row["exit_index"]
        exit_price = row["exit_price"]

        if exit_index is None or exit_price is None:
            continue

        exit_index = int(exit_index)

        if outcome == "WIN":
            outcome_color = "green"
        elif outcome == "LOSS":
            outcome_color = "red"
        elif outcome == "AMBIGUOUS":
            outcome_color = "orange"
        else:
            outcome_color = "gray"

        price_ax.plot(
            [entry_index, exit_index],
            [row["entry_price"], exit_price],
            linestyle="--",
            color=outcome_color,
            linewidth=1,
            alpha=0.8,
        )

        price_ax.scatter(
            exit_index,
            exit_price,
            marker="x",
            color=outcome_color,
            s=80,
            zorder=6,
        )

    price_ax.set_title(f"{SYMBOL} RSI + Bollinger Strategy")
    price_ax.set_ylabel("Price")
    price_ax.legend()
    price_ax.grid(True, alpha=0.3)

    rsi_ax.plot(df.index, df["rsi"], label="RSI", linewidth=1)
    rsi_ax.axhline(70, linestyle="--", linewidth=1)
    rsi_ax.axhline(30, linestyle="--", linewidth=1)

    rsi_ax.set_ylabel("RSI")
    rsi_ax.set_xlabel("Candles")
    rsi_ax.legend()
    rsi_ax.grid(True, alpha=0.3)

    # Snygga x-labels med timestamps
    step = max(len(df) // 10, 1)
    tick_positions = df.index[::step]
    tick_labels = df.loc[tick_positions, "timestamp"].astype(str).str.slice(0, 16)

    plt.xticks(tick_positions, tick_labels, rotation=45)

    plt.tight_layout()
    plt.show()


def main():
    print(f"Hämtar {LIMIT} senaste bars för {SYMBOL}...")

    bars = get_historical_bars(
        symbol=SYMBOL,
        limit=LIMIT,
    )

    print(f"Hämtade {len(bars)} bars.")
    print(f"Första timestamp: {bars.iloc[0]['timestamp']}")
    print(f"Senaste timestamp: {bars.iloc[-1]['timestamp']}")

    df = generate_signals_for_dataframe(bars)

    df = simulate_trade_outcomes(df)

    print_trade_summary(df)

    visualize(df)


if __name__ == "__main__":
    main()