**암호화폐 자동투자 프로그램**  

--------------------------------------------
# 환경변수 설정
1. BINANCE_ACCESS_KEY = 바이낸스 api key
2. BINANCE_SECRET_KEY = 바이낸스 secret key
3. SLACK_API_KEY = 슬랙 봇 api token
4. SLACK_ASSET_CHANNEL_ID = 자산 정보를 전송할 슬랙 채널 ID
5. SLACK_TRADE_CHANNEL_ID = 매매 정보를 전송할 슬랙 채널 ID
6. SLACK_ERROR_CHANNEL_ID = 에러 정보를 전송할 슬랙 채널 ID
API 설정에 대한 정보는 [[https://woghd-dev.tistory.com/19](https://woghd-dev.tistory.com/19)]참고

7. SEED_MONEY = 시드머니(수익률 계산용)
8. COIN_TICKERS = 매매하고자 하는 코인 티커(ex- USDT-BTC = 테더로 비트코인을 사겠다)(공백으로 구분)
9. STO_FUT_RATE = 현물/선물 거래 비율(공백으로 구분)
10. LEVERAGE_RATE = 레버리지 비율(숫자만 작성)

# 디렉토리 구조
  
# 데이터 정보
### **데이터 칼럼 구성 (캔들 데이터 기준)**  
  
캔들 데이터는 `data_control.py` 파일의 `data` 및 `update_data` 메서드에서 수집됩니다. 수집된 데이터는 Pandas DataFrame으로 변환되며, 주요 컬럼은 아래와 같습니다:  
  
| 칼럼명                              | 설명                                                     | 데이터 타입         |
| -------------------------------- | ------------------------------------------------------ | -------------- |
| **Open Time**                    | 해당 캔들이 시작된 시간                                          | datetime       |
| **Open**                         | 캔들의 시작 가격 (시가)                                         | float64        |
| **High**                         | 해당 기간 동안의 최고 가격                                        | float64        |
| **Low**                          | 해당 기간 동안의 최저 가격                                        | float64        |
| **Close**                        | 해당 기간 동안의 종료 가격 (종가)                                   | float64        |
| **Volume**                       | 해당 캔들 기간 동안의 총 거래량                                     | float64        |
| **Taker Buy Base Asset Volume**  | 매수 거래량 (실제 매수자의 거래량)                                   | float64        |
| **Taker Sell Base Asset Volume** | 매도 거래량 (매도 거래량 = 전체 거래량 - 매수 거래량)                      | float64        |
| **SMA_20, SMA_60, SMA_120**      | 20일, 60일, 120일 단순 이동평균선                                | float64        |
| **RSI**                          | 상대강도지수 (Relative Strength Index), 14일 기준               | float64        |
| **RSI_Signal**                   | RSI의 신호선, RSI 14일 평균치                                  | float64        |
| **Bollinger_MA**                 | 볼린저밴드 중간선 (20일 단순 이동평균)                                | float64        |
| **Bollinger_Upper**              | 볼린저밴드 상단                                               | float64        |
| **Bollinger_Lower**              | 볼린저밴드 하단                                               | float64        |
| **Bollinger_BW**                 | 볼린저밴드 폭 (Upper - Lower)                                | float64        |
| **OBV**                          | 온밸런스 볼륨 (On-Balance Volume)                            | float64        |
| **Spread_20_60**                 | 20일 SMA와 60일 SMA 간의 차이                               | float64        |
| **Spread_60_120**                | 60일 SMA와 120일 SMA 간의 차이                              | float64        |
| **Spread_20_120**                | 20일 SMA와 120일 SMA 간의 차이                              | float64        |
| **Spread_20_60_MA**              | Spread_20_60의 이동평균                                    | float64        |
| **Spread_60_120_MA**             | Spread_60_120의 이동평균                                   | float64        |
| **Spread_20_120_MA**             | Spread_20_120의 이동평균                                   | float64        |
| **Trend**                        | 추세 상태 (19단계: -9 ~ 9)                                  | int            |

- **단위:** `Open Time`은 밀리초(ms) 단위로 제공되며, 데이터프레임에서 `pd.to_datetime()`을 통해 datetime 형식으로 변환됩니다.  

### **Trend 칼럼 단계별 설명:**
- **코드 1**: `sma120 < sma60 < sma20` & `RBW >= 1.1` (폭 넓음)
- **코드 2**: `sma120 < sma60 < sma20` & `0.8 <= RBW < 1.1` (폭 평균)
- **코드 3**: `sma120 < sma60 < sma20` & `RBW < 0.8` (폭 좁음)
- **코드 4**: `sma60 < sma120 < sma20` & `RBW >= 1.1`
- **코드 5**: `sma60 < sma120 < sma20` & `0.8 <= RBW < 1.1`
- **코드 6**: `sma60 < sma120 < sma20` & `RBW < 0.8`
- **코드 7**: `sma120 < sma60 < sma20` & `RBW > 1.1`
- **코드 8**: `sma120 < sma20 < sma60` & `0.8 <= RBW < 1.1`
- **코드 9**: `sma120 < sma20 < sma60` & `RBW < 0.8`
- **코드 -1**: `sma20 < sma120 < sma60` & `RBW >= 1.1`
- **코드 -2**: `sma20 < sma120 < sma60` & `0.8 <= RBW < 1.1`
- **코드 -3**: `sma20 < sma120 < sma60` & `RBW < 0.8`
- **코드 -4**: `sma60 < sma20 < sma120` & `RBW >= 1.1`
- **코드 -5**: `sma60 < sma20 < sma120` & `0.8 <= RBW < 1.1`
- **코드 -6**: `sma60 < sma20 < sma120` & `RBW < 0.8`
- **코드 -7**: `sma20 < sma60 < sma120` & `RBW >= 1.1`
- **코드 -8**: `sma20 < sma60 < sma120` & `0.8 <= RBW < 1.1`
- **코드 -9**: `sma20 < sma60 < sma120` & `RBW < 0.8`
- **코드 0**: (기타, or `sma120 ≈ sma60 ≈ sma20` 등 애매 구간)

---
  
### **볼륨 프로파일 및 TPO 프로파일 (cal_tpo_volume_profile)**  
  
캔들 데이터 외에도 가격 구간별 거래량 및 시간 분석을 위해 TPO 및 볼륨 프로파일이 계산됩니다.  

| 칼럼명                             | 설명                                                     | 데이터 타입        |
| ------------------------------- | ------------------------------------------------------ | ------------- |
| **Bin**                         | 가격 구간을 나눈 인덱스 값                                        | int           |
| **Price_Low**                   | 해당 가격 구간의 최저 가격                                        | float64       |
| **Price_High**                  | 해당 가격 구간의 최고 가격                                        | float64       |
| **Volume**                      | 해당 가격 구간에서의 총 거래량                                      | float64       |
| **TPO**                         | 해당 가격 구간에서 머무른 시간(빈도)                                  | int           |
| **Taker_Buy_Volume**            | 해당 가격 구간에서 매수된 거래량                                     | float64       |
| **Taker_Sell_Volume**           | 해당 가격 구간에서 매도된 거래량                                     | float64       |
| **Volume_norm**                 | 거래량을 정규화한 값                                            | float64       |
| **TPO_norm**                    | TPO 값을 정규화한 값                                          | float64       |
| **Score**                       | 거래량 및 TPO 점수 합산치                                       | float64       |
- TPO/볼륨 프로파일은 `20`개의 가격 구간으로 나누어 계산됩니다.  
- 가장 거래량과 TPO 빈도가 높은 구간은 POC(Point of Control)로 정의됩니다.  
- 상위 3개의 구간을 잠재적인 지지/저항 구간으로 설정합니다.  
  
---
