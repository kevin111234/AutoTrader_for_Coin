import math

class TradeManager:
    def __init__(self, order_executor, notifier, config):
        self.order = order_executor
        self.notifier = notifier
        self.config = config

    def process_spot_trade(self, ticker, signal, spot_limit_amount, buy_sell_status, symbol_info):
        try:
            if signal["signal"] == "buy":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage = signal.get("weight", 1)
                if target_stage > current_stage:
                    for stage in range(current_stage + 1, target_stage + 1):
                        entry_price = signal["current_price"]
                        quantity = (int(spot_limit_amount.get(ticker, 0)) * 0.2) / entry_price
                        step_size = symbol_info["stepSize"]
                        min_qty = symbol_info["minQty"]
                        quantity = math.floor(quantity / step_size) * step_size

                        if quantity < min_qty:
                            print(f"{ticker} {stage}단계 매수 실패: 최소 주문량({min_qty}) 미만")
                            continue

                        print(f"{ticker} {stage}단계 매수 진행: 수량 {quantity}")
                        status = self.order.buy(symbol=f"{ticker}USDT", quantity=quantity)

                        if status and status.get("status") == "FILLED":
                            print(f"{ticker} {stage}단계 매수 성공")
                            message = (
                                f"매수 진행 신호 발생\n"
                                f"- 매수 비중: {signal.get('weight')}\n"
                                f"- 매수 근거: {signal.get('reason')}\n"
                                f"- 손절 퍼센트: {signal.get('stop_loss')}\n"
                                f"- 익절 퍼센트: {signal.get('take_profit')}"
                            )
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                            buy_sell_status[ticker]["buy_stage"] = stage
                            self.order.place_oco_order(
                                symbol=f"{ticker}USDT",
                                quantity=quantity,
                                entry_price=entry_price,
                                take_profit_percent=signal.get("take_profit"),
                                stop_loss_percent=signal.get("stop_loss")
                            )
                        else:
                            print(f"{ticker} {stage}단계 매수 실패: 주문 상태 미확인")
                            self.notifier.send_slack_message(
                                self.config.slack_error_channel_id,
                                f"{ticker} {stage}단계 매수 실패: 주문 상태 확인 필요"
                            )

            elif signal["signal"] == "sell":
                current_stage = buy_sell_status[ticker]["buy_stage"]
                target_stage = signal.get("weight", 1)
                if current_stage == 0:
                    print(f"{ticker}: 매도 신호 발생했으나 보유 수량 없음, 매도 스킵")
                    return

                if target_stage <= current_stage:
                    quantity = ((spot_limit_amount.get(ticker, 0) * 0.2) * target_stage) / signal["current_price"]
                    step_size = symbol_info["stepSize"]
                    min_qty = symbol_info["minQty"]
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity >= min_qty:
                        print(f"{ticker} {target_stage}단계 매도 진행: 수량 {quantity}")
                        message = (
                            f"매도 진행 신호 발생\n"
                            f"- 매도 비중: {signal.get('weight')}\n"
                            f"- 매도 근거: {signal.get('reason')}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            buy_sell_status[ticker]["buy_stage"] -= target_stage
                            buy_sell_status[ticker]["buy_stage"] = max(0, buy_sell_status[ticker]["buy_stage"])
                    else:
                        print(f"{ticker} 매도 실패: 최소 주문량 미만")
                else:
                    quantity = self.notifier.asset_info[ticker]["free"]
                    step_size = symbol_info["stepSize"]
                    min_qty = symbol_info["minQty"]
                    quantity = math.floor(quantity / step_size) * step_size
                    if quantity >= min_qty:
                        print(f"{ticker} 전량 매도 진행: 수량 {quantity}")
                        status = self.order.sell(symbol=f"{ticker}USDT", quantity=quantity)
                        if status and status.get("status") == "FILLED":
                            buy_sell_status[ticker]["buy_stage"] = 0
                            message = f"{ticker} 전량 매도 성공"
                            print(message)
                            self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                    else:
                        message = f"{ticker} 전량 매도 실패: 최소 주문량 미만"
                        print(message)
                        self.notifier.send_slack_message(
                            self.config.slack_error_channel_id,
                            message
                        )
            else:
                print("Hold")
        except Exception as e:
            print(f"스팟 거래 처리 중 오류 발생: {e}")

    def process_futures_trade(self, ticker, signal, futures_limit_amount, futures_status, symbol_info):
        """
        [선물 거래 로직 + Slack 알림 추가]
        signal["signal"] 값: "L_buy", "L_sell", "S_buy", "S_sell", "Hold" 등
        """
        try:
            current_price = signal.get("current_price")
            signal_type = signal["signal"]
            reason = signal.get("reason", "No reason")
            target_stage = signal.get("weight", 1)

            current_pos = futures_status[ticker].get("position")   # "LONG" / "SHORT" / None
            current_stage = futures_status[ticker].get("stage", 0)
            current_quantity = futures_status[ticker].get("quantity", 0)

            step_size = symbol_info["stepSize"]
            min_qty = symbol_info["minQty"]

            # ---------- 선물 롱 진입 ----------
            if signal_type == "L_buy":
                # 이미 LONG 포지션인지, 없는지 등에 따라 분기
                if current_pos == "LONG":
                    # 추가 진입 로직
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} 롱 추가진입 실패: 최소 주문량({min_qty}) 미만")
                        return

                    status = self.order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 롱 추가진입 성공")
                        message = (
                            f"[선물] {ticker} 롱 추가진입 성공\n"
                            f"- 수량: {quantity}\n"
                            f"- 진입가: {current_price}\n"
                            f"- 이유: {reason}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                        # stage, quantity 업데이트
                        current_stage += 1
                        current_quantity += quantity
                        futures_status[ticker]["stage"] = current_stage
                        futures_status[ticker]["quantity"] = current_quantity
                    else:
                        print(f"{ticker} 롱 추가진입 실패")
                elif current_pos == "SHORT":
                    print(f"{ticker}: 현재 숏 포지션 -> 먼저 S_sell 등으로 청산 필요")
                else:
                    # position == None
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} 롱 진입 실패: 최소 주문량({min_qty}) 미만")
                        return

                    status = self.order.L_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 롱 진입 성공")
                        message = (
                            f"[선물] {ticker} 롱 진입 성공\n"
                            f"- 수량: {quantity}\n"
                            f"- 진입가: {current_price}\n"
                            f"- 이유: {reason}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                        futures_status[ticker]["position"] = "LONG"
                        futures_status[ticker]["stage"] = 1
                        futures_status[ticker]["quantity"] = quantity
                    else:
                        print(f"{ticker} 롱 진입 실패")

            # ---------- 선물 롱 청산 ----------
            elif signal_type == "L_sell":
                if current_pos != "LONG":
                    print(f"{ticker}: 롱 포지션이 없어서 청산 불가")
                    return
                qty = futures_status[ticker].get("quantity", 0)
                if qty < min_qty:
                    print(f"{ticker} 롱 청산 실패: 최소 주문량 미만")
                    return

                status = self.order.L_sell(symbol=f"{ticker}USDT", quantity=qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 롱 청산 성공")
                    message = (
                        f"[선물] {ticker} 롱 청산 성공\n"
                        f"- 청산 수량: {qty}\n"
                        f"- 청산가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)
                    # 포지션 정보 초기화
                    futures_status[ticker]["position"] = None
                    futures_status[ticker]["stage"] = 0
                    futures_status[ticker]["quantity"] = 0
                else:
                    print(f"{ticker} 롱 청산 실패")

            # ---------- 선물 숏 진입 ----------
            elif signal_type == "S_buy":
                if current_pos == "SHORT":
                    # 추가 숏 진입
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} 숏 추가진입 실패: 최소 주문량({min_qty}) 미만")
                        return

                    status = self.order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 숏 추가진입 성공")
                        message = (
                            f"[선물] {ticker} 숏 추가진입 성공\n"
                            f"- 수량: {quantity}\n"
                            f"- 진입가: {current_price}\n"
                            f"- 이유: {reason}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                        current_stage += 1
                        current_quantity += quantity
                        futures_status[ticker]["stage"] = current_stage
                        futures_status[ticker]["quantity"] = current_quantity
                    else:
                        print(f"{ticker} 숏 추가진입 실패")
                elif current_pos == "LONG":
                    print(f"{ticker}: 현재 롱 포지션 -> 먼저 L_sell로 청산 필요")
                else:
                    # position == None
                    quantity = (int(futures_limit_amount.get(ticker, 0)) * 0.2) / current_price
                    quantity = math.floor(quantity / step_size) * step_size

                    if quantity < min_qty:
                        print(f"{ticker} 숏 진입 실패: 최소 주문량({min_qty}) 미만")
                        return

                    status = self.order.S_buy(symbol=f"{ticker}USDT", quantity=quantity)
                    if status and status.get("status") == "FILLED":
                        print(f"{ticker} 숏 진입 성공")
                        message = (
                            f"[선물] {ticker} 숏 진입 성공\n"
                            f"- 수량: {quantity}\n"
                            f"- 진입가: {current_price}\n"
                            f"- 이유: {reason}"
                        )
                        self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                        futures_status[ticker]["position"] = "SHORT"
                        futures_status[ticker]["stage"] = 1
                        futures_status[ticker]["quantity"] = quantity
                    else:
                        print(f"{ticker} 숏 진입 실패")

            # ---------- 선물 숏 청산 ----------
            elif signal_type == "S_sell":
                if current_pos != "SHORT":
                    print(f"{ticker}: 숏 포지션이 없어서 청산 불가")
                    return
                qty = futures_status[ticker].get("quantity", 0)
                if qty < min_qty:
                    print(f"{ticker} 숏 청산 실패: 최소 주문량 미만")
                    return

                status = self.order.S_sell(symbol=f"{ticker}USDT", quantity=qty)
                if status and status.get("status") == "FILLED":
                    print(f"{ticker} 숏 청산 성공")
                    message = (
                        f"[선물] {ticker} 숏 청산 성공\n"
                        f"- 청산 수량: {qty}\n"
                        f"- 청산가: {current_price}\n"
                        f"- 이유: {reason}"
                    )
                    self.notifier.send_slack_message(self.config.slack_trade_channel_id, message)

                    futures_status[ticker]["position"] = None
                    futures_status[ticker]["stage"] = 0
                    futures_status[ticker]["quantity"] = 0
                else:
                    print(f"{ticker} 숏 청산 실패")

            else:
                print("Hold")

        except Exception as e:
            print(f"선물 거래 처리 중 오류 발생: {e}")
            self.notifier.send_slack_message(
                self.config.slack_error_channel_id,
                f"선물 거래 처리 중 오류 발생: {e}"
            )
