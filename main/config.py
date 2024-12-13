
class Config():
    def __init__(self):
        print("환경변수 로드 중...")

        print("환경변수 로드 완료")
        
        self.verify(self)

    def verify(self):
        print("환경변수 검증중...")

        print("환경변수 검증 완료!")
