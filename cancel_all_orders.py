from config import get_trading_client

client = get_trading_client()
client.cancel_orders()
print("Cancelled all open orders.")