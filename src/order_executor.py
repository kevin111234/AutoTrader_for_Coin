import time

class Order:
    def __init__(self, client):
        self.client = client

    def _place_order(self, symbol, side, quantity, order_type="MARKET", **kwargs):
        """
        실제 Binance API를 호출하여 주문을 실행.
        """
        try:
            print(f"주문 실행 중: {side} {quantity} {symbol} {order_type}")
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                **kwargs
            )
            print(f"주문 완료: {order}")
            return order
        except Exception as e:
            print(f"주문 실패: {e}")
            return None

    def _check_order_status(self, symbol, order_id):
        """
        주문 상태를 확인하는 함수.
        """
        try:
            order_status = self.client.get_order(symbol=symbol, orderId=order_id)
            print(f"주문 상태: {order_status}")
            return order_status
        except Exception as e:
            print(f"주문 상태 확인 실패: {e}")
            return None

    def buy(self, symbol, quantity):
        """
        현물 매수 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def sell(self, symbol, quantity):
        """
        현물 매도 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def L_buy(self, symbol, quantity):
        """
        선물 롱 포지션 진입 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def L_sell(self, symbol, quantity):
        """
        선물 롱 포지션 정리 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def S_buy(self, symbol, quantity):
        """
        선물 숏 포지션 진입 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def S_sell(self, symbol, quantity):
        """
        선물 숏 포지션 정리 후 상태 확인.
        """
        order = self._place_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)  # 10초 대기
            status = self._check_order_status(symbol=symbol, order_id=order_id)
            return status
        return None
    
    def place_oco_order(self, symbol, quantity, entry_price, take_profit_percent, stop_loss_percent):
        """
        OCO 주문을 생성하여 익절 및 손절가 설정.
        
        :param symbol: 거래할 심볼 (예: "BTCUSDT")
        :param quantity: 거래 수량
        :param entry_price: 진입 가격
        :param take_profit_percent: 익절 비율 (예: 3% → 3)
        :param stop_loss_percent: 손절 비율 (예: 2% → 2)
        """
        # 익절 가격과 손절 가격 계산
        take_profit_price = entry_price * (1 + take_profit_percent / 100)
        stop_loss_price = entry_price * (1 - stop_loss_percent / 100)

        try:
            # OCO 주문 실행
            order = self.client.create_oco_order(
                symbol=symbol,
                side="SELL",
                quantity=quantity,
                price=round(take_profit_price, 2),  # 익절 지정가
                stopPrice=round(stop_loss_price, 2),  # 손절 트리거가
                stopLimitPrice=round(stop_loss_price * 0.99, 2),  # 손절 지정가
                stopLimitTimeInForce="GTC",  # 손절 주문 지속 시간 설정
                aboveType="STOP_LOSS_LIMIT",  # ✅ Binance API 요구 사항 추가
                belowType="LIMIT_MAKER"  # ✅ Binance API 요구 사항 추가
                )
            print(f"OCO 주문 생성 성공: {order}")
            return order

        except Exception as e:
            print(f"OCO 주문 생성 실패: {e}")
            return None
