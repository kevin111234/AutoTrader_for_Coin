from binance.client import Client

from config import Config

def main():
    print("투자 프로그램을 시작합니다.")
    
    # Config에서 환경변수 및 고정변수 불러오기
    config = Config()
    client = Client(config.binance_access_key, config.binance_secret_key)

    # 초기 자산 조회 - notifier.py

    # 초기 데이터 수집 - data_control.py

    # 반복문 시작
    while True:
        try:
            print("매수/매도 판단을 시작합니다.")
            # 현재 가격 조회

            # 가격데이터 업데이트

            # 매수/매도 판단

            # 주문 진행

        except Exception as e:
            print(f"메인 루프 오류: {e}")
            # notifier.py를 통해 error 로그 전송