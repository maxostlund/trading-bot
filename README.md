## Spy Paper Trading Bot
A paper-trading bot for SPY using Alpaca's API. I built this (AI-assisted) to learn how the main parts of a trading systems works. 

## How it works
- Fetches 200 one-minute SPY data from Alpaca
- Uses RSI (Cutler's not Wilder's) and Bollinger Bands to generate BUY/HOLD/SELL signals
- Runs each trade through a set of risk checks
- Sizes positions based on risk per trade
- Submits bracket orders with stop-loss and take-profit

## Risk manager
Limits position size, total exposure and daily losses, enforces a minimum cash reserve as well as trade cooldowns. Rejects market data older than 60 seconds.

## Limitations
The strategy is simple and relies heavily on Bollinger Bands. Mean reversion works best in ranging markets and loses on trending markets. 

## Next

I would like to implement a better backtest as well as trade logging. When that is in place I will start experimenting with trading strategies.  