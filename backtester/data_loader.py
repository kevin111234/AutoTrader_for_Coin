import sys
import os
# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import pandas as pd
from datetime import datetime
from binance.client import Client

from src.config import Config
from src.data_control import Data_Control

def load_backtest_data(client, symbol, timeframe, start_date, limit=300, futures=False):
    """
    주어진 시작 날짜부터 limit 개의 캔들 데이터를 로딩하여 DataFrame으로 반환.
    
    매개변수:
    client    : Binance API client 인스턴스
    symbol    : 심볼 (예: "BTC")
    timeframe : 캔들 간격 (예: Client.KLINE_INTERVAL_1MINUTE)
    start_date: 시작 날짜 (예:"2023-01-01 00:00:00")
    limit     : 불러올 캔들 수 (기본 300)
    futures   : 선물 여부 (기본 False)
    """
    symbol = f"{symbol}USDT"
    
    if futures:
        # futures_klines는 start_date를 timestamp(ms)로 전달해야 함
        dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        start_ts = int(dt.timestamp() * 1000)
        candles = client.futures_klines(symbol=symbol, interval=timeframe, startTime=start_ts, limit=limit)
    else:
        # get_historical_klines는 시작 날짜 문자열 사용 가능
        candles = client.get_historical_klines(symbol, timeframe, start_date, limit=limit)
    
    # API 반환 항목: [Open Time, Open, High, Low, Close, Volume, Close Time, ...]
    columns = [
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ]
    df = pd.DataFrame(candles, columns=columns)
    
    # 필요한 칼럼만 선택 및 형변환
    use_cols = ["Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]
    df = df[use_cols].copy()
    
    for col in ["Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]:
        df[col] = df[col].astype(float)
    
    # Taker Sell 거래량 = Volume - Taker Buy 거래량
    df["Taker Sell Base Asset Volume"] = df["Volume"] - df["Taker Buy Base Asset Volume"]
    
    # 타임스탬프 변환 및 정렬
    df["Open Time"] = pd.to_datetime(df["Open Time"], unit='ms')
    df = df.sort_values("Open Time").reset_index(drop=True)
    return df

def cal_indicator(data):
    data_control = Data_Control()
    # 각 데이터에 대한 기술적 지표 계산
    data = data_control.cal_moving_average(data)
    data = data_control.cal_rsi(data)
    data = data_control.cal_bollinger_band(data)
    data = data_control.cal_obv(data)
    data = data_control.LT_trand_check(data)

    data = data.dropna()

    if len(data) > 140:
        data = data.iloc[-140:].reset_index(drop=True)

    return data

if __name__ == "__main__":
    config = Config()
    api_key = config.binance_access_key
    api_secret = config.binance_secret_key
    client = Client(api_key, api_secret)

    symbol = "BTC"
    start_date = "2023-01-01 00:00:00"
    data_dict = {}

    for timeframe in ["1m", "5m", "1h"]:
        data = load_backtest_data(client, symbol, timeframe, start_date, limit=300, futures=False)
        data_dict[timeframe] = cal_indicator(data)

    print("데이터 로딩 완료:")
    print(data_dict)
