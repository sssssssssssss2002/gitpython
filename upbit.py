import logging
import pyupbit
import requests
import time
import jwt
import uuid
import hashlib
import numpy

import pandas as pd
from decimal import Decimal
from urllib.parse import urlencode
# Keys 업비트에서 키를 발급받아야함
access_key = 'IpXykP3HxVCflGxr5M0BDYGYbhYyTkqM0X6HZxe2'
secret_key = 'EzEMnSTorF2o5XxMRS1SyA8lXUrRk2q1wLhFXkzJ'
server_url = 'https://api.upbit.com'


# 로그 저장
def log():
    logger = logging.getLogger()
    formatter = logging.Formatter()
    fileHandler = logging.FileHandler("coindata.csv")
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    logger.setLevel(level=logging.INFO)
    return logger


# 리퀘스트 처리
# 요청 타입, URL, 파라메타, 헤더
def send_request(reqType, reqUrl, reqParam, reqHeader):
    try:
        # 요청 가능회수 확보를 위해 기다리는 시간(초)
        err_sleep_time = 1
        # 요청에 대한 응답을 받을 때까지 반복 수행
        while True:

            # 요청 처리
            response = requests.request(reqType, reqUrl, params=reqParam, headers=reqHeader)

            # 요청 가능회수 추출
            if 'Remaining-Req' in response.headers:

                hearder_info = response.headers['Remaining-Req']
                start_idx = hearder_info.find("sec=")
                end_idx = len(hearder_info)
                remain_sec = hearder_info[int(start_idx):int(end_idx)].replace('sec=', '')
            else:
                logging.error("헤더 정보 이상")
                logging.error(response.headers)
                break

            # 요청 가능회수가 4개 미만이면 요청 가능회수 확보를 위해 일정시간 대기
            if int(remain_sec) < 4:
                logging.debug("요청 가능회수 한도 도달! 남은횟수:" + str(remain_sec))
                time.sleep(err_sleep_time)

            # 정상 응답
            if response.status_code == 200 or response.status_code == 201:
                break
            # 요청 가능회수 초과인 경우
            elif response.status_code == 429:
                logging.error("요청 가능회수 초과!:" + str(response.status_code))
                time.sleep(err_sleep_time)
            # 그 외 오류
            else:
                logging.error("기타 에러:" + str(response.status_code))
                logging.error(response.status_code)
                break

            # 요청 가능회수 초과 에러 발생시에는 다시 요청
            logging.info("[restRequest] 요청 재처리중...")

        return response

    except Exception:
        raise

# 전체 종목 리스트 조회
# 대상 마켓(KRW,BTC,USDT)
# 제외 종목(BTC,ETH)
def get_items(market, except_item):
    try:

        # 조회결과
        rtn_list = []
        # 마켓 데이터
        markets = market.split(',')
        # 제외 데이터
        except_items = except_item.split(',')

        url = "https://api.upbit.com/v1/market/all"
        querystring = {"isDetails": "false"}
        response = send_request("GET", url, querystring, "")
        data = response.json()

        # 조회 마켓만 추출
        for data_for in data:
            for market_for in markets:
                if data_for['market'].split('-')[0] == market_for:
                    rtn_list.append(data_for)

        # 제외 종목 제거
        for rtnlist_for in rtn_list[:]:
            for exceptItemFor in except_items:
                for marketFor in markets:
                    if rtnlist_for['market'] == marketFor + '-' + exceptItemFor:
                        rtn_list.remove(rtnlist_for)

        return rtn_list

    except Exception:
        raise


# 시장가 매수
# 종목,금액
def buycoin_mp(target_item, buy_amount):
    try:
        query = {
            'market': target_item,
            'side': 'bid',
            'price': buy_amount,
            'ord_type': 'price',
        }

        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()

        return rtn_data

    except Exception:
        raise

