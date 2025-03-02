import time

class Order:
    def __init__(self, client):
        self.client = client

    def _place_spot_order(self, symbol, side, quantity, order_type="MARKET", **kwargs):
        """
        현물(Spot) API를 통해 주문.
        """
        try:
            print(f"[SPOT] 주문 실행 중: {side} {quantity} {symbol} {order_type}")
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                **kwargs
            )
            print(f"[SPOT] 주문 완료: {order}")
            return order
        except Exception as e:
            print(f"[SPOT] 주문 실패: {e}")
            return None

    def _place_futures_order(self, symbol, side, quantity, order_type="MARKET", **kwargs):
        """
        선물(Futures) API를 통해 주문.
        USDⓂ-M 선물 계좌를 사용하려면 futures_create_order()를 써야 함.
        """
        try:
            print(f"[FUTURES] 주문 실행 중: {side} {quantity} {symbol} {order_type}")
            order = self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                **kwargs
            )
            print(f"[FUTURES] 주문 완료: {order}")
            return order
        except Exception as e:
            print(f"[FUTURES] 주문 실패: {e}")
            return None

    def _check_spot_order_status(self, symbol, order_id):
        try:
            order_status = self.client.get_order(symbol=symbol, orderId=order_id)
            print(f"[SPOT] 주문 상태: {order_status}")
            return order_status
        except Exception as e:
            print(f"[SPOT] 주문 상태 확인 실패: {e}")
            return None

    def _check_futures_order_status(self, symbol, order_id):
        try:
            order_status = self.client.futures_get_order(symbol=symbol, orderId=order_id)
            print(f"[FUTURES] 주문 상태: {order_status}")
            return order_status
        except Exception as e:
            print(f"[FUTURES] 주문 상태 확인 실패: {e}")
            return None

    # -------------------------
    #     Spot 전용 메서드
    # -------------------------
    def buy(self, symbol, quantity):
        """
        현물 매수 후 상태 확인.
        """
        order = self._place_spot_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_spot_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def sell(self, symbol, quantity):
        """
        현물 매도 후 상태 확인.
        """
        order = self._place_spot_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_spot_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    # -------------------------
    #     선물(Futures) 전용 메서드
    # -------------------------
    def L_buy(self, symbol, quantity):
        """
        선물 롱 포지션 진입
        """
        order = self._place_futures_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_futures_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def L_sell(self, symbol, quantity):
        """
        선물 롱 포지션 청산
        """
        order = self._place_futures_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_futures_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def S_buy(self, symbol, quantity):
        """
        선물 숏 포지션 진입
        """
        # 숏 포지션 진입 = 선물에서 side="SELL"
        order = self._place_futures_order(symbol=symbol, side="SELL", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_futures_order_status(symbol=symbol, order_id=order_id)
            return status
        return None

    def S_sell(self, symbol, quantity):
        """
        선물 숏 포지션 청산
        """
        # 숏 포지션 청산 = 선물에서 side="BUY"
        order = self._place_futures_order(symbol=symbol, side="BUY", quantity=quantity)
        if order is not None:
            order_id = order.get("orderId")
            time.sleep(10)
            status = self._check_futures_order_status(symbol=symbol, order_id=order_id)
            return status
        return None
