import pandas as pd
import numpy as np


class HelperTA:
    def Stochastic(self, data, period=14):
        low = data.rolling(window=period).min()
        high = data.rolling(window=period).max()
        k_percent = 100 * ((data - low) / (high - low))
        return k_percent

    def RSI(self, data, period=14):
        delta = data.diff()
        up, down = delta.copy(), delta.copy()
        up[up < 0] = 0
        down[down > 0] = 0
        roll_up = up.ewm(span=period).mean()
        roll_down = down.abs().ewm(span=period).mean()
        RS = roll_up / roll_down
        RSI = 100.0 - (100.0 / (1.0 + RS))
        return RSI

    def stockRSI(self, data, K=5, D=5, rsiPeriod=20, stochPeriod=3):
        rsi = self.RSI(data, period=rsiPeriod)
        stoch = self.Stochastic(rsi, period=stochPeriod)
        k = stoch.rolling(window=K).mean()
        d = k.rolling(window=D).mean()
        return (k, d)

    def DCO(self, data, donchianPeriod=20, smaPeriod=3):
        lower = data.rolling(window=donchianPeriod).min()
        upper = data.rolling(window=donchianPeriod).max()
        DCO = (data - lower) / (upper - lower) * 100
        s = DCO.rolling(window=smaPeriod).mean()
        return (DCO, s)

    def MarketCycle(
        self,
        donchianPrice,
        rsiPrice,
        srsiPrice,
        donchianPeriod,
        donchianSmoothing,
        rsiPeriod,
        rsiSmoothing,
        srsiPeriod,
        srsiSmoothing,
        srsiK,
        srsiD,
        rsiWeight,
        srsiWeight,
        dcoWeight,
    ):
        DCO, DCOs = self.DCO(donchianPrice, donchianPeriod, donchianSmoothing)
        rsiValue = self.RSI(rsiPrice, rsiPeriod)
        rsiK = rsiValue.rolling(window=rsiSmoothing).mean()
        k, d = self.stockRSI(srsiPrice, srsiK, srsiD, srsiPeriod, srsiSmoothing)
        aggr = ((DCO + DCOs) * dcoWeight + (rsiValue + rsiK) * rsiWeight + (k + d) * srsiWeight) / (
            2 * (dcoWeight + rsiWeight + srsiWeight)
        )
        return aggr


class MarketCycle:
    def __init__(self, data):
        self.data = data
        self.hta = HelperTA()

    def mc(self, a, b):
        return self.hta.MarketCycle(
            self.data["Close"],
            self.data["Close"],
            self.data["Close"],
            donchianPeriod=a,
            donchianSmoothing=3,
            rsiPeriod=a,
            rsiSmoothing=3,
            srsiPeriod=b,
            srsiSmoothing=3,
            srsiK=5,
            srsiD=5,
            rsiWeight=0.5,
            srsiWeight=1,
            dcoWeight=1,
        )

    def build(self):
        self.data["MarketCycle"] = self.mc(14, 20)
        self.data["Prev_MarketCycle"] = self.data["MarketCycle"].shift()
        self.data["Prev2_MarketCycle"] = self.data["Prev_MarketCycle"].shift()
        return self.data
