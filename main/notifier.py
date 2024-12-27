from config import Config
from binance.client import Client
class Notifier():
    def __init__(self):
        config = Config()
        self.client = Client(config.binance_access_key, config.binance_secret_key)
        self.target_coins = ["USDT", ]
        coins = config.coin_tickers.split(" ")  # 환경 변수에서 코인 목록 불러오기
        for i in range(len(coins)):
            self.target_coins.append(coins[i].split("-")[1])

    def get_asset_info(self):
        try:
            account_info = self.client.get_account()
            balances = account_info['balances']

            asset_info = {}
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])

                # 조회할 코인 및 USDT만 필터링
                if asset in self.target_coins and (free > 0 or locked > 0):
                    asset_info[asset] = {
                        "free": free,
                        "locked": locked
                    }
            return asset_info

        except Exception as e:
            print(f"자산 정보 불러오기 중 오류 발생: {e}")
            return None

    def get_limit_amount():
        print("투자 한도 불러오기 함수를 실행합니다.")

    def send_slack_message():
        print("slack 메시지 전송 함수를 실행합니다.")

    def send_asset_info():
        print("자산 정보 전송 함수를 실행합니다.")

    def send_trade_info():
        print("거래 정보 전송 함수를 실행합니다.")

    def send_error_info():
        print("에러 정보 전송 함수를 실행합니다.")
