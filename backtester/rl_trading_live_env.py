import gym
from gym import spaces
import numpy as np
from datetime import datetime, timedelta
from binance.client import Client
import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.config import Config
from src.data_control import Data_Control
from src.utils import data_source
from backtester.backtest_engine import BacktestEngine
from backtester.data_loader import load_backtest_data, cal_indicator, update_data

class RLTradingLiveEnv(gym.Env):
    def __init__(self, start_date, end_date, max_steps=1000, symbol="BTC"):
        super(RLTradingLiveEnv, self).__init__()
        
        # Binance API 설정
        self.config = Config()
        api_key = self.config.binance_access_key
        api_secret = self.config.binance_secret_key
        self.client = Client(api_key, api_secret)
        
        self.symbol = symbol
        self.start_date = start_date  # "YYYY-MM-DD HH:MM:SS"
        self.end_date = end_date
        self.current_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        self.end_time = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        
        # 초기 데이터 로딩 (1m, 5m, 1h)
        self.data_dict = {self.symbol: {}}
        for timeframe in ["1m", "5m", "1h"]:
            data = load_backtest_data(self.client, self.symbol, timeframe, start_date, limit=300, futures=False)
            self.data_dict[self.symbol][timeframe] = cal_indicator(data)
        print("초기 데이터 저장 완료.")
        
        self.initial_balance = 100000
        self.engine = BacktestEngine(initial_balance=self.initial_balance)
        self.max_steps = max_steps
        
        # 액션 공간: 4차원 연속 벡터
        # 순서: [signal, weight, take_profit, stop_loss]
        # signal: [0, 2] (0: hold, 1: buy, 2: sell)
        # weight: [0, 5]
        # take_profit: [1.0, 2.0]
        # stop_loss: [0.5, 1.0]
        self.action_space = spaces.Box(
            low=np.array([0, 0, 1.0, 0.5], dtype=np.float32),
            high=np.array([2, 5, 2.0, 1.0], dtype=np.float32),
            dtype=np.float32
        )
        
        # 예시 관측 공간: 10차원 벡터
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(29,), dtype=np.float32
        )
    
    def _update_data(self):
        updated_1m = update_data(self.data_dict[self.symbol]["1m"], self.client, self.symbol, "1m", futures=False)
        self.data_dict[self.symbol]["1m"] = cal_indicator(updated_1m)
        last_open_time = self.data_dict[self.symbol]["1m"].iloc[-1]["Open Time"]
        self.current_time = last_open_time
        
        if last_open_time.minute % 5 == 0:
            updated_5m = update_data(self.data_dict[self.symbol]["5m"], self.client, self.symbol, "5m", futures=False)
            self.data_dict[self.symbol]["5m"] = cal_indicator(updated_5m)
        
        if last_open_time.minute == 0:
            updated_1h = update_data(self.data_dict[self.symbol]["1h"], self.client, self.symbol, "1h", futures=False)
            self.data_dict[self.symbol]["1h"] = cal_indicator(updated_1h)
    
    def _get_observation(self):
        data_core = data_source(self.data_dict[self.symbol])

        close_1m = data_core["last_1m"]["Close"]
        rsi_1m = data_core["last_1m"]["rsi"]
        close_5m = data_core["last_5m"]["Close"]
        rsi_5m = data_core["last_5m"]["rsi"]

        sma20_1m    = data_core["last_1m"].get("SMA_20", 0.0)
        sma60_1m    = data_core["last_1m"].get("SMA_60", 0.0)
        sma120_1m   = data_core["last_1m"].get("SMA_120", 0.0)

        sma20_5m    = data_core["last_5m"].get("SMA_20", 0.0)
        sma60_5m    = data_core["last_5m"].get("SMA_60", 0.0)
        sma120_5m   = data_core["last_5m"].get("SMA_120", 0.0)

        upper_boll_1m = data_core["last_1m"].get("upper_boll", 0.0)
        lower_boll_1m = data_core["last_1m"].get("lower_boll", 0.0)
        bandwidth_1m= data_core["last_1m"].get("bandwidth", 0.0)
        percent_b_1m = data_core["last_1m"].get("percent_b", 0.0)
        upper_boll_5m = data_core["last_5m"].get("upper_boll", 0.0)
        lower_boll_5m = data_core["last_5m"].get("lower_boll", 0.0)
        bandwidth_5m= data_core["last_5m"].get("bandwidth", 0.0)
        percent_b_5m = data_core["last_5m"].get("percent_b", 0.0)

        trend_1m = data_core.get("current_trend_1m", 0.0)
        trend_5m = data_core.get("current_trend_5m", 0.0)
        trend_1h = data_core.get("current_trend_1h", 0.0)
        
        volume_ratio = data_core.get("volume_ratio", 1.0)
        buy_volume_ratio = data_core.get("buy_volume_ratio", 0.0)

        obv_1m= data_core["last_1m"].get("obv", 0.0)
        obv_slope_from_max_1m= data_core["last_1m"].get("obv_slope_from_max", 0.0)
        obv_slope_from_min_1m= data_core["last_1m"].get("obv_slope_from_min", 0.0)
        obv_5m= data_core["last_5m"].get("obv", 0.0)
        obv_slope_from_max_5m= data_core["last_5m"].get("obv_slope_from_max", 0.0)
        obv_slope_from_min_5m= data_core["last_5m"].get("obv_slope_from_min", 0.0)
        
        obs = np.array([close_1m, rsi_1m, close_5m, rsi_5m,
                        sma20_1m, sma60_1m, sma120_1m,
                        sma20_5m, sma60_5m, sma120_5m, 
                        upper_boll_1m, upper_boll_5m, lower_boll_1m, lower_boll_5m,
                        percent_b_1m, percent_b_5m,
                        bandwidth_1m, bandwidth_5m,
                        trend_1m, trend_5m, trend_1h,
                        obv_1m, obv_5m, obv_slope_from_max_1m, obv_slope_from_max_5m,
                        obv_slope_from_min_1m, obv_slope_from_min_5m,
                        volume_ratio, buy_volume_ratio], dtype=np.float32)
        return obs
    
    def step(self, action):
        self._update_data()
        data_core = data_source(self.data_dict[self.symbol])
        
        # 액션 벡터를 클립하여 안전하게 만듦
        action = np.clip(action, self.action_space.low, self.action_space.high)
        
        # 첫 번째 값: signal (정수형으로 반올림)
        signal_val = int(round(action[0]))
        if signal_val == 0:
            signal = "hold"
        elif signal_val == 1:
            signal = "buy"
        elif signal_val == 2:
            signal = "sell"
        else:
            signal = "hold"
        
        weight = int(action[1])
        take_profit = float(action[2])
        stop_loss = float(action[3])
        
        current_price = data_core["last_1m"]["Close"]
        signal_info = {
            "current_price": current_price,
            "weight": weight,
            "take_profit": take_profit,
            "stop_loss": stop_loss
        }
        
        prev_balance = self.engine.balance
        prev_total_capital = self.engine.total_capital

        self.engine.execute_trade(signal, signal_info)

        # ✅ 실현손익 계산 (매매 후 잔고 변화량)
        realized_pnl = (self.engine.balance - prev_balance) / prev_total_capital  

        # ✅ 평가손익 계산 (현재 보유 포지션의 평가수익률)
        unrealized_pnl = 0
        if self.engine.position and self.engine.entry_price is not None:
            unrealized_pnl = (current_price - self.engine.entry_price) / self.engine.entry_price  

        # ✅ 최종 보상 계산: 실현손익에 더 높은 가중치 부여
        reward = 0.8 * realized_pnl + 0.2 * unrealized_pnl  
        
        done = (self.current_time >= self.end_time)
        obs = self._get_observation() if not done else np.zeros(self.observation_space.shape, dtype=np.float32)
        info = {"current_time": self.current_time, "balance": self.engine.balance}

        # print(f"지급보상: {reward} 현재가격: {current_price}")
        return obs, reward, done, info
    
    def reset(self):
        self.current_time = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M:%S")
        for timeframe in ["1m", "5m", "1h"]:
            data = load_backtest_data(self.client, self.symbol, timeframe, self.start_date, limit=300, futures=False)
            self.data_dict[self.symbol][timeframe] = cal_indicator(data)
        self.engine = BacktestEngine(initial_balance=self.initial_balance)
        return self._get_observation()
    
    def render(self, mode="human"):
        print(f"시간: {self.current_time}, 잔고: {self.engine.balance}, 포지션: {self.engine.position}")
