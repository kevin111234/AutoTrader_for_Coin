import os
from dotenv import load_dotenv

class Config():
    def __init__(self):
        print("환경변수 로드 중...")
        load_dotenv()
        self.binance_access_key = os.getenv("BINANCE_ACCESS_KEY")
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.slack_api_key = os.getenv("SLACK_API_KEY")
        self.slack_asset_channel_id = os.getenv("SLACK_ASSET_CHANNEL_ID")
        self.slack_trade_channel_id = os.getenv("SLACK_TRADE_CHANNEL_ID")
        self.slack_error_channel_id = os.getenv("SLACK_ERROR_CHANNEL_ID")

        self.seed_money = os.getenv("SEED_MONEY")
        self.coin_tickers = os.getenv("COIN_TICKERS")
        self.sto_fut_rate = os.getenv("STO_FUT_RATE")
        self.leverage_rate = os.getenv("LEVERAGE_RATE")

        print("환경변수 로드 완료")
        
        self.verify()

    def verify(self):
        print("환경변수 검증중...")
        if not self.binance_access_key:
            raise ValueError("binance access key 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.binance_secret_key:
            raise ValueError("binance secret key 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.slack_api_key:
            raise ValueError("slack api key환경변수가 제대로 설정되지 않았습니다.")
        elif not self.slack_asset_channel_id:
            raise ValueError("slack asset channel id 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.slack_trade_channel_id:
            raise ValueError("slack trade channel id 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.slack_error_channel_id:
            raise ValueError("slack error channel id 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.seed_money:
            raise ValueError("seed money 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.coin_tickers:
            raise ValueError("coin tickers 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.sto_fut_rate:
            raise ValueError("sto fut rate 환경변수가 제대로 설정되지 않았습니다.")
        elif not self.leverage_rate:
            raise ValueError("leverage rate 환경변수가 제대로 설정되지 않았습니다.")
        else:
            print("환경변수 검증 완료!")
