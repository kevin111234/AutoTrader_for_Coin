from config import Config
from binance.client import Client
class Notifier():
    def __init__(self):
        config = Config()
        self.client = Client(config.binance_access_key, config.binance_secret_key)
        self.asset_info = {}
        self.target_coins = ["USDT", ]
        coins = config.coin_tickers.split(" ")  # 환경 변수에서 코인 목록 불러오기
        for i in range(len(coins)):
            self.target_coins.append(coins[i].split("-")[1])

    def get_asset_info(self, symbol):
        """반환 형태 예시
        {
            "USDT-USDT": {
                "free": 1000.0,
                "locked": 0.0,
                "total_quantity": 1000.0,
                "average_buy_price": 0,
                "current_price": 0,
                "profit_rate": 0
            },
            "USDT-ETH": {
                "free": 1.2,
                "locked": 0,
                "total_quantity": 1.2,
                "average_buy_price": 1800.00,
                "current_price": 1900.00,
                "profit_rate": 5.56
            }
        }
        """
        try:
            # 1. 계좌 잔고 조회
            account_info = self.client.get_account()
            balances = account_info['balances']

            # 2. 각 자산별 평균 매수 가격 및 수익률 계산
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total_quantity = free + locked

                # USDT는 보유 수량만 저장
                if asset == "USDT":
                    self.asset_info[f"USDT-{asset}"] = {
                        "free": free,
                        "locked": locked,
                        "total_quantity": total_quantity,
                        "average_buy_price": 0,
                        "current_price": 0,
                        "profit_rate": 0
                    }
                    continue

                # 3. 코인 심볼 형식 변환 (BTC -> USDT-BTC)
                symbol = f"USDT-{asset}"

                # 4. 현재 가격 조회
                current_price = float(self.client.get_symbol_ticker(symbol=f"{asset}USDT")['price'])

                # 5. 보유 수량이 0인 경우 (현재 가격 제외하고 모두 0으로 저장)
                if total_quantity == 0:
                    self.asset_info[symbol] = {
                        "free": 0,
                        "locked": 0,
                        "total_quantity": 0,
                        "average_buy_price": 0,
                        "current_price": current_price,
                        "profit_rate": 0
                    }
                    continue

                # 6. 평균 매수 가격 계산
                trades = self.client.get_my_trades(symbol=f"{asset}USDT")
                total_cost = 0
                total_trade_quantity = 0

                for trade in trades:
                    qty = float(trade['qty'])
                    price = float(trade['price'])
                    commission = float(trade['commission'])

                    total_cost += (qty * price) + commission
                    total_trade_quantity += qty

                avg_buy_price = total_cost / total_trade_quantity if total_trade_quantity > 0 else 0

                # 7. 수익률 계산
                profit_rate = 0
                if avg_buy_price > 0:
                    profit_rate = ((current_price - avg_buy_price) / avg_buy_price) * 100

                # 8. 결과 저장
                self.asset_info[symbol] = {
                    "free": free, # 거래가능 수량
                    "locked": locked, # 거래 진행중인 수량량
                    "total_quantity": total_quantity, # 보유량
                    "average_buy_price": avg_buy_price, # 평균 매수가
                    "current_price": current_price, # 현재가격
                    "profit_rate": profit_rate # 수익률
                }

        except Exception as e:
            print(f"자산 정보 및 수익률 계산 중 오류 발생: {e}")

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
