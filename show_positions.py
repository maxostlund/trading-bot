from config import get_trading_client

client = get_trading_client()

positions = client.get_all_positions()

if not positions:
    print("Inga öppna placeringar")
else:
    for p in positions:
        print(p.symbol, p.qty, p.market_value, p.unrealized_pl)