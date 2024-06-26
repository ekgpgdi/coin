import math
import pyupbit
import datetime

from apscheduler.schedulers.background import BackgroundScheduler
import time

from dotenv import load_dotenv
import os

import mysql.connector
from mysql.connector import Error


def get_transaction_amount(num, current_date):
    # 원화시장의 암호화폐 목록만 확인 = KRW를 통해 거래되는 코인만 불러오기
    tickers = pyupbit.get_tickers("KRW")
    dic_ticker = {}

    # 코인 목록의 개수 확인
    num_of_tickers = len(tickers)

    # 개수 출력
    print("코인 목록 개수:", num_of_tickers)

    for ticker in tickers:
        # API 호출 제한을 피하기 위해 잠시 대기
        time.sleep(0.1)

        # get_ohlcv(ticker, interval, count, to, period)
        # ticker : 가격 내역을 조회할 코인의 ticker
        # interval : 가격 조회 간격 > day, minute1 (1분봉), week, month > minute : 1, 3, 5, 10, 15, 30, 60, 240
        # count : 최근 며칠 치의 데이터 조회
        # to : 출력할 max date time
        # period : 데이터 요청 주기 (초)
        df = pyupbit.get_ohlcv(ticker, interval='day', count=10, to=current_date, period=0.1)  # date 기간의 거래대금을 구해준다
        volume_money = 0.0

        if ticker == "KRW-BTC":
            continue

        if df is None or df.empty:
            print(f"{ticker} returned no data")
            continue

        try:
            if len(df) < 8:
                print(f"{ticker} does not have enough data")
                continue

            # 순위가 바뀔 수 있으니 당일은 포함 X
            for i in range(2, 9):
                volume_money += df['close'].iloc[-i] * df['volume'].iloc[-i]

        except TypeError as e:
            print(f"Error: {e} | 코인 {ticker}의 데이터를 처리하는 중에 오류 발생")
        except KeyError as e:
            print(f"Error: {e} | 코인 {ticker}의 데이터를 처리하는 중에 오류 발생")

        dic_ticker[ticker] = volume_money

    # 거래대금 큰 순으로 ticker를 정렬
    sorted_ticker = sorted(dic_ticker.items(), key=lambda x: x[1], reverse=True)

    coin_list = []
    count = 0

    for coin in sorted_ticker:
        count += 1

        # 거래대금이 높은 num 개의 코인만 구한다
        if count <= num:
            coin_list.append(coin[0])
        else:
            break

    return coin_list


def get_rsi(df, period=14):
    try:
        # 전일 대비 변동 평균
        df['change'] = df['close'].diff()

        # 상승한 가격과 하락한 가격
        df['up'] = df['change'].apply(lambda x: x if x > 0 else 0)
        df['down'] = df['change'].apply(lambda x: -x if x < 0 else 0)

        # 상승 평균과 하락 평균
        df['avg_up'] = df['up'].ewm(alpha=1 / period).mean()
        df['avg_down'] = df['down'].ewm(alpha=1 / period).mean()

        # 상대강도지수(RSI) 계산
        df['rs'] = df['avg_up'] / df['avg_down']
        df['rsi'] = 100 - (100 / (1 + df['rs']))
        rsi = df['rsi']
    except(TypeError, KeyError):
        print("rsi 계산 중 에러 발생!")

    return rsi


# 이미 매수한 코인인지 확인
def has_coin(ticker, balances):
    result = False

    for coin in balances:
        coin_ticker = coin['unit_currency'] + "-" + coin['currency']

        if ticker == coin_ticker:
            result = True

    return result


# 수익률 확인
def get_revenue_rate(balances, ticker):
    revenue_rate = 0.0

    for coin in balances:
        # 티커 형태로 전환
        coin_ticker = coin['unit_currency'] + "-" + coin['currency']

        if ticker == coin_ticker:
            # 현재 시세
            now_price = pyupbit.get_current_price(coin_ticker)

            # 수익률 계산을 위한 형 변환
            revenue_rate = (now_price - float(coin['avg_buy_price'])) / float(coin['avg_buy_price']) * 100.0

    return revenue_rate


