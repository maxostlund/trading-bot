import os
from alpaca.trading.client import TradingClient
from dotenv import load_dotenv

load_dotenv()

def get_trading_client():
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("API-nycklar saknas. Kolla .env")
    
    return TradingClient(api_key,secret_key,paper=True)