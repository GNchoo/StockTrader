#!/usr/bin/env python3
"""
트레이더 마크 📊 - 실시간 모의투자 모니터링 (고정 버전)
AI 신호 + 자동 거래 + 실시간 반영
"""

import json, os, sys, time, threading, asyncio
from datetime import datetime, timedelta
from pathlib import Path

from ai_signal_engine   import AISignalEngine
from volatility_monitor import VolatilityCalculator, EmergencyStopManager
from upbit_live_client  import UpbitLiveClient
from paper_engine       import PaperEngine, FEE_RATE, BEP_RATE

# ─────────────────────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────────────────────
SYMBOLS = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
CHECK_INTERVAL = 10   # 초 (5→10초, API 호출 절반으로 줄임)
MIN_CONFIDENCE = 0.75  # AI 신호 최소 신뢰도 (65→75%, 더 확실한 신호만)
MAX_TRADES_PER_HOUR = 6  # 시간당 최대 거래 수 (20→6, 과잉매매 방지)
MIN_HOLD_SECONDS = 300   # 최소 보유 시간 5분 (연속 매도 방지)

# ─────────────────────────────────────────────────────────────
# 실시간 모니터링 클래스
# ─────────────────────────────────────────────────────────────
class RealtimeTrader:
    """실시간 모의투자 모니터링"""

    def __init__(self):
        self.paper_engine = PaperEngine()
        self.ai_engine = AISignalEngine()
        self.vol_calc = VolatilityCalculator()
        self.upbit = UpbitLiveClient()
        
        self.running = True
        self.trade_counts = {}
        self.last_prices = {}
        self.price_history = {}   # 심볼별 가격 기록
        self.entry_times = {}     # 심볼별 진입 시간 (최소 보유 시간 체크용)
        
        print("=" * 70)
        print("트레이더 마크 📊 - 실시간 모의투자 모니터링")
        print("=" * 70)
        print(f"심볼: {', '.join(SYMBOLS)}")
        print(f"체크 간격: {CHECK_INTERVAL}초")
        print(f"AI 최소 신뢰도: {MIN_CONFIDENCE*100:.0f}%")
        print(f"현재 자본: {self.paper_engine.portfolio.capital:,.0f}원")
        print()

    def update_price(self, symbol: str, price: float):
        """가격 업데이트"""
        self.last_prices[symbol] = price
        
        # 가격 기록
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        self.price_history[symbol].append(price)
        if len(self.price_history[symbol]) > 200:
            self.price_history[symbol].pop(0)

    def process_signal(self, symbol: str, price: float, signal: str, confidence: float):
        """AI 신호 처리"""
        # 시간당 거래 제한
        hour_key = datetime.now().strftime("%Y-%m-%d-%H")
        if hour_key not in self.trade_counts:
            self.trade_counts[hour_key] = 0
        if self.trade_counts[hour_key] >= MAX_TRADES_PER_HOUR:
            return

        positions = self.paper_engine.portfolio.positions
        now_ts = time.time()

        if signal == "BUY" and symbol not in positions:
            # 데이터 충분한지 확인 (최소 30개)
            if len(self.price_history.get(symbol, [])) < 30:
                return

            prices = self.price_history[symbol][-50:]
            vol = self.vol_calc.calculate(prices)
            strategy = self.vol_calc.suggest_strategy(vol)

            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] 🟢 BUY {symbol} | 신뢰도: {confidence:.1%} | 전략: {strategy} | 가격: {price:,.0f}원")

            self.paper_engine.open_position(symbol, price, strategy)
            self.entry_times[symbol] = now_ts   # 진입 시간 기록
            self.trade_counts[hour_key] += 1
            self.paper_engine.portfolio.save()

        elif signal == "SELL" and symbol in positions:
            # 최소 보유 시간 체크 (연속 매도 방지)
            entry_ts = self.entry_times.get(symbol, 0)
            hold_sec = now_ts - entry_ts
            if hold_sec < MIN_HOLD_SECONDS:
                print(f"   ⏳ {symbol} 보유 {hold_sec:.0f}초 (최소 {MIN_HOLD_SECONDS}초 필요, 대기 중)")
                return

            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] 🔴 SELL {symbol} | 신뢰도: {confidence:.1%} | 가격: {price:,.0f}원 | 보유: {hold_sec:.0f}초")

            self.paper_engine.close_position(symbol, price, "AI_SELL")
            self.entry_times.pop(symbol, None)
            self.trade_counts[hour_key] += 1
            self.paper_engine.portfolio.save()

    def run(self):
        """실시간 모니터링 시작"""
        print("실시간 모니터링 시작... (Ctrl+C로 종료)")
        print("-" * 70)
        
        try:
            while self.running:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] 가격 조회 시작")
                
                for symbol in SYMBOLS:
                    try:
                        # 실시간 가격 조회
                        tickers = self.upbit.get_ticker([symbol])
                        if tickers and len(tickers) > 0:
                            price = float(tickers[0]["trade_price"])
                            self.update_price(symbol, price)
                            
                            print(f"   {symbol}: {price:,.0f}원", end="")
                            
                            # AI 신호 생성 (최소 20개 데이터 필요)
                            if len(self.price_history.get(symbol, [])) >= 20:
                                prices = self.price_history[symbol][-50:]
                                # 변동성 계산
                                vol = self.vol_calc.calculate(prices)
                                # 기본값으로 AI 신호 생성
                                result = self.ai_engine.decide(symbol, prices, vol)
                                signal = result.get("signal", "HOLD")
                                confidence = result.get("confidence", 0.0)
                                
                                if confidence >= MIN_CONFIDENCE:
                                    print(f" | {signal} 신호 ({confidence:.1%})", end="")
                                    self.process_signal(symbol, price, signal, confidence)
                            
                            print()  # 줄바꿈
                            
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"   {symbol} 오류: {e}")
                
                # 손절/익절 체크
                positions = self.paper_engine.portfolio.positions
                if positions:
                    for symbol in list(positions.keys()):
                        if symbol in self.last_prices:
                            self.paper_engine.check_exits(symbol, self.last_prices[symbol])
                
                # 포트폴리오 저장 (매 사이클마다)
                self.paper_engine.portfolio.save()
                
                # 포트폴리오 파일 업데이트 시간 표시
                portfolio_path = Path("paper_portfolio.json")
                if portfolio_path.exists():
                    mtime = portfolio_path.stat().st_mtime
                    age = time.time() - mtime
                    print(f"   📁 포트폴리오: {datetime.fromtimestamp(mtime).strftime('%H:%M:%S')} ({age:.0f}초 전)")
                
                print(f"[{timestamp}] 다음 조회까지 {CHECK_INTERVAL}초 대기...")
                print("-" * 50)
                time.sleep(CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n모니터링 종료")
        except Exception as e:
            print(f"치명적 오류: {e}")
        finally:
            self.running = False
            print("포트폴리오 저장 완료")

    def status(self):
        """현재 상태 출력"""
        print("\n" + "=" * 70)
        print("실시간 모니터링 상태")
        print("=" * 70)
        
        # 가격 정보
        print("📈 실시간 가격:")
        for symbol in SYMBOLS:
            price = self.last_prices.get(symbol, 0)
            if price > 0:
                print(f"   {symbol}: {price:,.0f}원")
        
        # 포지션 정보
        positions = self.paper_engine.portfolio.positions
        if positions:
            print("\n📊 현재 포지션:")
            for symbol, pos in positions.items():
                current = self.last_prices.get(symbol, pos["entry"])
                pnl_pct = (current - pos["entry"]) / pos["entry"] * 100
                color = "🟢" if pnl_pct >= 0 else "🔴"
                print(f"   {color} {symbol}: 진입 {pos['entry']:,.0f}원 → 현재 {current:,.0f}원 ({pnl_pct:+.2f}%)")
        
        # 오늘 거래 통계
        today = datetime.now().strftime("%Y-%m-%d")
        today_trades = [t for t in self.paper_engine.portfolio.data["trade_log"]
                       if t["date"].startswith(today)]
        
        print(f"\n📅 오늘 거래: {len(today_trades)}회")
        print(f"💰 현재 자본: {self.paper_engine.portfolio.capital:,.0f}원")
        print("=" * 70)


# ─────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="트레이더 마크 실시간 모니터링")
    parser.add_argument("--status", action="store_true", help="현재 상태 확인")
    parser.add_argument("--run", action="store_true", help="실시간 모니터링 실행")
    
    args = parser.parse_args()
    
    if args.status:
        trader = RealtimeTrader()
        trader.status()
    elif args.run:
        trader = RealtimeTrader()
        trader.run()
    else:
        # 기본: 실시간 모니터링 실행
        trader = RealtimeTrader()
        trader.run()