def check_coin():
    # 현재 날짜를 저장하는 변수
    current_date = datetime.datetime.now().date()

    tickers = get_transaction_amount(10, current_date)  # 거래대금 상위 10개 코인 선정
    print(f"거래 대금 상위 10개 코인 : {tickers}")

    money_rate = 0.35  # 투자 비중
    target_revenue = 1.1  # 목표 수익률(1.0 %)
    target_loss = -3.0  # 3.0% 손실 날시 매도
    min_ravenue = 0.45  # 최소 수익률
    #   division_amount = 0.3   # 분할 매도 비중

    # 나의 계좌 조회
    # currency : 자산 종류  (KRW = 원화, BTC = 비트코인, EOS = 이오스 등등)
    # balance : 보유 자산 현황
    # avg_buy_price : 평균 단가
    # unit_currentcy : 평균 단가 단위
    balances = upbit.get_balances()

    print(f"나의 계좌 정보 : {balances}")

    # my_money = float(balances[0]['balance'])  # 내 원화
    # money = my_money * money_rate  # 코인에 할당할 비용
    # money = math.floor(money)  # 소수점 버림
    #
    # fee = 0.0005
    #
    # #   count_coin = len(tickers)       # 목표 코인 개수
    # #   money /= count_coin             # 각각의 코인에 공평하게 자본 분배
    #
    # for target_ticker in tickers:
    #     ticker_rate = get_revenue_rate(balances, target_ticker)
    #     df_minute = pyupbit.get_ohlcv(target_ticker, interval="minute1")  # 1분봉 정보
    #     rsi = get_rsi(df_minute, 15)
    #     rsi14 = rsi.iloc[-1]  # 당일 RSI14
    #     before_rsi14 = rsi.iloc[-2]  # 작일 RSI14
    #
    #     if has_coin(target_ticker, balances):
    #         ticker_rate = get_revenue_rate(balances, target_ticker)  # 수익률 확인
    #
    #         # 매도 조건 충족1
    #         if rsi14 < 70 and before_rsi14 > 70:
    #             if ticker_rate > min_ravenue:
    #                 amount = upbit.get_balance(target_ticker)  # 현재 비트코인 보유 수량
    #                 upbit.sell_market_order(target_ticker, amount)  # 시장가에 매도
    #                 balances = upbit.get_balances()  # 매도했으니 잔고를 최신화!
    #                 print(
    #                     f"1. 매도 - {target_ticker}: 가격 {amount * pyupbit.get_current_price(target_ticker)}에 {amount}개 판매, 수익률 : {ticker_rate}%")
    #
    #         # 매도 조건 충족2 (과매수 구간일 때)
    #         elif rsi14 > 70:
    #             # 목표 수익률을 만족한다면
    #             if ticker_rate >= target_revenue:
    #                 amount = upbit.get_balance(target_ticker)  # 현재 코인 보유 수량
    #                 sell_amount = amount  # 분할 매도 비중
    #                 upbit.sell_market_order(target_ticker, sell_amount)  # 시장가에 매도
    #                 balances = upbit.get_balances()  # 매도했으니 잔고를 최신화
    #                 print(
    #                     f"2. 매도 - {target_ticker}: 가격 {amount * pyupbit.get_current_price(target_ticker)}에 {amount}개 판매, 수익률 : {ticker_rate}%")
    #
    #         # 매도 조건 충족3 (수익률 달성 했을 시)
    #         elif ticker_rate >= target_revenue:
    #             amount = upbit.get_balance(target_ticker)  # 현재 코인 보유 수량
    #             sell_amount = amount  # 분할 매도 비중
    #             upbit.sell_market_order(target_ticker, sell_amount)  # 시장가에 매도
    #             balances = upbit.get_balances()  # 매도했으니 잔고를 최신화
    #             print(
    #                 f"3. 매도 - {target_ticker}: 가격 {amount * pyupbit.get_current_price(target_ticker)}에 {amount}개 판매, 수익률 : {ticker_rate}%")
    #
    #         # 매도 조건 충족4 (3.0% 이하로 내려갈 시 손절)
    #         elif ticker_rate < target_loss:
    #             amount = upbit.get_balance(target_ticker)  # 현재 코인 보유 수량
    #             sell_amount = amount  # 분할 매도 비중
    #             try:
    #                 # upbit.sell_market_order(target_ticker, sell_amount)  # 시장가에 매도
    #                 balances = upbit.get_balances()  # 매도했으니 잔고를 최신화
    #                 print(
    #                     f"4. 매도 - {target_ticker}: 가격 {amount * pyupbit.get_current_price(target_ticker)}에 {amount}개 판매, 수익률 : {ticker_rate}%")
    #             except Exception as e:
    #                 print("매도 실패")
    #
    #         # 추가 매수
    #         elif before_rsi14 < 30:
    #             if rsi14 > 30:
    #                 buy_money = (money - (money * fee))  # 본인이 가지고 있는 금액에 15% 추가 매수
    #                 if buy_money < 5000 or (my_money - buy_money) < 5000:
    #                     buy_money = upbit.get_balance('KRW')
    #                     buy_money = (buy_money - (buy_money * fee))
    #                 try:
    #                     upbit.buy_market_order(target_ticker, buy_money)  # 시장가에 비트코인을 매수
    #                     balances = upbit.get_balances()  # 매수했으니 잔고를 최신화
    #                     print(
    #                         f"추가 매수 - {target_ticker}: 가격 {buy_money}에 {buy_money / pyupbit.get_current_price(target_ticker)}개 구매")
    #                 except Exception as e:
    #                     print("매수 실패")
    #
    #     else:
    #         # 매수 조건 충족
    #         if before_rsi14 < 30:
    #             if rsi14 > 30:
    #                 buy_money = money - (money * fee)
    #                 if buy_money < 5000 or (my_money - buy_money) < 5000:
    #                     buy_money = upbit.get_balance('KRW')
    #                     buy_money = (buy_money - (buy_money * fee))
    #
    #                 try:
    #                     upbit.buy_market_order(target_ticker, buy_money)  # 시장가에 비트코인을 매수
    #                     balances = upbit.get_balances()  # 매수했으니 잔고를 최신화
    #                     print(
    #                         f"매수 - {target_ticker}: 가격 {buy_money}에 {buy_money / pyupbit.get_current_price(target_ticker)}개 구매")
    #                 except Exception as e:
    #                     print("매수 실패")


