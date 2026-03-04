#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 단타 매매 모의투자
"""

import random
from datetime import datetime

class SimpleScalpingPaper:
    """간단한 단타 매매 모의투자"""
    
    def __init__(self, capital=1000000):
        self.initial = capital
        self.capital = capital
        self.portfolio = {}
        self.trades = []
        
        # 단타 설정
        self.target = 0.005  # 0.5%
        self.stop = 0.003    # 0.3%
        self.max_pos = 0.02  # 2%
        
        # 시장
        self.markets = [
            {'symbol': 'KRW-BTC', 'price': 99619000},
            {'symbol': 'KRW-ETH', 'price': 2934000},
            {'symbol': 'KRW-XRP', 'price': 2162},
        ]
    
    def get_signal(self):
        """단타 신호"""
        market = random.choice(self.markets)
        
        # 기술적 분석 시뮬레이션
        rsi = random.uniform(20, 80)
        momentum = random.uniform(-0.02, 0.02)
        
        if rsi < 30 and momentum > 0:
            signal = 'BUY'
            conf = 0.7
            reason = f"RSI {rsi:.1f} + 상승"
        elif rsi > 70 and momentum < 0:
            signal = 'SELL'
            conf = 0.7
            reason = f"RSI {rsi:.1f} + 하락"
        else:
            signal = 'HOLD'
            conf = 0.3
            reason = "신호 없음"
        
        return {
            'symbol': market['symbol'],
            'signal': signal,
            'conf': conf,
            'reason': reason,
            'price': market['price']
        }
    
    def execute_trade(self, signal):
        """거래 실행"""
        symbol = signal['symbol']
        action = signal['signal']
        price = signal['price']
        
        if action == 'BUY':
            # 매수
            amount = min(self.capital * 0.01, 50000)  # 최대 5만원
            if amount > self.capital:
                return False
            
            qty = amount / price
            self.capital -= amount
            
            if symbol in self.portfolio:
                self.portfolio[symbol] += qty
            else:
                self.portfolio[symbol] = qty
            
            self.trades.append({
                'time': datetime.now(),
                'type': 'BUY',
                'symbol': symbol,
                'amount': amount,
                'price': price
            })
            return True
        
        elif action == 'SELL':
            # 매도
            if symbol in self.portfolio and self.portfolio[symbol] > 0:
                qty = self.portfolio[symbol] * 0.5  # 50% 매도
                amount = qty * price
                
                self.capital += amount
                self.portfolio[symbol] -= qty
                
                if self.portfolio[symbol] <= 0:
                    del self.portfolio[symbol]
                
                # 수익 계산
                profit = amount * random.uniform(-0.003, 0.005)
                
                self.trades.append({
                    'time': datetime.now(),
                    'type': 'SELL',
                    'symbol': symbol,
                    'amount': amount,
                    'profit': profit,
                    'price': price
                })
                return True
        
        return False
    
    def update_prices(self):
        """가격 업데이트"""
        for market in self.markets:
            change = random.uniform(-0.02, 0.02)
            market['price'] *= (1 + change)
    
    def get_value(self):
        """포트폴리오 가치"""
        value = self.capital
        for symbol, qty in self.portfolio.items():
            market = next(m for m in self.markets if m['symbol'] == symbol)
            value += qty * market['price']
        return value
    
    def run_day(self, day_num):
        """하루 거래"""
        print(f"\n📅 Day {day_num}")
        print("-" * 30)
        
        start = self.capital
        day_trades = 0
        
        # 5분 봉 기준 288번의 기회
        for i in range(1, 289):
            # 가격 업데이트 (5분마다)
            if i % 1 == 0:
                self.update_prices()
            
            # 거래 시도 (20% 확률)
            if random.random() < 0.2 and day_trades < 50:
                signal = self.get_signal()
                
                if signal['conf'] > 0.6:
                    if self.execute_trade(signal):
                        day_trades += 1
                        
                        # 중요한 거래만 출력
                        if day_trades % 10 == 0 or i % 48 == 0:
                            print(f"  {i}/288: {signal['signal']} {signal['symbol']}")
        
        # 일일 결과
        value = self.get_value()
        profit = value - start
        profit_pct = (profit / start) * 100
        
        print(f"\n  💰 자본: {self.capital:,.0f}원")
        print(f"  📊 가치: {value:,.0f}원")
        print(f"  📈 수익: {profit:+,.0f}원 ({profit_pct:+.2f}%)")
        print(f"  🔄 거래: {day_trades}회")
        
        if self.portfolio:
            print(f"  📦 보유: {len(self.portfolio)}종목")
        
        return profit
    
    def run_simulation(self, days=3):
        """시뮬레이션 실행"""
        print("=" * 70)
        print("트레이더 마크 📊 - 단타 매매 모의투자")
        print("=" * 70)
        print(f"초기 자본: {self.initial:,.0f}원")
        print(f"기간: {days}일")
        print(f"목표: {self.target:.1%}, 손절: {self.stop:.1%}")
        print()
        
        total_profit = 0
        daily_results = []
        
        for day in range(1, days + 1):
            day_profit = self.run_day(day)
            total_profit += day_profit
            daily_results.append(day_profit)
        
        # 최종 리포트
        self.print_report(total_profit, daily_results)
    
    def print_report(self, total_profit, daily_results):
        """최종 리포트"""
        final_value = self.get_value()
        total_pct = (total_profit / self.initial) * 100
        
        print("\n" + "=" * 70)
        print("단타 매매 모의투자 결과")
        print("=" * 70)
        
        print(f"\n📈 성과:")
        print(f"  초기: {self.initial:,.0f}원")
        print(f"  최종: {final_value:,.0f}원")
        print(f"  수익: {total_profit:+,.0f}원")
        print(f"  수익률: {total_pct:+.2f}%")
        
        print(f"\n📊 거래:")
        print(f"  총 거래: {len(self.trades)}회")
        
        # 승률 계산
        wins = sum(1 for t in self.trades if t.get('profit', 0) > 0)
        losses = len(self.trades) - wins
        
        if len(self.trades) > 0:
            win_rate = (wins / len(self.trades)) * 100
            print(f"  승리: {wins}회")
            print(f"  패배: {losses}회")
            print(f"  승률: {win_rate:.1f}%")
        
        print(f"\n📅 일별:")
        for i, profit in enumerate(daily_results, 1):
            pct = (profit / self.initial) * 100
            print(f"  Day {i}: {profit:+,.0f}원 ({pct:+.2f}%)")
        
        print(f"\n📦 포트폴리오:")
        if self.portfolio:
            for symbol, qty in self.portfolio.items():
                market = next(m for m in self.markets if m['symbol'] == symbol)
                value = qty * market['price']
                print(f"  {symbol}: {qty:.6f}개 ({value:,.0f}원)")
        else:
            print("  없음")
        
        print(f"\n🎯 평가:")
        if total_pct > 3:
            print("  ✅ 우수! 단타 전략 효과적")
        elif total_pct > 0:
            print("  ⚠️ 양호. 개선 가능")
        else:
            print("  ❌ 개선 필요")
        
        print(f"\n🚀 다음 단계:")
        print("1. AI 시스템과 통합")
        print("2. 실시간 데이터 연동")
        print("3. 업비트 API 준비")
        
        print("\n" + "=" * 70)
        print("✅ 단타 매매 모의투자 완료!")
        print("=" * 70)

def main():
    """메인 실행"""
    print("트레이더 마크 📊 - 단타 매매 모의투자 시작")
    
    # 100만원으로 3일간 단타 매매
    trader = SimpleScalpingPaper(capital=1000000)
    trader.run_simulation(days=3)
    
    print("\n💡 통찰:")
    print("• 단타는 소액 수익 누적 전략")
    print("• 고빈도 거래로 많은 기회")
    print("• 엄격한 손절매 필수")
    print("• AI와 결합 시 효과적")

if __name__ == "__main__":
    main()