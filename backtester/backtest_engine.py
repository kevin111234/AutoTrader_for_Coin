import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_DOWN


class BacktestEngine:
    def __init__(self, initial_balance=1000, trading_fee=0.003):
        self.initial_balance = initial_balance  # 초기 자본
        self.total_capital = initial_balance  # 전체 자산 (기준값)
        self.balance = initial_balance  # 현재 잔고 (매매 후 변경)
        self.position = None  # 현재 포지션 (None, "long", "short")
        self.entry_price = None  # 진입 가격
        self.current_weight = 0  # 현재 보유 weight (0~5)
        self.trade_history = []  # 거래 내역 저장
        self.trading_fee = trading_fee  # 거래 수수료
        self.total_holdings = 0  # 현재 보유한 BTC 수량

    def execute_trade(self, signal, signal_info, trade_type="TRADE"):
        current_price = signal_info["current_price"]
        stop_loss = signal_info["stop_loss"]
        take_profit = signal_info["take_profit"]
        signal_weight = signal_info["weight"]
        trade_ratio = signal_weight / 5  

        # 전체 자산 기준 매매 비율 설정
        if self.current_weight == 0:
            self.total_capital = self.balance  # 초기 잔고를 전체 자산으로 설정

        # ✅ 손절 및 익절 체크 (중복 실행 제거)
        if self.position == "long":
            if current_price <= self.entry_price * stop_loss:
                signal = "sell"
                trade_type = "STOP_LOSS"
                signal_weight = 5  # 최대 가중치로 전량 매도

            elif current_price >= self.entry_price * take_profit:
                signal = "sell"
                trade_type = "TAKE_PROFIT"
                signal_weight = 5  # 최대 가중치로 전량 매도

        # ✅ 매매 로직 수행 (손절/익절 반영)
        if signal == "buy":
            if signal_weight > self.current_weight:
                max_buy_amount = self.balance / (current_price * (1 + self.trading_fee))
                buy_amount = (self.total_capital * (trade_ratio - self.current_weight / 5)) / current_price

                # 잔고 초과 방지
                buy_amount = min(max_buy_amount, buy_amount)
                if buy_amount < 0.00001:
                    print(f"[{trade_type}] BUY SKIPPED (Insufficient balance) | Balance: {self.balance:.2f}")
                    return

                # ✅ 총 보유량 업데이트
                self.total_holdings += buy_amount

                # 잔고 차감
                self.balance -= buy_amount * current_price * (1 + self.trading_fee)
                self.current_weight = signal_weight
                self.position = "long"

                # 진입각격 업데이트
                if self.entry_price is not None:
                    total_quantity = self.total_holdings + buy_amount
                    self.entry_price = (self.entry_price * self.total_holdings + current_price * buy_amount) / total_quantity
                else:
                    self.entry_price = current_price


                self.trade_history.append({
                    "type": trade_type, "price": current_price, "qty": buy_amount,
                    "weight": self.current_weight, "pnl": None
                })
                print(f"[{trade_type}] BUY {buy_amount:.6f} at ${current_price:.2f} | 거래비중: {self.current_weight} | 보유량: {self.total_holdings:.6f} | 잔고: ${self.balance:.2f}")

        elif signal == "sell" and self.entry_price is not None:
            if self.position == "long" and self.current_weight > 0 and signal_weight > 0:
                if current_price > self.entry_price*1.01 or trade_type != "TRADE":
                    sell_weight = min(self.current_weight, signal_weight)  # 매도 weight 결정

                    # ✅ 현재 보유한 BTC 수량을 기준으로 매도량 계산
                    sell_amount = max(self.total_holdings * (sell_weight / self.current_weight), 0.00001)

                    # 매도 실행 전에 보유량 체크
                    if sell_amount > self.total_holdings:
                        sell_amount = self.total_holdings  # 보유량 초과 방지

                    # ✅ 총 보유량 업데이트
                    self.total_holdings -= sell_amount

                    # 매도 수행
                    profit = (current_price - self.entry_price) / self.entry_price * 100
                    PnL = (current_price - self.entry_price) * sell_amount
                    self.balance += sell_amount * current_price * (1 - self.trading_fee)
                    self.current_weight -= sell_weight

                    # 포지션 정리 조건 수정
                    if self.current_weight == 0:
                        self.position = None
                        self.entry_price = None
                        if self.total_holdings > 0:
                            self.balance += self.total_holdings * current_price * (1 - self.trading_fee)
                            self.total_holdings = 0
                        else:
                            self.total_holdings = 0  # ✅ 모든 포지션 정리 시 보유량 초기화

                    self.trade_history.append({
                        "type": trade_type, "price": current_price, "qty": sell_amount,
                        "weight": self.current_weight, "pnl": profit
                    })
                    print(f"[{trade_type}] SELL {sell_amount:.6f} at ${current_price:.2f} | 수익률: {profit:.2f}% | 수익액: ${PnL:.2f} | 거래비중: {signal_weight} | 보유수량: {self.total_holdings:.6f} | 잔고: ${self.balance:.2f}")

    def get_trade_history(self):
        df = pd.DataFrame(self.trade_history)
        df["pnl"] = df["pnl"].fillna("-")  
        return df
