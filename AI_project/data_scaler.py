import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, QuantileTransformer
from binance.client import Client
import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.config import Config
from src.data_control import Data_Control
from backtester.data_loader import timeframe_to_timedelta, load_backtest_data, cal_indicator, update_data

def data_scaler(data_dict, ticker_list):
    """
    각 심볼, 타임프레임별로 데이터프레임의 여러 피처에 대해
    지정한 스케일링 방법(로그 변환+스탠다드, MinMax, Robust 등)을 적용하고,
    각 그룹별 스케일러 객체를 scaler_dict에 저장하여 나중에 복원(unscale)할 수 있도록 함.
    ATR 컬럼도 가격 그룹에 포함시킴.
    """
    scaled_data = {}
    scaler_dict = {}

    for symbol in ticker_list:
        scaled_data[symbol] = {}
        scaler_dict[symbol] = {}
        for timeframe in ["1m", "5m", "1h"]:
            df = data_dict[symbol][timeframe].copy()
            scaler_dict[symbol][timeframe] = {}

            # 1. 가격 및 관련 지표 그룹 (ATR 추가)
            price_features = ['Open', 'High', 'Low', 'Close', 'SMA_20', 'SMA_60', 'SMA_120', 'upper_boll', 'lower_boll', 'ATR']
            # 가격 데이터에 log1p 적용 (0 이하 값 없다는 가정)
            df[price_features] = df[price_features].apply(lambda x: np.log1p(x))
            price_scaler = StandardScaler()
            df[price_features] = price_scaler.fit_transform(df[price_features])
            scaler_dict[symbol][timeframe]['price'] = price_scaler

            # 2. RSI, ADX 등 모멘텀/강도 지표 그룹
            rsi_adx_features = ['rsi', 'rsi_signal', 'ADX', 'percent_b']
            rsi_adx_scaler = MinMaxScaler(feature_range=(0, 1))
            df[rsi_adx_features] = rsi_adx_scaler.fit_transform(df[rsi_adx_features])
            scaler_dict[symbol][timeframe]['rsi_adx'] = rsi_adx_scaler

            # 3. MACD, OBV, bandwidth 그룹
            macd_obv_features = ['MACD', 'MACD_signal', 'obv', 'bandwidth']
            robust_scaler = RobustScaler()
            df[macd_obv_features] = robust_scaler.fit_transform(df[macd_obv_features])
            scaler_dict[symbol][timeframe]['macd_obv'] = robust_scaler

            # 4. 거래량 그룹
            volume_features = ['Volume', 'Taker Buy Base Asset Volume']
            df[volume_features] = np.log1p(df[volume_features])
            volume_scaler = StandardScaler()  # 또는 RobustScaler() 선택 가능
            df[volume_features] = volume_scaler.fit_transform(df[volume_features])
            scaler_dict[symbol][timeframe]['volume'] = volume_scaler

            scaled_data[symbol][timeframe] = df

    return scaled_data, scaler_dict

def data_unscaler(scaled_data, scaler_dict, ticker_list):
    """
    data_scaler에서 저장한 scaler_dict를 활용하여,
    스케일링된 데이터프레임을 원래 값으로 복원하는 함수.
    가격 그룹(로그 변환 적용)은 inverse_transform 후 np.expm1로 복원합니다.
    """
    unscaled_data = {}

    for symbol in ticker_list:
        unscaled_data[symbol] = {}
        for timeframe in ["1m", "5m", "1h"]:
            df = scaled_data[symbol][timeframe].copy()

            # 1. 가격 및 관련 지표 그룹 (ATR 포함)
            price_features = ['Open', 'High', 'Low', 'Close', 'SMA_20', 'SMA_60', 'SMA_120', 'upper_boll', 'lower_boll', 'ATR']
            price_scaler = scaler_dict[symbol][timeframe]['price']
            df[price_features] = price_scaler.inverse_transform(df[price_features])
            df[price_features] = np.expm1(df[price_features])  # 로그 변환 역변환

            # 2. RSI, ADX 그룹
            rsi_adx_features = ['rsi', 'rsi_signal', 'ADX', 'percent_b']
            rsi_adx_scaler = scaler_dict[symbol][timeframe]['rsi_adx']
            df[rsi_adx_features] = rsi_adx_scaler.inverse_transform(df[rsi_adx_features])

            # 3. MACD, OBV 그룹
            macd_obv_features = ['MACD', 'MACD_signal', 'obv', 'bandwidth']
            robust_scaler = scaler_dict[symbol][timeframe]['macd_obv']
            df[macd_obv_features] = robust_scaler.inverse_transform(df[macd_obv_features])

            # 4. 거래량 그룹
            volume_features = ['Volume', 'Taker Buy Base Asset Volume']
            volume_scaler = scaler_dict[symbol][timeframe]['volume']
            df[volume_features] = volume_scaler.inverse_transform(df[volume_features])
            df[volume_features] = np.expm1(df[volume_features])

            unscaled_data[symbol][timeframe] = df

    return unscaled_data

if __name__ == "__main__":
    config = Config()
    api_key = config.binance_access_key
    api_secret = config.binance_secret_key
    client = Client(api_key, api_secret)

    future_use = bool(config.futures_use)
    if future_use:
        ticker_list = config.futures_coin_tickers.split(" ")
    else:
        ticker_list = config.coin_tickers.split(" ")

    # 백테스트 시작 시점을 end_date로 지정 → 해당 시점까지의 데이터 로딩
    end_date = "2023-01-01 00:00:00"
    data_dict = {}

    for symbol in ticker_list:
        data_dict[symbol] = {}
        for timeframe in ["1m", "5m", "1h"]:
            data = load_backtest_data(client, symbol, timeframe, end_date, limit=300, futures=future_use)
            data_dict[symbol][timeframe] = cal_indicator(data)

    scaled_data, scaler_dict = data_scaler(data_dict, ticker_list)

    print("스케일링 완료!")
    # CSV 저장
    for symbol, timeframe_data in scaled_data.items():
        for timeframe, df in timeframe_data.items():
            file_path = f"scaled_data/{symbol}_{timeframe}_scaled.csv"
            df.to_csv(file_path, index=False)
            print(f"Saved {file_path}")

    # 예시: 스케일링된 데이터를 원래 값으로 복원해보고 출력
    unscaled_data = data_unscaler(scaled_data, scaler_dict, ticker_list)
    for symbol, timeframe_data in unscaled_data.items():
        for timeframe, df in timeframe_data.items():
            print(f"Unscaled data for {symbol} {timeframe}:")
            print(df.head())
