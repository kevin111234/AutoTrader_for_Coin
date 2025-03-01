import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from datetime import datetime, timedelta
import pandas as pd
from binance.client import Client

from src.config import Config
from src.data_control import Data_Control

def timeframe_to_timedelta(timeframe):
    """
    timeframe 문자열("1m", "5m", "1h", "1d" 등)을 timedelta 객체로 변환
    """
    unit = timeframe[-1]
    value = int(timeframe[:-1])
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    elif unit == 'w':
        return timedelta(weeks=value)
    else:
        raise ValueError("지원하지 않는 timeframe 단위: " + timeframe)

def load_backtest_data(client, symbol, timeframe, end_date, limit=300, futures=False):
    """
    주어진 end_date(예: "2023-01-01 00:00:00")까지의 데이터 limit 개의 캔들 데이터를 로딩하여 DataFrame으로 반환.
    
    매개변수:
    client    : Binance API client 인스턴스
    symbol    : 심볼 (예: "BTC")
    timeframe : 캔들 간격 (예: "1m", "5m", "1h")
    end_date  : 백테스트 시작 시점(해당 시점까지의 데이터 로딩)
    limit     : 불러올 캔들 수 (기본 300)
    futures   : 선물 여부 (기본 False)
    """
    symbol = f"{symbol}USDT"
    end_dt = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    
    if futures:
        # 선물의 경우 endTime 매개변수와 limit을 사용해 end_date 이전 limit 캔들 로딩
        end_ts = int(end_dt.timestamp() * 1000)
        candles = client.futures_klines(symbol=symbol, interval=timeframe, endTime=end_ts, limit=limit)
    else:
        # 스팟의 경우, start_dt를 계산해서 end_date까지의 데이터를 요청
        delta = timeframe_to_timedelta(timeframe) * limit
        start_dt = end_dt - delta
        candles = client.get_historical_klines(
            symbol, timeframe,
            start_dt.strftime("%Y-%m-%d %H:%M:%S"),
            end_date
        )
    
    # API 반환 항목: [Open Time, Open, High, Low, Close, Volume, Close Time, ...]
    columns = [
        "Open Time", "Open", "High", "Low", "Close", "Volume",
        "Close Time", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ]
    df = pd.DataFrame(candles, columns=columns)
    
    # 필요한 칼럼 선택 및 데이터 타입 변환
    use_cols = ["Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]
    df = df[use_cols].copy()
    for col in ["Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]:
        df[col] = df[col].astype(float)
    
    # Taker Sell 거래량 계산
    df["Taker Sell Base Asset Volume"] = df["Volume"] - df["Taker Buy Base Asset Volume"]
    
    # Open Time을 datetime으로 변환 후 정렬
    df["Open Time"] = pd.to_datetime(df["Open Time"], unit='ms')
    df = df.drop_duplicates(subset=["Open Time"]).sort_values("Open Time").reset_index(drop=True)
    
    # 혹시 데이터가 limit보다 많다면 마지막 limit개만 취함
    if len(df) > limit:
        df = df.iloc[-limit:].reset_index(drop=True)
    
    return df

def cal_indicator(data):
    data_control = Data_Control()
    # 기술적 지표 계산
    data = data_control.cal_moving_average(data)
    data = data_control.cal_rsi(data)
    data = data_control.cal_bollinger_band(data)
    data = data_control.cal_obv(data)
    data = data_control.LT_trand_check(data)
    data = data_control.cal_atr(data)
    data = data_control.cal_macd(data)
    data = data_control.cal_adx(data)

    data = data.dropna()

    if len(data) > 140:
        data = data.iloc[-140:].reset_index(drop=True)

    return data

def update_data(existing_df, client, symbol, timeframe, futures=False):
    """
    기존 데이터를 기반으로 마지막 캔들의 open_time 이후 5분 후의 캔들을 불러와 병합함.

    매개변수:
    existing_df : 기존 DataFrame (칼럼: "Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume")
    client      : Binance API client 인스턴스
    symbol      : 심볼 (예: "BTCUSDT")
    timeframe   : 캔들 간격 (예: Client.KLINE_INTERVAL_5MINUTE 또는 "5m")
    futures     : 선물 여부 (기본 False)

    반환:
    기존 데이터에 새 캔들을 병합한 DataFrame
    """
    symbol = f"{symbol}USDT"
    # 마지막 캔들의 Open Time 가져오기
    last_open_time = existing_df.iloc[-1]["Open Time"]
    # 새로운 데이터 시작 시각: 마지막 open_time + 5분
    new_start_dt = last_open_time + timedelta(minutes=5)
    new_start_str = new_start_dt.strftime("%Y-%m-%d %H:%M:%S")
    
    # 새 캔들 데이터 로딩 (캔들 하나만 요청)
    if futures:
        # futures_klines는 timestamp(ms) 사용
        start_ts = int(new_start_dt.timestamp() * 1000)
        candles = client.futures_klines(symbol=symbol, interval=timeframe, startTime=start_ts, limit=1)
    else:
        # 스팟은 시작 시간 문자열 사용 가능
        candles = client.get_historical_klines(symbol, timeframe, new_start_str, limit=1)
    
    if not candles:
        # 새 데이터 없으면 기존 데이터 그대로 반환
        return existing_df
    
    # API 반환 항목: [Open Time, Open, High, Low, Close, Volume, Close Time, ...]
    cols = ["Open Time", "Open", "High", "Low", "Close", "Volume",
            "Close Time", "Quote Asset Volume", "Number of Trades",
            "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"]
    new_df = pd.DataFrame(candles, columns=cols)
    
    # 필요한 칼럼 선택 및 형변환
    use_cols = ["Open Time", "Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]
    new_df = new_df[use_cols].copy()
    for col in ["Open", "High", "Low", "Close", "Volume", "Taker Buy Base Asset Volume"]:
        new_df[col] = new_df[col].astype(float)
    
    # Taker Sell 거래량 계산
    new_df["Taker Sell Base Asset Volume"] = new_df["Volume"] - new_df["Taker Buy Base Asset Volume"]
    
    # Open Time 컬럼을 datetime 형식으로 변환 (단, 스팟 API의 경우 ms 단위 아님)
    # futures API는 ms 단위 반환하므로, 단위를 확인 후 변환 필요
    try:
        # 시도: ms 단위로 변환
        new_df["Open Time"] = pd.to_datetime(new_df["Open Time"], unit="ms")
    except Exception:
        # 실패하면 문자열 그대로 datetime 변환
        new_df["Open Time"] = pd.to_datetime(new_df["Open Time"])
    
    # 기존 데이터와 새 데이터를 병합
    combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=["Open Time"], keep="last")
    combined_df = combined_df.drop_duplicates(subset=["Open Time"]).sort_values("Open Time").reset_index(drop=True)
    
    return combined_df

if __name__ == "__main__":
    config = Config()
    api_key = config.binance_access_key
    api_secret = config.binance_secret_key
    client = Client(api_key, api_secret)

    ticker_list = config.coin_tickers.split(" ")
    future_use = bool(config.futures_use)
    if future_use:
        future_ticker_list = config.futures_coin_tickers.split(" ")

    # 백테스트 시작 시점을 end_date로 지정 → 해당 시점까지의 데이터 로딩
    end_date = "2023-01-01 00:00:00"
    data_dict = {}
    future_data_dict = {}

    for symbol in ticker_list:
        data_dict[symbol] = {}
        for timeframe in ["1m", "5m", "1h"]:
            data = load_backtest_data(client, symbol, timeframe, end_date, limit=300, futures=False)
            data_dict[symbol][timeframe] = cal_indicator(data)

    if future_use:
        for symbol in future_ticker_list:
            future_data_dict[symbol] = {}
            for timeframe in ["1m", "5m", "1h"]:
                data = load_backtest_data(client, symbol, timeframe, end_date, limit=300, futures=True)
                future_data_dict[symbol][timeframe] = cal_indicator(data)

    print("데이터 로딩 완료:")
    print(data_dict)
    print(future_data_dict)

    for coin, timeframes in data_dict.items():
        for tf, df in timeframes.items():
            csv_filename = f"{coin}_{tf}.csv"
            df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
            print(f"{csv_filename} 파일로 저장 완료.")