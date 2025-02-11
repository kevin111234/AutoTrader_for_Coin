import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils import get_trend_info

def rsi_stratage(data_core):
    signal = "hold"
    weight = 0
    reason = ""
    stop_loss = 0.98
    take_profit = 1.02

    rsi = data_core["last_5m"]["rsi"]

    if rsi > 80:
        signal = "sell"
        weight = 5
    elif rsi > 75:
        signal = "sell"
        weight = 4
    elif rsi > 70:
        signal = "sell"
        weight = 3
    elif rsi > 65:
        signal = "sell"
        weight = 2
    elif rsi > 60:
        signal = "sell"
        weight = 1

    elif rsi < 20:
        signal = "buy"
        weight = 5
    elif rsi < 25:
        signal = "buy"
        weight = 4
    elif rsi < 30:
        signal = "buy"
        weight = 3
    elif rsi < 35:
        signal = "buy"
        weight = 2
    elif rsi < 40:
        signal = "buy"
        weight = 1

    return {
    "current_price": data_core["last_5m"]["Close"],
    "signal": signal,
    "weight": weight,
    "reason": reason,
    "stop_loss":stop_loss,
    "take_profit":take_profit,
    "trend_5m": data_core["current_trend_5m"],
    "trend_1h": data_core["current_trend_1h"],
    }