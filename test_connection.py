from config import get_trading_client

#Skapa en klient mha TradingClient
client = get_trading_client()
account = client.get_account()

print("Status: ", account.status)
print("Köpkraft: ", account.buying_power)