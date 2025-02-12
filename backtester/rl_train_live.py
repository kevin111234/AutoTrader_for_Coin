import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from stable_baselines3 import TD3
from backtester.rl_trading_live_env import RLTradingLiveEnv

# 시작/종료 시간 및 에피소드 스텝 설정
start_date = "2023-01-01 00:00:00"
end_date = "2024-01-01 00:00:00"
env = RLTradingLiveEnv(start_date=start_date, end_date=end_date, max_steps=500, symbol="BTC")

# TD3 알고리즘 (연속 액션 지원) 사용 – signal, weight, take_profit, stop_loss 모두 에이전트가 결정
model = TD3("MlpPolicy", env, verbose=1)
model.learn(total_timesteps=100000)
model.save("td3_rl_live_trading_model")
