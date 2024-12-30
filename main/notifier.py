from config import Config
from binance.client import Client
from slack_sdk import WebClient

class Notifier():
    def __init__(self):
        config = Config()
        self.client = Client(config.binance_access_key, config.binance_secret_key)
        self.slack = WebClient(token=self.config.slack_api_token)
        self.asset_info = {}
        self.target_coins = ["USDT", ]
        coins = config.coin_tickers.split(" ")  # 환경 변수에서 코인 목록 불러오기
        for i in range(len(coins)):
            self.target_coins.append(coins[i])

    def get_asset_info(self, symbol):
        """반환 형태 예시
        {
            "USDT": {
                "free": 1000.0,
                "locked": 0.0,
                "total_quantity": 1000.0,
                "average_buy_price": 0,
                "current_price": 0,
                "profit_rate": 0
            },
            "ETH": {
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
                if asset not in self.target_coins:
                    continue  # target_coins에 없는 자산은 건너뛰기
                free = float(balance['free'])
                locked = float(balance['locked'])
                total_quantity = free + locked

                # USDT는 보유 수량만 저장
                if asset == "USDT":
                    self.asset_info[asset] = {
                        "free": free,
                        "locked": locked,
                        "total_quantity": total_quantity,
                        "average_buy_price": 0,
                        "current_price": 0,
                        "profit_rate": 0,
                    }
                    continue

                # 4. 현재 가격 조회
                current_price = float(self.client.get_symbol_ticker(f"{asset}USDT")['price'])

                # 5. 보유 수량이 0인 경우 (현재 가격 제외하고 모두 0으로 저장)
                if total_quantity == 0:
                    self.asset_info[asset] = {
                        "free": 0,
                        "locked": 0,
                        "total_quantity": 0,
                        "average_buy_price": 0,
                        "current_price": current_price,
                        "profit_rate": 0
                    }
                    continue

                # 6. 평균 매수 가격 계산
                trades = self.client.get_my_trades(f"{asset}USDT")
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
                    "locked": locked, # 거래 진행중인 수량
                    "total_quantity": total_quantity, # 보유량
                    "average_buy_price": avg_buy_price, # 평균 매수가
                    "current_price": current_price, # 현재가격
                    "profit_rate": profit_rate, # 수익률
                }

        except Exception as e:
            print(f"자산 정보 및 수익률 계산 중 오류 발생: {e}")
    
    def get_limit_amount(self):
        try:
            # 1. USDT 잔액 조회
            usdt_balance = float(self.asset_info.get("USDT", {}).get("total_quantity", 0))

            # 2. 코인별 현재가 및 자산 가치 계산
            coin_values = {}
            total_asset = usdt_balance

            for symbol in self.target_coins:
                # USDT는 제외하고 다른 코인만 처리
                if symbol == "USDT":
                    continue

                # 코인별 현재 가격 및 보유량 조회
                coin_info = self.asset_info.get(symbol, {})
                current_price = float(coin_info.get("current_price", 0))
                total_amount = float(coin_info.get("total_quantity", 0))

                # 코인의 총 가치(USDT 환산) 계산
                coin_value = total_amount * current_price
                coin_values[symbol] = coin_value
                total_asset += coin_value

            # 3. 코인 개수 및 자산 균등 배분 금액 계산
            coin_count = len(self.target_coins) - 1  # USDT 제외
            if coin_count == 0:
                raise ValueError("코인 개수가 0입니다")

            target_amount_per_coin = total_asset / coin_count

            # 4. 매수 가능 금액 계산
            limit_amounts = {}
            negative_sum = 0
            negative_count = 0

            for symbol in self.target_coins:
                if symbol == "USDT":
                    continue

                # 목표 금액에서 보유 자산 가치 차감
                limit_amount = target_amount_per_coin - coin_values.get(symbol, 0)

                # 초과 보유 시 0으로 설정하고, 초과분을 누적
                if limit_amount < 0:
                    negative_sum += abs(limit_amount)
                    negative_count += 1
                    limit_amounts[symbol] = 0
                else:
                    limit_amounts[symbol] = limit_amount

            # 5. 초과 자산을 다른 코인들에게 분배
            if negative_count > 0 and coin_count > negative_count:
                additional_reduction = negative_sum / (coin_count - negative_count)
                for symbol in self.target_coins:
                    if symbol == "USDT":
                        continue
                    if limit_amounts[symbol] > 0:
                        limit_amounts[symbol] -= additional_reduction

            return limit_amounts

        except Exception as e:
            error_msg = f"주문 가능 금액 조회 중 오류 발생: {str(e)}"
            self.send_slack_message(self.config.slack_error_channel, error_msg)
            print(error_msg)
            return {}

    def send_slack_message(self, channel_id, message):
        try:
            self.slack.chat_postMessage(channel=channel_id, text=message)
        except Exception as e:
            print(f"Error sending message: {e}")

    def send_asset_info(self):
        print("자산 정보 전송 함수를 실행합니다.")

    def send_trade_info(self):
        print("거래 정보 전송 함수를 실행합니다.")

    def send_error_info(self):
        print("에러 정보 전송 함수를 실행합니다.")
