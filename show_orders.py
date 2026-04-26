from config import get_trading_client

client = get_trading_client()

orders = client.get_orders()

if not orders:
    print("No open orders.")
else:
    for o in orders:
        print(o.symbol, o.side, o.qty, o.status, o.filled_qty, o.submitted_at)