#!/usr/bin/env python3
"""
트레이더 마크 📊 - 메인 시스템 (수정판)
"""

import sys
import os
import json
from datetime import datetime

# 로깅 설정
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 모듈 임포트
from data_collector import DataCollector
from trading_strategy import MovingAverageCrossover

class SimpleTradingSystem:
    """간단한 트레이딩 시스템"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config = self.load_config(config_file)
        self.collector = DataCollector()
        self.strategy = MovingAverageCrossover(5, 20)
        
        logger.info(f"트레이더 마크 📊 시스템 초기화 완료")
        logger.info(f"전략: {self.strategy.name}")
    
    def load_config(self, config_file: str):
        """설정 파일 로드"""
        default_config = {
            'initial_capital': 10000000,
            'watchlist': ['005930.KS', '000660.KS', '035420.KS'],
            'risk_per_trade': 0.02,
            'stop_loss_percent': 0.05,
            'take_profit_percent': 0.10
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
                logger.info(f"설정 파일 로드 완료: {config_file}")
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
        
        return default_config
    
    def run_daily_analysis(self):
        """일일 분석 실행"""
        print("=" * 60)
        print("트레이더 마크 📊 - 일일 시장 분석")
        print("=" * 60)
        
        try:
            # 데이터 수집
            print("\n1. 시장 데이터 수집 중...")
            watchlist = self.config.get('watchlist', [])
            
            stock_data = {}
            for ticker in watchlist:
                data = self.collector.get_stock_data(ticker, period="5d")
                if not data.empty:
                    stock_data[ticker] = data
                    print(f"  • {ticker}: {len(data)}일 데이터 수집 완료")
            
            if not stock_data:
                print("데이터 수집 실패")
                return
            
            # 종목별 분석
            print("\n2. 종목별 트레이딩 신호 분석...")
            print("-" * 60)
            
            signals = []
            for ticker, data in stock_data.items():
                signal = self.strategy.analyze(data, ticker)
                
                if signal.action.value != 'HOLD':
                    # 포지션 사이즈 계산
                    current_price = data['Close'].iloc[-1]
                    stop_loss = current_price * (1 - self.config.get('stop_loss_percent', 0.05))
                    
                    risk_amount = self.config.get('initial_capital', 10000000) * self.config.get('risk_per_trade', 0.02)
                    risk_per_share = abs(current_price - stop_loss)
                    
                    if risk_per_share > 0:
                        position_size = int(risk_amount / risk_per_share)
                    else:
                        position_size = 0
                    
                    signal_info = {
                        'ticker': ticker,
                        'action': signal.action.value,
                        'price': current_price,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'position_size': position_size,
                        'investment': position_size * current_price if position_size > 0 else 0
                    }
                    signals.append(signal_info)
                    
                    print(f"\n[{ticker}]")
                    print(f"  신호: {signal.action.value}")
                    print(f"  현재가: {current_price:,.0f}원")
                    print(f"  신뢰도: {signal.confidence:.2f}")
                    print(f"  이유: {signal.reason}")
                    if position_size > 0:
                        print(f"  권장 포지션: {position_size}주")
                        print(f"  투자 금액: {position_size * current_price:,.0f}원")
                else:
                    print(f"\n[{ticker}]: 홀드 (신뢰도: {signal.confidence:.2f})")
            
            # 리포트 생성
            print("\n3. 일일 리포트 생성...")
            print("-" * 60)
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'analysis_time': datetime.now().strftime('%H:%M:%S'),
                'total_signals': len(signals),
                'buy_signals': len([s for s in signals if s['action'] == 'BUY']),
                'sell_signals': len([s for s in signals if s['action'] == 'SELL']),
                'signals': signals,
                'market_summary': {
                    'analyzed_stocks': len(stock_data),
                    'total_investment': sum(s.get('investment', 0) for s in signals)
                }
            }
            
            # 리포트 저장
            report_dir = 'reports'
            os.makedirs(report_dir, exist_ok=True)
            
            report_file = f"{report_dir}/daily_report_{datetime.now().strftime('%Y%m%d')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"리포트 저장 완료: {report_file}")
            
            # 요약 출력
            print(f"\n📊 일일 분석 요약:")
            print(f"  • 분석 종목: {len(stock_data)}개")
            print(f"  • 매수 신호: {report['buy_signals']}개")
            print(f"  • 매도 신호: {report['sell_signals']}개")
            print(f"  • 총 투자 금액: {report['market_summary']['total_investment']:,.0f}원")
            
            print("\n" + "=" * 60)
            print("일일 분석 완료!")
            print("=" * 60)
            
            return report
            
        except Exception as e:
            logger.error(f"일일 분석 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def run_test_mode(self):
        """테스트 모드 실행"""
        print("=" * 60)
        print("트레이더 마크 📊 - 테스트 모드")
        print("=" * 60)
        
        print("\n테스트 모드에서는 실제 거래가 실행되지 않습니다.")
        print("시장 분석만 수행하며, 리포트를 생성합니다.")
        
        report = self.run_daily_analysis()
        
        if report:
            print("\n✅ 테스트 모드 완료!")
            print("실전 모드로 전환하려면:")
            print("1. config.json 파일에서 실제 API 키 설정")
            print("2. python main_fixed.py --mode live 실행")
        else:
            print("\n⚠️ 테스트 모드 실패")
        
        return report

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='트레이더 마크 📊 트레이딩 시스템')
    parser.add_argument('--mode', choices=['test', 'analysis'], 
                       default='test', help='실행 모드')
    parser.add_argument('--config', default='config.json', help='설정 파일')
    
    args = parser.parse_args()
    
    # 시스템 초기화
    system = SimpleTradingSystem(config_file=args.config)
    
    if args.mode == 'test' or args.mode == 'analysis':
        # 테스트/분석 모드
        system.run_test_mode()
    else:
        print(f"지원되지 않는 모드: {args.mode}")
        print("사용 가능한 모드: test, analysis")

if __name__ == "__main__":
    main()