#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 백테스팅 시스템
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from data_collector import DataCollector
from trading_strategy import MovingAverageCrossover, RSIMeanReversion, BollingerBandStrategy

def simple_backtest():
    """간단한 백테스팅 실행"""
    print("=" * 60)
    print("트레이더 마크 📊 - 간단한 백테스팅 시스템")
    print("=" * 60)
    
    # 데이터 수집
    print("\n1. 데이터 수집 중...")
    collector = DataCollector()
    
    # 테스트 티커 (삼성전자)
    ticker = '005930.KS'
    print(f"종목: {ticker}")
    
    # 6개월 데이터 수집
    data = collector.get_stock_data(ticker, period="6mo")
    
    if data.empty:
        print("데이터 수집 실패")
        return
    
    print(f"수집 완료: {len(data)}일치 데이터")
    print(f"기간: {data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')}")
    print(f"최근 종가: {data['Close'].iloc[-1]:,.0f}원")
    
    # 전략 생성
    print("\n2. 트레이딩 전략 설정...")
    
    strategies = [
        ("이동평균선 크로스오버 (5,20)", MovingAverageCrossover(5, 20)),
        ("RSI 평균회귀 (30,70)", RSIMeanReversion(30, 70)),
        ("볼린저밴드", BollingerBandStrategy()),
    ]
    
    # 백테스팅 시뮬레이션
    print("\n3. 백테스팅 시뮬레이션 실행...")
    print("-" * 60)
    
    initial_capital = 10000000  # 1000만원
    results = []
    
    for strategy_name, strategy in strategies:
        print(f"\n전략: {strategy_name}")
        print("-" * 40)
        
        capital = initial_capital
        position = 0  # 현재 포지션 (0: 없음, 1: 매수, -1: 매도)
        entry_price = 0
        trades = []
        
        # 일별 백테스팅
        for i in range(20, len(data)):  # 처음 20일은 기술적 지표 계산용
            historical_data = data.iloc[:i+1]
            current_date = historical_data.index[-1]
            current_price = historical_data['Close'].iloc[-1]
            
            # 신호 생성
            signal = strategy.analyze(historical_data, ticker)
            
            # 거래 실행
            if signal.action.value == 'BUY' and position <= 0:
                if position == -1:  # 숏 포지션 청산
                    pnl = (entry_price - current_price) * 100  # 100주 기준
                    capital += pnl
                    trades.append({
                        'date': current_date,
                        'action': 'CLOSE_SHORT',
                        'price': current_price,
                        'pnl': pnl
                    })
                
                # 매수 실행
                position = 1
                entry_price = current_price
                shares = int(capital * 0.1 / current_price)  # 자본의 10% 투자
                if shares > 0:
                    trades.append({
                        'date': current_date,
                        'action': 'BUY',
                        'price': current_price,
                        'shares': shares,
                        'reason': signal.reason
                    })
                    
            elif signal.action.value == 'SELL' and position >= 0:
                if position == 1:  # 롱 포지션 청산
                    pnl = (current_price - entry_price) * 100  # 100주 기준
                    capital += pnl
                    trades.append({
                        'date': current_date,
                        'action': 'CLOSE_LONG',
                        'price': current_price,
                        'pnl': pnl
                    })
                
                # 매도 실행 (숏)
                position = -1
                entry_price = current_price
                trades.append({
                    'date': current_date,
                    'action': 'SELL',
                    'price': current_price,
                    'reason': signal.reason
                })
        
        # 최종 포지션 청산
        if position == 1:  # 롱 포지션
            final_price = data['Close'].iloc[-1]
            pnl = (final_price - entry_price) * 100
            capital += pnl
            trades.append({
                'date': data.index[-1],
                'action': 'CLOSE_LONG_FINAL',
                'price': final_price,
                'pnl': pnl
            })
        elif position == -1:  # 숏 포지션
            final_price = data['Close'].iloc[-1]
            pnl = (entry_price - final_price) * 100
            capital += pnl
            trades.append({
                'date': data.index[-1],
                'action': 'CLOSE_SHORT_FINAL',
                'price': final_price,
                'pnl': pnl
            })
        
        # 결과 계산
        total_return = ((capital - initial_capital) / initial_capital) * 100
        total_trades = len([t for t in trades if t['action'] in ['BUY', 'SELL']])
        winning_trades = len([t for t in trades if 'pnl' in t and t['pnl'] > 0])
        win_rate = winning_trades / len(trades) * 100 if trades else 0
        
        results.append({
            '전략': strategy_name,
            '초기자본': initial_capital,
            '최종자본': capital,
            '수익률(%)': total_return,
            '총거래': total_trades,
            '승률(%)': win_rate,
            '거래내역': trades
        })
        
        print(f"초기 자본: {initial_capital:,.0f}원")
        print(f"최종 자본: {capital:,.0f}원")
        print(f"수익률: {total_return:.2f}%")
        print(f"총 거래: {total_trades}회")
        print(f"승률: {win_rate:.1f}%")
    
    # 결과 비교
    print("\n" + "=" * 60)
    print("전략 비교 결과")
    print("=" * 60)
    
    results_df = pd.DataFrame(results)
    print(results_df[['전략', '수익률(%)', '총거래', '승률(%)']].to_string(index=False))
    
    # 최적 전략 선택
    best_strategy = max(results, key=lambda x: x['수익률(%)'])
    print(f"\n✅ 최적 전략: {best_strategy['전략']}")
    print(f"   수익률: {best_strategy['수익률(%)']:.2f}%")
    print(f"   승률: {best_strategy['승률(%)']:.1f}%")
    
    # 시각화
    print("\n4. 결과 시각화...")
    visualize_results(data, results)
    
    print("\n" + "=" * 60)
    print("백테스팅 완료!")
    print("=" * 60)
    
    return results, best_strategy

