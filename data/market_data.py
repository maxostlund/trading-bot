import os
from datetime import datetime, timedelta, timezone

import pandas as pd
from dotenv import load_dotenv

from alpaca.common.enums import Sort
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestBarRequest
from alpaca.data.timeframe import TimeFrame


load_dotenv()


def get_market_data_client():
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("API-nycklar saknas. Kolla .env")

    return StockHistoricalDataClient(api_key, secret_key)


def get_historical_bars(
    symbol: str,
    timeframe=TimeFrame.Minute,
    limit: int = 100,
    lookback_days: int = 10,
) -> pd.DataFrame:
    """
    Hämtar de SENASTE historiska bars/candles för en symbol.

    Returnerar DataFrame med ungefär:
    symbol, timestamp, open, high, low, close, volume, trade_count, vwap
    """

    client = get_market_data_client()

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=lookback_days)

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        limit=limit,
        sort=Sort.DESC,
        feed=DataFeed.IEX,
    )

    bars = client.get_stock_bars(request)
    df = bars.df

    if df.empty:
        raise ValueError(f"Inga bars hittades för {symbol}")

    df = df.reset_index()

    if "symbol" in df.columns:
        df = df[df["symbol"] == symbol]

    if df.empty:
        raise ValueError(f"Inga bars kvar efter filtrering för {symbol}")

    df = df.sort_values("timestamp").reset_index(drop=True)

    required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        raise ValueError(f"Saknade kolumner i market data: {missing_columns}")

    return df


def get_latest_bar(symbol: str):
    """
    Hämtar senaste baren för en symbol.
    """

    client = get_market_data_client()

    request = StockLatestBarRequest(
        symbol_or_symbols=symbol,
        feed=DataFeed.IEX,
    )

    latest_bars = client.get_stock_latest_bar(request)

    if symbol not in latest_bars:
        raise ValueError(f"Ingen latest bar hittades för {symbol}")

    return latest_bars[symbol]


def get_latest_price(symbol: str) -> float:
    latest_bar = get_latest_bar(symbol)
    return float(latest_bar.close)


def get_latest_price_with_timestamp(symbol: str):
    latest_bar = get_latest_bar(symbol)

    return {
        "symbol": symbol,
        "price": float(latest_bar.close),
        "timestamp": latest_bar.timestamp,
    }