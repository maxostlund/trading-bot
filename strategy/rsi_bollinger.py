import pandas as pd


def calculate_rsi(close_prices: pd.Series, period: int = 14) -> pd.Series:
    delta = close_prices.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=period).mean()
    avg_loss = losses.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def calculate_bollinger_bands(
    close_prices: pd.Series,
    period: int = 20,
    num_std: float = 2.0,
):
    middle_band = close_prices.rolling(window=period).mean()
    std = close_prices.rolling(window=period).std()

    upper_band = middle_band + (num_std * std)
    lower_band = middle_band - (num_std * std)

    return upper_band, middle_band, lower_band


def add_indicators(
    bars: pd.DataFrame,
    rsi_period: int = 14,
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
) -> pd.DataFrame:
    df = bars.copy()

    df["rsi"] = calculate_rsi(df["close"], period=rsi_period)

    upper, middle, lower = calculate_bollinger_bands(
        df["close"],
        period=bollinger_period,
        num_std=bollinger_std,
    )

    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower

    return df


def generate_signal(
    bars: pd.DataFrame,
    rsi_period: int = 14,
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
):
    if bars is None or bars.empty:
        return {
            "signal": "HOLD",
            "reason": "No data",
        }

    if len(bars) < max(rsi_period, bollinger_period) + 2:
        return {
            "signal": "HOLD",
            "reason": "Not enough data",
            "bars_count": len(bars),
        }

    df = add_indicators(
        bars=bars,
        rsi_period=rsi_period,
        bollinger_period=bollinger_period,
        bollinger_std=bollinger_std,
    )

    latest = df.iloc[-1]

    close = float(latest["close"])
    rsi = float(latest["rsi"])
    bb_upper = float(latest["bb_upper"])
    bb_middle = float(latest["bb_middle"])
    bb_lower = float(latest["bb_lower"])

    if pd.isna(rsi) or pd.isna(bb_upper) or pd.isna(bb_middle) or pd.isna(bb_lower):
        return {
            "signal": "HOLD",
            "reason": "Indicators not ready",
        }

    base_result = {
        "close": close,
        "rsi": round(rsi, 2),
        "bb_upper": round(bb_upper, 2),
        "bb_middle": round(bb_middle, 2),
        "bb_lower": round(bb_lower, 2),
    }

    if rsi < 30 and close <= bb_lower:
        return {
            "signal": "BUY",
            "reason": "RSI < 30 and close <= lower Bollinger Band",
            **base_result,
        }

    if rsi > 70 or close >= bb_upper:
        return {
            "signal": "SELL",
            "reason": "RSI > 70 or close >= upper Bollinger Band",
            **base_result,
        }

    return {
        "signal": "HOLD",
        "reason": "No trade signal",
        **base_result,
    }

def generate_signals_for_dataframe(
    bars: pd.DataFrame,
    rsi_period: int = 14,
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
    buy_rsi_threshold: float = 30,
    sell_rsi_threshold: float = 70,
) -> pd.DataFrame:
    """
    Räknar RSI + Bollinger Bands och skapar en signal för varje candle.

    Returnerar DataFrame med extra kolumner:
    rsi, bb_upper, bb_middle, bb_lower, signal, signal_reason
    """

    df = add_indicators(
        bars=bars,
        rsi_period=rsi_period,
        bollinger_period=bollinger_period,
        bollinger_std=bollinger_std,
    )

    df["signal"] = "HOLD"
    df["signal_reason"] = "No trade signal"

    buy_condition = (
        (df["rsi"] < buy_rsi_threshold)
        & (df["close"] <= df["bb_lower"])
    )

    sell_condition = (
        (df["rsi"] > sell_rsi_threshold)
        | (df["close"] >= df["bb_upper"])
    )

    df.loc[buy_condition, "signal"] = "BUY"
    df.loc[buy_condition, "signal_reason"] = "RSI low + close below lower band"

    df.loc[sell_condition, "signal"] = "SELL"
    df.loc[sell_condition, "signal_reason"] = "RSI high or close above upper band"

    return df