def visualize_results(data, results):
    """결과 시각화"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle('트레이더 마크 📊 - 백테스팅 결과', fontsize=16)
    
    # 1. 주가 차트
    ax1 = axes[0, 0]
    ax1.plot(data.index, data['Close'], label='종가', color='blue', linewidth=2)
    ax1.plot(data.index, data['MA20'], label='20일 이동평균', color='red', linestyle='--', alpha=0.7)
    ax1.fill_between(data.index, data['BB_lower'], data['BB_upper'], alpha=0.2, color='gray', label='볼린저밴드')
    ax1.set_title('주가 차트 + 기술적 지표')
    ax1.set_xlabel('날짜')
    ax1.set_ylabel('가격 (원)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.ticklabel_format(style='plain', axis='y')
    
    # 2. RSI
    ax2 = axes[0, 1]
    ax2.plot(data.index, data['RSI'], label='RSI', color='purple', linewidth=2)
    ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='과매수 (70)')
    ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='과매도 (30)')
    ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
    ax2.set_title('RSI 지표')
    ax2.set_xlabel('날짜')
    ax2.set_ylabel('RSI')
    ax2.set_ylim(0, 100)
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 3. 전략별 수익률 비교
    ax3 = axes[1, 0]
    strategies = [r['전략'] for r in results]
    returns = [r['수익률(%)'] for r in results]
    
    colors = ['green' if r > 0 else 'red' for r in returns]
    bars = ax3.bar(strategies, returns, color=colors, alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.set_title('전략별 수익률 비교')
    ax3.set_xlabel('전략')
    ax3.set_ylabel('수익률 (%)')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # 수치 표시
    for bar, return_val in zip(bars, returns):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{return_val:.1f}%', ha='center', va='bottom' if height >= 0 else 'top')
    
    # 4. 거래 신호 표시
    ax4 = axes[1, 1]
    ax4.plot(data.index, data['Close'], label='종가', color='blue', linewidth=1, alpha=0.7)
    
    # 이동평균선 크로스오버 신호 표시 (예시)
    ma5 = data['MA5']
    ma20 = data['MA20']
    
    # 골든크로스 (매수 신호)
    golden_cross = (ma5.shift(1) <= ma20.shift(1)) & (ma5 > ma20)
    buy_signals = data[golden_cross]
    
    # 데드크로스 (매도 신호)
    death_cross = (ma5.shift(1) >= ma20.shift(1)) & (ma5 < ma20)
    sell_signals = data[death_cross]
    
    if not buy_signals.empty:
        ax4.scatter(buy_signals.index, buy_signals['Close'], 
                   color='green', marker='^', s=100, label='매수 신호', zorder=5)
    
    if not sell_signals.empty:
        ax4.scatter(sell_signals.index, sell_signals['Close'], 
                   color='red', marker='v', s=100, label='매도 신호', zorder=5)
    
    ax4.set_title('거래 신호 표시')
    ax4.set_xlabel('날짜')
    ax4.set_ylabel('가격 (원)')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.ticklabel_format(style='plain', axis='y')
    
    plt.tight_layout()
    
    # 그래프 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    plt.savefig(f'backtest_results_{timestamp}.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"그래프 저장 완료: backtest_results_{timestamp}.png")

if __name__ == "__main__":
    simple_backtest()