# 주문가능 잔고 조회
def get_balance(target_item):
    try:

        # 주문가능 잔고 리턴용
        rtn_balance = 0

        # 최대 재시도 횟수
        max_cnt = 0

        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        # 잔고가 조회 될 때까지 반복
        while True:

            # 조회 회수 증가
            max_cnt = max_cnt + 1

            res = send_request("GET", server_url + "/v1/accounts", "", headers)
            my_asset = res.json()


            # 해당 종목에 대한 잔고 조회
            # 잔고는 마켓에 상관없이 전체 잔고가 조회됨
            for myasset_for in my_asset:
                if myasset_for['currency'] == target_item.split('-')[1]:
                    rtn_balance = myasset_for['balance']

            # 잔고가 0 이상일때까지 반복
            if Decimal(str(rtn_balance)) > Decimal(str(0)):
                break

            # 최대 100회 수행
            if max_cnt > 100:
                break

            logging.info("[주문가능 잔고 리턴용] 요청 재처리중...")

        return rtn_balance

    except Exception:
        raise


# 시장가 매도
def sellcoin_mp(target_item):
    try:

        # 잔고 조회
        cur_balance = get_balance(target_item)

        query = {
            'market': target_item,
            'side': 'ask',
            'volume': cur_balance,
            'ord_type': 'market',
        }

        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()

        logging.info("시장가 매도 완료!")

        return rtn_data

    except Exception:
        raise

# - Desc : 지정가 매도
def sellcoin_tg(target_item, sell_price):
    try:

        # 잔고 조회
        cur_balance = get_balance(target_item)

        query = {
            'market': target_item,
            'side': 'ask',
            'volume': cur_balance,
            'price': sell_price,
            'ord_type': 'limit',
        }

        query_string = urlencode(query).encode()

        m = hashlib.sha512()
        m.update(query_string)
        query_hash = m.hexdigest()

        payload = {
            'access_key': access_key,
            'nonce': str(uuid.uuid4()),
            'query_hash': query_hash,
            'query_hash_alg': 'SHA512',
        }

        jwt_token = jwt.encode(payload, secret_key)
        authorize_token = 'Bearer {}'.format(jwt_token)
        headers = {"Authorization": authorize_token}

        res = send_request("POST", server_url + "/v1/orders", query, headers)
        rtn_data = res.json()
        logging.info("지정가 매도 완료!")

        return rtn_data

    except Exception:
        raise

#현재가 조회
def current_price(target_item):
    return pyupbit.get_current_price(target_item)

#캔들 조회
def get_candle(target_item, tick_kind, inq_range):
    try:

        # Tick 별 호출 URL 설정
        # 분봉
        if tick_kind == "1" or tick_kind == "3" or tick_kind == "5" or tick_kind == "10" or tick_kind == "15" or tick_kind == "30" or tick_kind == "60" or tick_kind == "240":
            target_url = "minutes/" + tick_kind
        # 일
        elif tick_kind == "D":
            target_url = "days"
        # 주
        elif tick_kind == "W":
            target_url = "weeks"
        # 월
        elif tick_kind == "M":
            target_url = "months"
        # 잘못된 입력
        else:
            raise Exception("잘못된 틱 종류:" + str(tick_kind))

        logging.debug(target_url)

        # Tick 조회
        querystring = {"market": target_item, "count": inq_range}
        res = send_request("GET", server_url + "/v1/candles/" + target_url, querystring, "")
        candle_data = res.json()

        #logging.debug(candle_data)

        return candle_data

    except Exception:
        raise

def get_ma(n):
    df = pyupbit.get_ohlcv()
    ma = df['close'].rolling(window=n).mean()
    return ma

