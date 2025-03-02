import math
from decimal import Decimal, ROUND_DOWN

class TradeManager:
    def __init__(self, order_executor, notifier, config):
        self.order = order_executor
        self.notifier = notifier
        self.config = config

    def _truncate_by_step_size(self, value, step):
        """
        float value와 step_size(예: 0.0001)가 주어졌을 때,
        value를 step_size 배수에 맞춰 내림(truncation) 처리하여 float로 반환.
        """
        value_dec = Decimal(str(value))
        step_dec = Decimal(str(step))
        truncated = value_dec.quantize(step_dec, rounding=ROUND_DOWN)
        return float(truncated)

    # --------------------------------------------------------
    #                   현물(Spot) 로직
    # --------------------------------------------------------
    def process_spot_trade(self, ticker, signal, spot_limit_amount, buy_sell_status, symbol_info):
        """
        스팟(현물) 매매 로직
        :param ticker: 예) "BTC"
        :param signal: 예) {
                            "signal": "buy" / "sell" / "hold",
                            "current_price": float,
                            "weight": int(분할매매단계),
                            "reason": str,
                            "stop_loss": float(손절%),
                            "take_profit": float(익절%)
                          }
        :param spot_limit_amount: 코인별 매매 한도 (USDT 기준)
        :param buy_sell_status: { ticker: {"buy_stage": int}, ... } - 현재 매수단계 추적
        :param symbol_info: { "stepSize": float, "minQty": float } - 바이낸스 거래 규칙 정보
        """
        try:
            signal_type = signal["signal"]
            current_price = signal.get("current_price", 0.0)

            step_size = symbol_info["stepSize"]
            min_qty   = symbol_info["minQty"]

            # ----------------------
            #   매수 시그널
            # ----------------------
            if signal_type == "buy":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage  = signal.get("weight", 1)

                # 현재 단계 < 목표 단계라면, (current_stage+1 ~ target_stage) 순차 매수
                if target_stage > current_stage:
                    for stage in range(current_stage + 1, target_stage + 1):
                        entry_price  = current_price
                        raw_quantity = (int(spot_limit_amount.get(ticker, 0)) * 0.19) / entry_price

                        # step_size 규칙 맞춰 truncate
                        quantity = self._truncate_by_step_size(raw_quantity, step_size)

                        # 최소 주문수량 미만이면 스킵
                        if quantity < min_qty:
                            print(f"{ticker} {stage}단계 매수 실패: "
                                  f"최소 주문량({min_qty}) 미만 (계산수량={quantity})")
                            continue

                        print(f"{ticker} {stage}단계 매수 진행: 수량 {quantity}")
                        status = self.order.buy(symbol=f"{ticker}USDT", quantity=quantity)

                        if status and status.get("status") == "FILLED":
                            print(f"{ticker} {stage}단계 매수 성공")
                            message = (
                                f"매수 진행 신호 발생\n"
                                f"- 매수 비중(단계): {signal.get('weight')}\n"
                                f"- 매수 근거: {signal.get('reason')}\n"
                                f"- 손절 퍼센트: {signal.get('stop_loss')}\n"
                                f"- 익절 퍼센트: {signal.get('take_profit')}"
                            )
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                            # 스테이지 갱신
                            buy_sell_status[ticker]["buy_stage"] = stage

                        else:
                            print(f"{ticker} {stage}단계 매수 실패: 주문 상태 미확인")
                            self.notifier.send_slack_message(
                                self.config.slack_error_channel_id,
                                f"{ticker} {stage}단계 매수 실패: 주문 상태 확인 필요"
                            )

            # ----------------------
            #   매도 시그널
            # ----------------------
            elif signal_type == "sell":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage  = signal.get("weight", 1)

                # 보유단계 0이면 매도 불가능
                if current_stage == 0:
                    print(f"{ticker}: 매도 신호 발생했으나 보유 단계=0, 매도 스킵")
                    return

                # (1) 부분매도
                if target_stage <= current_stage:
                    raw_quantity = ((spot_limit_amount.get(ticker, 0) * 0.19) * target_stage) / current_price
                    quantity = self._truncate_by_step_size(raw_quantity, step_size)

                    if quantity >= min_qty:
                        print(f"{ticker} {target_stage}단계 매도 진행: 수량 {quantity}")
                        message = (
                            f"매도 진행 신호 발생\n"
                            f"- 매도 비중(단계): {signal.get('weight')}\n"
                            f"- 매도 근거: {signal.get('reason')}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            # 현재 단계에서 target_stage 만큼 소진
                            buy_sell_status[ticker]["buy_stage"] -= target_stage
                            if buy_sell_status[ticker]["buy_stage"] < 0:
                                buy_sell_status[ticker]["buy_stage"] = 0
                    else:
                        print(f"{ticker} 매도 실패: 최소 주문량({min_qty}) 미만 (수량={quantity})")

                # (2) 목표 스테이지 > 현재 스테이지 => 전량 매도
                else:
                    raw_quantity = self.notifier.asset_info[ticker]["free"]
                    quantity = self._truncate_by_step_size(raw_quantity, step_size)

                    if quantity >= min_qty:
                        print(f"{ticker} 전량 매도 진행: 수량 {quantity}")
                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            buy_sell_status[ticker]["buy_stage"] = 0
                            message = f"{ticker} 전량 매도 성공"
                            print(message)
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                    else:
                        message = f"{ticker} 전량 매도 실패: 최소 주문량({min_qty}) 미만 (수량={quantity})"
                        print(message)
                        self.notifier.send_slack_message(
                            self.config.slack_error_channel_id,
                            message
                        )

            # ----------------------
            #  그 외 (Hold 등)
            # ----------------------
            else:
                print("Hold (스팟)")

        except Exception as e:
            print(f"스팟 거래 처리 중 오류 발생: {e}")

    # --------------------------------------------------------
    #                   선물(Futures) 로직
    # --------------------------------------------------------

    def _truncate_to_3decimals(self, value):
        """
        value를 소수점 셋째 자리까지만 유지하고 내림 처리함 (0.001 step).
        예: 0.0021234 -> 0.002
            0.0029999 -> 0.002
        """
        step_dec = Decimal("0.001")
        value_dec = Decimal(str(value))
        truncated = value_dec.quantize(step_dec, rounding=ROUND_DOWN)
        return float(truncated)

    def process_futures_trade(self, ticker, signal, futures_limit_amount, futures_status, symbol_info):
        """
        선물 거래 로직
        signal["signal"] 예시:
          - "L_buy"  : 롱 진입(추가 진입 포함)
          - "L_sell" : 롱 청산
          - "S_buy"  : 숏 진입(추가 진입 포함)
          - "S_sell" : 숏 청산
          - "Hold"   : 아무 것도 안 함
        """
        try:
            leverage = self.config.futures_leverage
            weight = signal["weight"]

            current_price = signal.get("current_price", 0.0)
            signal_type   = signal["signal"]
            reason        = signal.get("reason", "No reason")

            current_pos   = futures_status[ticker].get("position")   # "LONG" / "SHORT" / None
            current_stage = futures_status[ticker].get("stage", 0)
            current_qty   = futures_status[ticker].get("quantity", 0.0)

            step_size     = symbol_info["stepSize"]
            min_qty       = symbol_info["minQty"]

            # --------------------------
            #    롱 진입 (L_buy)
            # --------------------------
            if signal_type == "L_buy":
                # (1) SHORT 포지션이면 자동 청산 후 롱 전환
                if current_pos == "SHORT":
                    print(f"{ticker}: 현재 숏 포지션 -> 자동으로 숏 청산 후 롱 전환 시도")
                    short_qty = current_qty
                    if short_qty >= min_qty:
                        close_status = self.order.S_sell(symbol=f"{ticker}USDT", quantity=short_qty)
                        if close_status and close_status.get("status") == "FILLED":
                            print(f"{ticker} 숏 포지션 청산 성공, 롱 전환 진행")
                            futures_status[ticker]["position"] = None
                            futures_status[ticker]["stage"]    = 0
                            futures_status[ticker]["quantity"] = 0
                        else:
                            print(f"{ticker} 숏 청산 실패 -> 롱 진입 중단")
                            return
                    else:
                        print(f"{ticker} 숏 포지션 수량({short_qty})이 min_qty({min_qty}) 미만 -> 청산 불가, 롱 진입 중단")
                        return

                # (2) 현재 포지션이 LONG이면 추가 진입, None이면 신규 진입
                raw_quantity = (int(futures_limit_amount.get(ticker, 0)) * leverage * 0.19 * weight) / current_price
                quantity = self._truncate_to_3decimals(raw_quantity)

                if quantity < min_qty:
                    print(f"{ticker} 롱 진입 실패: 최소 주문량({min_qty}) 미만 (계산수량={quantity})")
                    return

                status = self.order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 롱 진입/추가진입 성공!")
                    message = (
                        f"[선물] {ticker} 롱 진입 성공\n"
                        f"- 수량: {quantity}\n"
                        f"- 현재가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                    futures_status[ticker]["position"] = "LONG"
                    futures_status[ticker]["stage"]    = current_stage + 1
                    futures_status[ticker]["quantity"] = current_qty + quantity
                else:
                    print(f"{ticker} 롱 진입 실패")

            # --------------------------
            #    롱 청산 (L_sell)
            # --------------------------
            elif signal_type == "L_sell":
                if current_pos != "LONG":
                    print(f"{ticker}: 롱 포지션 없음 -> 청산 불가")
                    return

                # (1) partial or full close
                #    - 현 스테이지 current_stage가 0~n
                #    - 들어온 weight만큼만 청산
                if weight >= current_stage:
                    # 전량 청산
                    close_qty = current_qty
                    final_stage = 0
                else:
                    # 부분 청산
                    # 단계비율 = weight / current_stage
                    close_ratio = weight / current_stage
                    close_qty = current_qty * close_ratio
                    final_stage = current_stage - weight

                # stepSize 반올림
                close_qty = self._truncate_to_3decimals(close_qty)

                if close_qty < min_qty:
                    print(f"{ticker} 롱 부분청산 실패: 최소 주문단위({min_qty}) 미만 (close_qty={close_qty})")
                    return

                status = self.order.L_sell(symbol=f"{ticker}USDT", quantity=close_qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 롱 청산 성공 (수량={close_qty})")
                    message = (
                        f"[선물] {ticker} 롱 청산(부분) 성공\n"
                        f"- 청산 수량: {close_qty}\n"
                        f"- 청산가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                    # 포지션 정보 갱신
                    new_qty = current_qty - close_qty
                    # 주의: 부동소수점
                    if new_qty < 1e-12:
                        new_qty = 0.0
                    
                    futures_status[ticker]["quantity"] = new_qty
                    futures_status[ticker]["stage"]    = final_stage
                    if new_qty <= 0:
                        # 전량 청산됐으면 포지션 해제
                        futures_status[ticker]["position"] = None
                else:
                    print(f"{ticker} 롱 청산 실패")

            # --------------------------
            #    숏 진입 (S_buy)
            # --------------------------
            elif signal_type == "S_buy":
                # (1) LONG 포지션이면 자동 청산 후 숏 전환
                if current_pos == "LONG":
                    print(f"{ticker}: 현재 롱 포지션 -> 자동으로 롱 청산 후 숏 전환 시도")
                    long_qty = current_qty
                    if long_qty >= min_qty:
                        close_status = self.order.L_sell(symbol=f"{ticker}USDT", quantity=long_qty)
                        if close_status and close_status.get("status") == "FILLED":
                            print(f"{ticker} 롱 포지션 청산 성공, 숏 전환 진행")
                            futures_status[ticker]["position"] = None
                            futures_status[ticker]["stage"]    = 0
                            futures_status[ticker]["quantity"] = 0
                        else:
                            print(f"{ticker} 롱 청산 실패 -> 숏 진입 중단")
                            return
                    else:
                        print(f"{ticker} 롱 포지션 수량({long_qty})이 min_qty({min_qty}) 미만 -> 청산 불가, 숏 진입 중단")
                        return

                # (2) 현재 포지션이 SHORT면 추가 진입, None이면 신규 진입
                raw_quantity = (int(futures_limit_amount.get(ticker, 0)) * leverage * weight * 0.19) / current_price
                quantity = self._truncate_to_3decimals(raw_quantity)

                if quantity < min_qty:
                    print(f"{ticker} 숏 진입 실패: 최소 주문량({min_qty}) 미만 (계산수량={quantity})")
                    return

                status = self.order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 숏 진입/추가진입 성공!")
                    message = (
                        f"[선물] {ticker} 숏 진입 성공\n"
                        f"- 수량: {quantity}\n"
                        f"- 현재가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                    futures_status[ticker]["position"] = "SHORT"
                    futures_status[ticker]["stage"]    = current_stage + 1
                    futures_status[ticker]["quantity"] = current_qty + quantity
                else:
                    print(f"{ticker} 숏 진입 실패")

            # --------------------------
            #    숏 청산 (S_sell)
            # --------------------------
            elif signal_type == "S_sell":
                if current_pos != "SHORT":
                    print(f"{ticker}: 숏 포지션 없음 -> 청산 불가")
                    return

                # 스테이지 계산
                if weight >= current_stage:
                    # 전량 청산
                    close_qty = current_qty
                    final_stage = 0
                else:
                    # 부분 청산
                    close_ratio = weight / current_stage
                    close_qty = current_qty * close_ratio
                    final_stage = current_stage - weight

                close_qty = self._truncate_to_3decimals(close_qty)
                if close_qty < min_qty:
                    print(f"{ticker} 숏 부분청산 실패: 최소단위({min_qty}) 미만 (close_qty={close_qty})")
                    return

                status = self.order.S_sell(symbol=f"{ticker}USDT", quantity=close_qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 숏 청산 성공 (수량={close_qty})")
                    message = (
                        f"[선물] {ticker} 숏 청산(부분) 성공\n"
                        f"- 청산 수량: {close_qty}\n"
                        f"- 청산가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                    new_qty = current_qty - close_qty
                    if new_qty < 1e-12:
                        new_qty = 0.0

                    futures_status[ticker]["quantity"] = new_qty
                    futures_status[ticker]["stage"]    = final_stage
                    if new_qty <= 0:
                        # 전량 청산
                        futures_status[ticker]["position"] = None
                else:
                    print(f"{ticker} 숏 청산 실패")

            # --------------------------
            #    그 외(Hold 등)
            # --------------------------
            else:
                print("Hold (선물)")

        except Exception as e:
            print(f"선물 거래 처리 중 오류 발생: {e}")
