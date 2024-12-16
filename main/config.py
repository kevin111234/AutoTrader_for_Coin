import os
import dotenv

class Config():
    def __init__(self):
        print("환경변수 로드 중...")
        binance_access_key = os.getenv("BINANCE_ACCESS_KEY")
        binance_secret_key = os.getenv("BINANCE_SECRET_KEY")
        slack_api_key = os.getenv("SLACK_API_KEY")
        slack_asset_channel_id = os.getenv("SKACK_ASSET_CHANNEL_ID")
        slack_trade_channel_id = os.getenv("SKACK_TRADE_CHANNEL_ID")
        slack_error_channel_id = os.getenv("SKACK_ERROR_CHANNEL_ID")

        seed_money = os.getenv("SEED_MONEY")
        coin_tickers = os.getenv("COIN_TICKERS")
        sto_fut_rate = os.getenv("STO_FUT_RATE")
        leverage_rate = os.getenv("LEVERAGE_RATE")

        print("환경변수 로드 완료")
        
        self.verify(self)

    def verify(self):
        print("환경변수 검증중...")

        print("환경변수 검증 완료!")