# RSI 조회 S
# Input
# 대상 종목, 캔들 종류 (1, 3, 5, 10, 15, 30, 60, 240 - 분, D-일, W-주, M-월), 조회 범위
def get_rsi(target_item, tick_kind, inq_range):
    try:

        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)

        df = pd.DataFrame(candle_data)
        df = df.reindex(index=df.index[::-1]).reset_index()

        df['close'] = df["trade_price"]

        # RSI 계산
        def rsi(ohlc: pd.DataFrame, period: int = 14):
            ohlc["close"] = ohlc["close"]
            delta = ohlc["close"].diff()

            up, down = delta.copy(), delta.copy()
            up[up < 0] = 0
            down[down > 0] = 0

            _gain = up.ewm(com=(period - 1), min_periods=period).mean()
            _loss = down.abs().ewm(com=(period - 1), min_periods=period).mean()

            RS = _gain / _loss
            return pd.Series(100 - (100 / (1 + RS)), name="RSI")

        rsi = round(rsi(df, 14).iloc[-1], 4)

        return rsi

    except Exception:
        raise


# MFI 조회 S
def get_mfi(target_item, tick_kind, inq_range, loop_cnt):
    try:

        # 캔들 데이터 조회용
        candle_datas = []

        # MFI 데이터 리턴용
        mfiList = []

        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)

        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])

        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:

            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]

            df['typical_price'] = (df['trade_price'] + df['high_price'] + df['low_price']) / 3
            df['money_flow'] = df['typical_price'] * df['candle_acc_trade_volume']

            positive_mf = 0
            negative_mf = 0

            for i in range(0, 14):

                if df["typical_price"][i] > df["typical_price"][i + 1]:
                    positive_mf = positive_mf + df["money_flow"][i]
                elif df["typical_price"][i] < df["typical_price"][i + 1]:
                    negative_mf = negative_mf + df["money_flow"][i]

            if negative_mf > 0:
                mfi = 100 - (100 / (1 + (positive_mf / negative_mf)))
            else:
                mfi = 100 - (100 / (1 + (positive_mf)))

            #mfiList.append({"type": "MFI", "DT": dfDt[0], "MFI": round(mfi, 4)})

        return mfi

    except Exception:
        raise

# - Desc : MACD 조회
# #캔들 종류 , 캔들 조회 범위, 지표 반복계산 횟수
def get_macd(target_item, tick_kind, inq_range, loop_cnt):
    try:

        # 캔들 데이터 조회용
        candle_datas = []

        # MACD 데이터 리턴용
        macd_list = []

        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)

        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])

        df = pd.DataFrame(candle_datas[0])
        df = df.iloc[::-1]
        df = df['trade_price']

        # MACD 계산
        exp1 = df.ewm(span=12, adjust=False).mean()
        exp2 = df.ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        exp3 = macd.ewm(span=9, adjust=False).mean()

        for i in range(0, int(loop_cnt)):
            macd_list.append(
                {"type": "MACD", "DT": candle_datas[0][i]['candle_date_time_kst'], "MACD": round(macd[i], 4),
                 "SIGNAL": round(exp3[i], 4),
                 "OCL": round(macd[i] - exp3[i], 4)})

        return macd_list

    except Exception:
        raise


# 볼린저밴드
def get_bb(target_item, tick_kind, inq_range, loop_cnt):
    try:

        # 캔들 데이터 조회용
        candle_datas = []

        # 볼린저밴드 데이터 리턴용
        bb_list = []

        # 캔들 추출
        candle_data = get_candle(target_item, tick_kind, inq_range)

        # 조회 횟수별 candle 데이터 조합
        for i in range(0, int(loop_cnt)):
            candle_datas.append(candle_data[i:int(len(candle_data))])

        # 캔들 데이터만큼 수행
        for candle_data_for in candle_datas:
            df = pd.DataFrame(candle_data_for)
            dfDt = df['candle_date_time_kst'].iloc[::-1]
            df = df['trade_price'].iloc[::-1]

            # 표준편차(곱)
            unit = 2

            band1 = unit * numpy.std(df[len(df) - 20:len(df)])
            bb_center = numpy.mean(df[len(df) - 20:len(df)])
            band_high = bb_center + band1
            band_low = bb_center - band1

            bb_list.append({"type": "BB", "DT": dfDt[0], "BBH": round(band_high, 4), "BBM": round(bb_center, 4),
                            "BBL": round(band_low, 4)})

        return bb_list

    except Exception:
        raise