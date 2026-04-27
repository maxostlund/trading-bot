Testar att sätta upp en algoritmisk paper trading-bot. Målet är att förlora en massa pengar (och lära mig varför)

#features
- Hämta senaste 200 1-minuts candlebars för SPY via Alpaca
- Räknar RSI och Bollingerband
- Genererar BUY / HOLD / SELL signal
- Utvärderar via risk_manager ifall en position är tillåten
- Printar ut graf för hur strategin hanterade senaste 200 en-minutsbars (signaler, candlebars)

#Strategi just nu
- Bollinger banden väger för mkt
- Kanske om man försöker analysera när marknaden rör sig sidleds vs trend, vilket låter omöjligt
- Strategin är fett bearish (iaf baserat på mitt fantastiska 200minuters stickprov)

#Nästa
- logging
- leka runt

#random tankar
- skäms lite över vibe-coding aspekten, men satan vad kraftfullt det är 