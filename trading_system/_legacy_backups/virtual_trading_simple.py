#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 가상 모의투자 시스템
3월 16일까지 시스템 구축
"""

import random
from datetime import datetime, timedelta
import json

class SimpleVirtualTrading:
    """간단한 가상 모의투자"""
    
    def __init__(self, capital=1000000):
        self.initial_capital = capital
        self.capital = capital
        self.portfolio = {}
        self.trades = []
        
        # 업비트 주요 종목
        self.markets = [
            {'symbol': 'KRW-BTC', 'price': 99619000, 'name': '비트코인'},
            {'symbol': 'KRW-ETH', 'price': 2934000, 'name': '이더리움'},
            {'symbol': 'KRW-XRP', 'price': 2162, 'name': '리플'},
        ]
    
    def simulate_ai_signal(self):
        """AI 신호 시뮬레이션"""
        market = random.choice(self.markets)
        
        # 가상 분석
        action = random.choice(['BUY', 'SELL', 'HOLD'])
        confidence = random.uniform(0.3, 0.9)
        
        return {
            'symbol': market['symbol'],
            'action': action,
            'confidence': confidence,
            'price': market['price']
        }
    
    def execute_trade(self, signal):
        """가상 거래 실행"""
        symbol = signal['symbol']
        action = signal['action']
        price = signal['price']
        
        if action == 'BUY':
            # 매수
            amount = min(self.capital * 0.1, 100000)  # 최대 10만원
            quantity = amount / price
            
            if amount <= self.capital:
                self.capital -= amount
                if symbol in self.portfolio:
                    self.portfolio[symbol] += quantity
                else:
                    self.portfolio[symbol] = quantity
                
                self.trades.append({
                    'time': datetime.now(),
                    'type': 'BUY',
                    'symbol': symbol,
                    'price': price,
                    'quantity': quantity,
                    'amount': amount
                })
                return True
        
        elif action == 'SELL':
            # 매도
            if symbol in self.portfolio and self.portfolio[symbol] > 0:
                quantity = self.portfolio[symbol] * 0.5  # 50% 매도
                amount = quantity * price
                
                self.capital += amount
                self.portfolio[symbol] -= quantity
                
                if self.portfolio[symbol] <= 0:
                    del self.portfolio[symbol]
                
                self.trades.append({
                    'time': datetime.now(),
                    'type': 'SELL',
                    'symbol': symbol,
                    'price': price,
                    'quantity': quantity,
                    'amount': amount
                })
                return True
        
        return False
    
    def update_prices(self):
        """가격 업데이트 시뮬레이션"""
        for market in self.markets:
            change = random.uniform(-0.03, 0.03)  # -3% ~ +3%
            market['price'] *= (1 + change)
    
    def get_portfolio_value(self):
        """포트폴리오 가치 계산"""
        value = self.capital
        for symbol, quantity in self.portfolio.items():
            market = next(m for m in self.markets if m['symbol'] == symbol)
            value += quantity * market['price']
        return value
    
    def run_simulation(self, days=7):
        """시뮬레이션 실행"""
        print("=" * 70)
        print("가상 100만원 모의투자 시뮬레이션")
        print("=" * 70)
        print(f"초기 자본: {self.initial_capital:,.0f}원")
        print(f"시뮬레이션 기간: {days}일")
        print()
        
        for day in range(1, days + 1):
            print(f"📅 Day {day}/{days}")
            print("-" * 40)
            
            # 가격 업데이트
            self.update_prices()
            
            # 포트폴리오 가치
            portfolio_value = self.get_portfolio_value()
            return_pct = ((portfolio_value / self.initial_capital) - 1) * 100
            
            print(f"현금: {self.capital:,.0f}원")
            print(f"포트폴리오: {portfolio_value:,.0f}원")
            print(f"수익률: {return_pct:+.2f}%")
            
            # 보유 종목
            if self.portfolio:
                print(f"\n보유 종목:")
                for symbol, quantity in self.portfolio.items():
                    market = next(m for m in self.markets if m['symbol'] == symbol)
                    value = quantity * market['price']
                    print(f"  {symbol}: {quantity:.6f}개 ({value:,.0f}원)")
            
            # AI 신호 및 거래 (50% 확률)
            if random.random() < 0.5:
                signal = self.simulate_ai_signal()
                if signal['confidence'] > 0.6:
                    print(f"\n🤖 AI 신호: {signal['symbol']} {signal['action']} "
                          f"(신뢰도: {signal['confidence']:.0%})")
                    
                    if self.execute_trade(signal):
                        print(f"  ✅ {signal['action']} 실행 완료")
            
            print()
        
        # 최종 리포트
        self.print_final_report()
    
    def print_final_report(self):
        """최종 리포트"""
        final_value = self.get_portfolio_value()
        total_return = final_value - self.initial_capital
        return_pct = (total_return / self.initial_capital) * 100
        
        print("=" * 70)
        print("시뮬레이션 최종 리포트")
        print("=" * 70)
        print()
        
        print(f"초기 자본: {self.initial_capital:,.0f}원")
        print(f"최종 가치: {final_value:,.0f}원")
        print(f"총 수익: {total_return:+,.0f}원")
        print(f"수익률: {return_pct:+.2f}%")
        print()
        
        print(f"총 거래: {len(self.trades)}회")
        print(f"보유 종목: {len(self.portfolio)}개")
        print()
        
        print("🎯 3월 16일까지 할 일:")
        print("1. AI 합의 시스템 고도화")
        print("2. 업비트 API 실제 연동")
        print("3. 리스크 관리 시스템 완성")
        print("4. 모니터링 대시보드 개발")
        print()
        
        print("=" * 70)
        print("✅ 시뮬레이션 완료! 실전 준비 중...")
        print("=" * 70)

def main():
    """메인 실행"""
    print("트레이더 마크 📊 - 3월 16일 실전 투자 준비")
    
    # 가상 100만원으로 시뮬레이션
    trader = SimpleVirtualTrading(capital=1000000)
    
    # 7일 시뮬레이션 실행
    trader.run_simulation(days=7)
    
    # 다음 단계 안내
    print("\n🚀 다음 실행 명령어:")
    print("python ai_consensus_simple.py --test")
    print("python upbit_ubuntu_simple.py")
    print("python paper_trading_engine.py --test")

if __name__ == "__main__":
    main()