import sys
import os

# 프로젝트 루트 디렉토리의 절대 경로를 구함
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.config import Config
from binance.client import Client
from slack_sdk import WebClient

class Notifier():
    def __init__(self):
        self.config = Config()
        self.client = Client(self.config.binance_access_key, self.config.binance_secret_key)
        self.slack = WebClient(token=self.config.slack_api_key)
        self.asset_info = {}
        self.futures_asset_info = {}
        self.target_coins = ["USDT", ]
        coins = self.config.coin_tickers.split(" ")  # 환경 변수에서 코인 목록 불러오기
        for i in range(len(coins)):
            self.target_coins.append(coins[i])
        self.future_target_coins = ["USDT", ]
        future_coins = self.config.futures_coin_tickers.split(" ")
        for j in range(len(future_coins)):
            self.future_target_coins.append(future_coins[j])

    def get_asset_info(self):
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
                current_price = float(self.client.get_symbol_ticker(symbol = (f"{asset}USDT") )['price'])

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
                self.asset_info[asset] = {
                    "free": free, # 거래가능 수량
                    "locked": locked, # 거래 진행중인 수량
                    "total_quantity": total_quantity, # 보유량
                    "average_buy_price": avg_buy_price, # 평균 매수가
                    "current_price": current_price, # 현재가격
                    "profit_rate": profit_rate, # 수익률
                }

        except Exception as e:
            print(f"자산 정보 및 수익률 계산 중 오류 발생: {e}")

    def get_futures_asset_info(self):
        """
        선물 계좌 정보를 조회하고 self.asset_info에 저장.
        """
        try:
            # 1. 선물 계좌 잔액 조회
            futures_balances = self.client.futures_account_balance()

            for balance in futures_balances:
                asset = balance['asset']
                if asset not in self.future_target_coins:
                    continue  # future_target_coins에 없는 자산은 건너뛰기
                
                balance_amount = float(balance['balance'])
                withdraw_available = float(balance.get('withdrawAvailable', balance['balance']))

                # 2. 잔액 정보 저장
                self.futures_asset_info[asset] = {
                    "balance": balance_amount,
                    "withdraw_available": withdraw_available,
                    "positions": []
                }

            # 3. 선물 포지션 정보 조회
            futures_positions = self.client.futures_position_information()

            for position in futures_positions:
                symbol = position['symbol']
                if symbol.replace("USDT", "") not in self.future_target_coins:
                    continue  # 선물 대상 코인에 없는 경우 스킵

                position_amt = float(position['positionAmt'])
                entry_price = float(position['entryPrice'])
                unrealized_profit = float(position['unRealizedProfit'])
                leverage = int(position['leverage'])

                if position_amt != 0:  # 포지션이 있을 경우만 저장
                    self.futures_asset_info[symbol] = {
                        "position_amt": position_amt,
                        "entry_price": entry_price,
                        "unrealized_profit": unrealized_profit,
                        "leverage": leverage,
                        "margin_type": position['marginType']
                    }

        except Exception as e:
            print(f"선물 계좌 정보 조회 중 오류 발생: {e}")

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
            self.send_slack_message(self.config.slack_error_channel_id, error_msg)
            print(error_msg)
            return {}

    def futures_get_limit_amount(self):
        """
        선물 계좌의 투자 한도를 계산하는 함수.
        """
        try:
            # 1. USDT 잔액 조회 (선물 계좌)
            usdt_balance = float(self.futures_asset_info.get("USDT", {}).get("balance", 0))
            available_balance = float(self.futures_asset_info.get("USDT", {}).get("withdraw_available", 0))

            # 2. 선물 계좌의 포지션 가치 계산
            coin_values = {}
            total_asset = usdt_balance

            for symbol in self.future_target_coins:
                if symbol == "USDT":
                    continue

                # 선물 포지션 정보 가져오기
                position_info = self.futures_asset_info.get(f"{symbol}USDT", {})
                position_amt = float(position_info.get("position_amt", 0))
                entry_price = float(position_info.get("entry_price", 0))

                # 포지션 크기 및 가치 계산
                position_value = abs(position_amt) * entry_price
                coin_values[symbol] = position_value
                total_asset += position_value

            # 3. 코인 개수 및 균등 배분 금액 계산
            coin_count = len(self.future_target_coins) - 1  # USDT 제외
            if coin_count == 0:
                raise ValueError("선물 대상 코인이 없습니다.")

            target_amount_per_coin = total_asset / coin_count

            # 4. 매수/매도 가능 금액 계산
            limit_amounts = {}
            negative_sum = 0
            negative_count = 0

            for symbol in self.future_target_coins:
                if symbol == "USDT":
                    continue

                # 목표 금액에서 현재 포지션 가치 차감
                limit_amount = target_amount_per_coin - coin_values.get(symbol, 0)

                # 초과 보유 시 0으로 설정하고, 초과분을 누적
                if limit_amount < 0:
                    negative_sum += abs(limit_amount)
                    negative_count += 1
                    limit_amounts[symbol] = 0
                else:
                    limit_amounts[symbol] = limit_amount

            # 5. 초과 포지션을 다른 코인들에게 분배
            if negative_count > 0 and coin_count > negative_count:
                additional_reduction = negative_sum / (coin_count - negative_count)
                for symbol in self.future_target_coins:
                    if symbol == "USDT":
                        continue
                    if limit_amounts[symbol] > 0:
                        limit_amounts[symbol] -= additional_reduction

            return limit_amounts

        except Exception as e:
            error_msg = f"선물 주문 가능 금액 계산 중 오류 발생: {str(e)}"
            print(error_msg)
            return {}

    def send_slack_message(self, channel_id, message):
        try:
            self.slack.chat_postMessage(channel=channel_id, text=message)
        except Exception as e:
            print(f"Error sending message: {e}")

    # 자산 정보 전송 함수
    def send_asset_info(self, spot_limit_amount, futures_limit_amount, position_tracker=""):
        """
        현물 및 선물 계좌 정보를 Slack에 전송하는 함수.
        """
        try:
            # 1. 현물 계좌 정보
            usdt_balance = self.asset_info.get("USDT", {}).get("total_quantity", 0)
            total_spot_asset = usdt_balance

            spot_message = f"""
    📊 현물 계좌 자산 현황
    ──────────────
    💰 보유 USDT: {usdt_balance:,.2f} USDT
    ──────────────
    """

            # 현물 자산 정보 추가
            for symbol, info in self.asset_info.items():
                if symbol == "USDT" or symbol not in self.target_coins:
                    continue

                coin_value = info["total_quantity"] * info["current_price"]
                total_spot_asset += coin_value

                spot_message += f"""
    🪙 {symbol} (현물):
    수량: {info['total_quantity']:.8f}
    거래 가능 수량: {info['free']:.8f}
    거래 중 잠김: {info['locked']:.8f}
    평균매수가: {info['average_buy_price']:,.2f} USDT
    현재가격: {info['current_price']:,.2f} USDT
    평가금액: {coin_value:,.2f} USDT
    수익률: {info['profit_rate']:.2f}%
    코인별 투자한도: {spot_limit_amount.get(symbol, 0):,.2f} USDT
    ──────────────"""

            # 2. 선물 계좌 정보
            usdt_futures_balance = self.futures_asset_info.get("USDT", {}).get("balance", 0)
            total_futures_asset = usdt_futures_balance

            futures_message = f"""
    📊 선물 계좌 자산 현황
    ──────────────
    💰 선물 USDT 잔액: {usdt_futures_balance:,.2f} USDT
    ──────────────
    """

            # 선물 자산 정보 추가
            for symbol in self.future_target_coins:
                if symbol == "USDT":
                    continue
                futures_message += f"""{symbol}투자한도: {futures_limit_amount[symbol]}"""
            for symbol, info in self.futures_asset_info.items():
                if "USDT" not in symbol or symbol.replace("USDT", "") not in self.future_target_coins:
                    continue

                position_value = abs(info.get("position_amt", 0)) * info.get("entry_price", 0)
                total_futures_asset += position_value

                futures_message += f"""
    🪙 {symbol} (선물):
    포지션 크기: {info.get('position_amt', 0):.8f}
    진입가격: {info.get('entry_price', 0):,.2f} USDT
    현재 미실현 손익: {info.get('unrealized_profit', 0):,.2f} USDT
    레버리지: {info.get('leverage', 0)}x
    포지션 가치: {position_value:,.2f} USDT
    선물 투자한도: {futures_limit_amount.get(symbol.replace("USDT", ""), 0):,.2f} USDT
    ──────────────"""

            # 3. 총 자산 및 수익률
            total_asset = total_spot_asset + total_futures_asset
            total_message = f"""
    💵 총 자산 (현물 + 선물): {total_asset:,.2f} USDT
    💵 전체 수익률: {((float(total_asset) - float(self.config.seed_money)) / float(self.config.seed_money) * 100):.2f}%
    ──────────────
    """

            # 4. 최종 메시지 작성
            full_message = spot_message + position_tracker + futures_message + total_message

            # 5. 메시지 전송
            self.send_slack_message(self.config.slack_asset_channel_id, full_message)

        except Exception as e:
            print(f"자산 보고 오류: {str(e)}")
