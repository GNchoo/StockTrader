#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 텍스트 대시보드
터미널에서 실행 가능
"""

import json
import os
import sys
from datetime import datetime

def load_portfolio():
    """포트폴리오 데이터 로드"""
    try:
        with open('paper_portfolio.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ paper_portfolio.json 파일을 찾을 수 없습니다")
        return None
    except json.JSONDecodeError:
        print("❌ JSON 파싱 오류")
        return None

def print_dashboard(data):
    """대시보드 출력"""
    if not data:
        return
    
    print("=" * 70)
    print("트레이더 마크 📊 - 모의투자 대시보드 (터미널 버전)")
    print("=" * 70)
    
    # 기본 정보
    capital = data.get('capital', 0)
    initial = 1000000
    total_return_pct = ((capital - initial) / initial * 100)
    
    print(f"💰 현재 자본: {capital:,.0f}원")
    print(f"📈 누적 수익률: {total_return_pct:+.2f}%")
    print(f"🕒 마지막 업데이트: {data.get('last_updated', '없음')}")
    
    # 거래 통계
    trades = data.get('trade_log', [])
    print(f"📊 총 거래 횟수: {len(trades)}회")
    
    # 오늘 거래
    today = datetime.now().strftime('%Y-%m-%d')
    today_trades = [t for t in trades if t.get('date', '').startswith(today)]
    print(f"📅 오늘 거래: {len(today_trades)}회")
    
    # 승률
    profitable = len([t for t in trades if t.get('profit', 0) > 0])
    win_rate = (profitable / len(trades) * 100) if trades else 0
    print(f"🎯 승률: {win_rate:.1f}% ({profitable}승/{len(trades)-profitable}패)")
    
    # 수수료
    total_fee = 0
    for t in trades:
        if 'total_fee' in t:
            total_fee += t['total_fee']
        elif 'buy_fee' in t and 'sell_fee' in t:
            total_fee += t['buy_fee'] + t['sell_fee']
    print(f"💸 총 수수료: {total_fee:,.1f}원")
    
    # 현재 포지션
    positions = data.get('positions', {})
    if positions:
        print(f"\n📦 현재 포지션 ({len(positions)}개):")
        for sym, pos in positions.items():
            entry = pos.get('entry', 0)
            volume = pos.get('volume', 0)
            strategy = pos.get('strategy', '')
            opened = pos.get('opened_at', '')[:19]
            print(f"   {sym}: {volume:.6f} @ {entry:,.0f}원 ({strategy}, {opened})")
    else:
        print(f"\n📦 현재 포지션: 없음")
    
    # 최근 거래 (5건)
    if trades:
        print(f"\n📈 최근 거래 (5건):")
        recent = trades[-5:][::-1]  # 최신순
        for t in recent:
            date = t.get('date', '')[:19]
            side = t.get('side', '')
            symbol = t.get('symbol', '')
            price = t.get('price', 0)
            profit = t.get('profit', 0)
            reason = t.get('reason', '')
            
            side_emoji = "🟢" if side == 'BUY' else "🔴"
            profit_str = f"+{profit:.1f}" if profit >= 0 else f"{profit:.1f}"
            profit_color = "\033[92m" if profit >= 0 else "\033[91m"
            
            print(f"   {date} {side_emoji} {side} {symbol} @ {price:,.0f}원 "
                  f"{profit_color}{profit_str}원\033[0m ({reason})")
    
    print("=" * 70)
    print("실시간 모니터링 상태: ✅ 실행 중 (5초 간격)")
    print("웹 대시보드: http://localhost:8088/ (로컬)")
    print("=" * 70)

def main():
    """메인 함수"""
    print("트레이더 마크 📊 데이터 로드 중...")
    
    data = load_portfolio()
    if data:
        print_dashboard(data)
        
        # 자동 새로고침 옵션
        if len(sys.argv) > 1 and sys.argv[1] == '--watch':
            import time
            try:
                print("\n⏰ 10초마다 자동 새로고침 (Ctrl+C로 종료)...")
                while True:
                    time.sleep(10)
                    os.system('clear' if os.name == 'posix' else 'cls')
                    data = load_portfolio()
                    if data:
                        print_dashboard(data)
            except KeyboardInterrupt:
                print("\n👋 대시보드 종료")
    else:
        print("데이터를 로드할 수 없습니다.")

if __name__ == '__main__':
    main()