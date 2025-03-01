import pandas as pd
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

class BacktestEngine:
    def __init__(self, initial_balance=1000, trading_fee=0.0004):
        self.initial_balance = initial_balance  # 초기 자본
        self.total_capital = initial_balance  
        self.balance = initial_balance  
        self.peak_balance = initial_balance  
        self.max_drawdown = 0  
        self.position = None  
        self.entry_price = None  
        self.current_weight = 0  
        self.trade_history = []  
        self.trading_fee = trading_fee  
        self.total_holdings = 0  
        self.last_stop_loss_trend = None
        
        # 거래 진입 시 설정한 손절/익절 값을 저장하는 변수 추가
        self.entry_stop_loss = None
        self.entry_take_profit = None

    def get_total_value(self, current_price):
        """현재 모든 자산을 매도할 경우의 총 자산 반환"""
        estimated_value = self.balance + (self.total_holdings * current_price * (1 - self.trading_fee))
        return estimated_value

    def update_mdd(self, current_price):
        """MDD 업데이트 (현재 모든 보유 자산을 매도한 경우의 평가 자산 기준)"""
        total_value = self.get_total_value(current_price)
        self.peak_balance = max(self.peak_balance, total_value)
        drawdown = (self.peak_balance - total_value) / self.peak_balance
        self.max_drawdown = max(self.max_drawdown, drawdown)

    def execute_trade(self, signal, signal_info, trade_type="TRADE"):
        current_price = signal_info["current_price"]

        # 포지션이 열려 있다면, 기존 설정된 손절/익절 값을 사용
        if self.position == "long":
            stop_loss = self.entry_stop_loss
            take_profit = self.entry_take_profit
        else:
            stop_loss = signal_info["stop_loss"]
            take_profit = signal_info["take_profit"]

        signal_weight = signal_info["weight"]
        trade_ratio = signal_weight / 5  

        if self.current_weight == 0:
            self.total_capital = self.balance

        # 포지션이 열려 있는 경우 손절/익절 체크: 이미 진입 시 설정된 값을 사용
        if self.position == "long":
            if current_price <= self.entry_price * stop_loss:
                signal = "sell"
                trade_type = "STOP_LOSS"
                signal_weight = 5  
                self.last_stop_loss_trend = signal_info.get("current_trend_5m", None)
            elif current_price >= self.entry_price * take_profit:
                signal = "sell"
                trade_type = "TAKE_PROFIT"
                signal_weight = 5  

        if signal == "buy":
            if signal_weight > self.current_weight:
                max_buy_amount = self.balance / (current_price * (1 + self.trading_fee))
                buy_amount = (self.total_capital * (trade_ratio - self.current_weight / 5)) / current_price
                buy_amount = min(max_buy_amount, buy_amount)
                if buy_amount < 0.00001:
                    print(f"[{trade_type}] BUY SKIPPED (Insufficient balance) | Balance: {self.balance:.2f}")
                    return

                self.total_holdings += buy_amount
                self.balance -= buy_amount * current_price * (1 + self.trading_fee)
                self.current_weight = signal_weight
                self.position = "long"

                # 거래 진입 시, stop_loss 및 take_profit을 고정하여 저장
                self.entry_stop_loss = signal_info["stop_loss"]
                self.entry_take_profit = signal_info["take_profit"]

                if self.entry_price is not None:
                    total_quantity = self.total_holdings + buy_amount
                    self.entry_price = (self.entry_price * self.total_holdings + current_price * buy_amount) / total_quantity
                else:
                    self.entry_price = current_price

                self.trade_history.append({
                    "type": trade_type,
                    "price": current_price,
                    "qty": buy_amount,
                    "weight": self.current_weight,
                    "pnl": None,
                    "reason": signal_info["reason"],
                    "stop_loss": self.entry_stop_loss,
                    "take_profit": self.entry_take_profit
                })
                print(f"[{trade_type}] BUY {buy_amount:.6f} at ${current_price:.2f} | weight: {self.current_weight} | holdings: {self.total_holdings:.6f} | balance: ${self.balance:.2f}")
                print(signal_info["reason"])

        elif signal == "sell" and self.entry_price is not None:
            if self.position == "long" and self.current_weight > 0 and signal_weight > 0:
                sell_weight = min(self.current_weight, signal_weight)
                sell_amount = max(self.total_holdings * (sell_weight / self.current_weight), 0.00001)
                if sell_amount > self.total_holdings:
                    sell_amount = self.total_holdings
                self.total_holdings -= sell_amount
                profit = (current_price - self.entry_price) / self.entry_price * 100
                PnL = (current_price - self.entry_price) * sell_amount
                self.balance += sell_amount * current_price * (1 - self.trading_fee)
                self.current_weight -= sell_weight

                self.trade_history.append({
                    "type": trade_type,
                    "price": current_price,
                    "qty": sell_amount,
                    "weight": self.current_weight,
                    "pnl": profit,
                    "reason": signal_info["reason"],
                    "stop_loss": self.entry_stop_loss,
                    "take_profit": self.entry_take_profit
                })
                print(f"[{trade_type}] SELL {sell_amount:.6f} at ${current_price:.2f} | profit: {profit:.2f}% | PnL: ${PnL:.2f} | weight: {signal_weight} | holdings: {self.total_holdings:.6f} | balance: ${self.balance:.2f}")
                print(signal_info["reason"])
                # 포지션이 완전히 청산되면, 진입 시 손절/익절 값 초기화
                if self.current_weight == 0:
                    self.position = None
                    self.entry_price = None
                    self.entry_stop_loss = None
                    self.entry_take_profit = None
                    if self.total_holdings > 0:
                        self.balance += self.total_holdings * current_price * (1 - self.trading_fee)
                        self.total_holdings = 0
                    else:
                        self.total_holdings = 0
        self.update_mdd(current_price)

    def get_trade_history(self):
        df = pd.DataFrame(self.trade_history)
        df["pnl"] = df["pnl"].fillna("-")  
        return df

    def get_mdd(self):
        """최대 손실(MDD) 반환"""
        return self.max_drawdown * 100  # 퍼센트 단위 변환
    
    def save_trade_history(self, filename="backtest_results.csv"):
        """거래 기록을 CSV 파일로 저장"""
        df = self.get_trade_history()
        df.to_csv(filename, index=False)
        print(f"📁 거래 내역 저장 완료: {filename}")