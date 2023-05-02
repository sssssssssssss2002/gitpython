import sys
import traceback
import upbit
import datetime
import logging
import time
import pyupbit
import pandas as pd


def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time


price_data = upbit.current_price('KRW-BTC');
datalogger = upbit.log()

print("프로그램 실행시작")
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1)

        candles = upbit.get_candle('KRW-BTC', '1', 1)
        price = upbit.current_price('KRW-BTC')
        rsi = upbit.get_rsi('KRW-BTC', '30', '200')
        mfi = upbit.get_mfi('KRW-BTC', '30', '200', 1)
        macd = upbit.get_macd('KRW-BTC', '30', '200', 1)
        signal = macd[0]['SIGNAL']
        bb_data = upbit.get_bb('KRW-BTC', '30', '200', 1)
        bbh = bb_data[0]["BBH"]
        df = pd.DataFrame(candles)
        dfDt = df['candle_date_time_kst'].iloc[::-1]

        # result = upbit.buycoin_mp("KRW-BTC", '10000')
        # datalogger.info(result)
        # #
        # result = upbit.sellcoin_mp("KRW-BTC")
        # datalogger.info(result)
        result = upbit.buycoin_mp("KRW-BTC", '10000')
        datalogger.info(result)
        print("매수완료")
        #
        result = upbit.sellcoin_mp("KRW-BTC")
        datalogger.info(result)
        print("매도완료")

        Coin_Data = []
        Coin_Data.append(
            {"type": "BTC", "DT": dfDt[0], "PRICE": price, "RSI": rsi, "MFI": round(mfi, 4),
             "MACD": macd[0]["MACD"],
             "SIGNAL": macd[0]['SIGNAL'], "OCL": macd[0]['OCL'], "BBH": bb_data[0]["BBH"],
             "BBM": bb_data[0]["BBM"],
             "BBL": bb_data[0]["BBL"]})

        #
        #
        #
        datalogger.info(candles)
        datalogger.info(Coin_Data)

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            print("****프로그램 실행중****")
        else:
            btc = upbit.get_balance()
        time.sleep(1)

    except Exception as e:
        print(e)
        time.sleep(1)



    except Exception:
        logging.error("Exception 발생!")
        logging.error(traceback.format_exc())
        sys.exit(1)


