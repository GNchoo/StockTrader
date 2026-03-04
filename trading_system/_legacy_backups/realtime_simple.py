#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 실시간 모니터링
5초 간격으로 가격 확인만 (거래 없음)
"""

import json, os, sys, time, datetime
from pathlib import Path

from upbit_live_client  import UpbitLiveClient

# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
SYMBOLS = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
CHECK_INTERVAL = 5  # 초

def main():
    print("=" * 70)
    print("트레이더 마크 📊 - 간단한 실시간 모니터링")
    print("=" * 70)
    print(f"심볼: {', '.join(SYMBOLS)}")
    print(f"체크 간격: {CHECK_INTERVAL}초")
    print("실시간 가격만 모니터링 (거래 없음)")
    print("-" * 70)
    
    upbit = UpbitLiveClient()
    last_prices = {}
    
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 가격 조회 시작")
            
            for symbol in SYMBOLS:
                try:
                    tickers = upbit.get_ticker([symbol])
                    if tickers and len(tickers) > 0:
                        price = float(tickers[0]["trade_price"])
                        last_prices[symbol] = price
                        print(f"   {symbol}: {price:,.0f}원")
                    else:
                        print(f"   {symbol}: 데이터 없음")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"   {symbol} 오류: {e}")
            
            # 포트폴리오 파일 업데이트 시간 표시
            portfolio_path = Path("paper_portfolio.json")
            if portfolio_path.exists():
                mtime = portfolio_path.stat().st_mtime
                age = time.time() - mtime
                print(f"   📁 포트폴리오: {datetime.datetime.fromtimestamp(mtime).strftime('%H:%M:%S')} ({age:.0f}초 전)")
            
            print(f"[{timestamp}] 다음 조회까지 {CHECK_INTERVAL}초 대기...")
            print("-" * 50)
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n모니터링 종료")
    except Exception as e:
        print(f"치명적 오류: {e}")

if __name__ == "__main__":
    main()
