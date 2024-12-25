from data_control import Data_Control
from config import Config
class Strategy():
    def __init__(self):
        self.position_check = {}

    def trand_check(self):
        pass
    
    def position_tracker(self):
        print("포지션 추적용 함수 실행")

        print("매수인지 매도인지 판단")
        print("매수이면 포지션 정보 기록")
        print("매도이면 포지션 정보 삭제")

    def rsi_check(self):
        print("RSI 체크 함수 실행")

    def volume_profile(self):
        print("볼륨 프로파일 체크 함수 실행")

        score = int()
        
        return score

    def OBV_check(self):
        print("OBV 체크 함수 실행")

        score = int()

        return score
    
    def bandwidth_check(self):
        print("볼린저밴드 폭 체크 함수 실행")

        score = int()

        return score

    def volatility_score(self):
        print("변동성 집계 함수 실행")

        vp_score = self.volume_profile(self)
        OBV_score = self.OBV_check(self)
        bw_score = self.bandwidth_check(self)

        total_score = int()

        return total_score

    def buy_signal(self):
        
        signal = bool()

        return signal

    def sell_signal(self):

        signal = bool()

        return signal