def check_coin_test():
    # 현재 날짜를 저장하는 변수
    current_date = datetime.datetime.now().date()

    tickers = get_transaction_amount(10, current_date)  # 거래대금 상위 10개 코인 선정
    print(f"거래 대금 상위 10개 코인 : {tickers}")


load_dotenv()

access = os.getenv('ACCESS_KEY')
secret = os.getenv('SECRET_KEY')
database = os.getenv('DATABASE')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('DATABASE_PASSWORD')

try:
    # MySQL 데이터베이스에 연결
    connection = mysql.connector.connect(
        host='localhost',  # 호스트 이름
        database=database,  # 데이터베이스 이름
        user=database_user,  # 사용자 이름
        password=database_password  # 비밀번호
    )
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)

except Error as e:
    print("Error while connecting to MySQL", e)

    # MySQL 연결을 종료합니다.
    if (connection.is_connected()):
        cursor.close()
        connection.close()
        print("MySQL connection is closed")

# 객체 생성
upbit = pyupbit.Upbit(access, secret)

# 백그라운드 스케줄러 생성
scheduler = BackgroundScheduler()

scheduler.add_job(check_coin_test, 'interval', seconds=120)

# 스케줄러 시작
scheduler.start()

try:
    # 작업 실행 시간 동안 프로그램 유지
    while True:
        time.sleep(1)
except (KeyboardInterrupt, SystemExit):
    # Ctrl+C 등 종료 시 스케줄러 중지
    scheduler.shutdown()

    if (connection.is_connected()):
        cursor.close()
        connection.close()
        print("MySQL connection is closed")
