#!/usr/bin/env python3
"""
트레이더 마크 📊 - 시스템 테스트 스크립트
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_data_collection():
    """데이터 수집 테스트"""
    print("=" * 50)
    print("1. 데이터 수집 모듈 테스트")
    print("=" * 50)
    
    try:
        from data_collector import DataCollector
        
        collector = DataCollector()
        
        # 삼성전자 데이터 수집 테스트
        print("\n삼성전자 데이터 수집 중...")
        samsung_data = collector.get_stock_data('005930.KS', period="1mo")
        
        if not samsung_data.empty:
            print(f"✓ 데이터 수집 성공: {len(samsung_data)}개 봉")
            print(f"  최근 종가: {samsung_data['Close'].iloc[-1]:,.0f}원")
            print(f"  RSI: {samsung_data['RSI'].iloc[-1]:.2f}")
            print(f"  이동평균(20): {samsung_data['MA20'].iloc[-1]:,.0f}원")
            
            # 데이터 저장 확인
            import glob
            data_files = glob.glob("data/*.csv")
            print(f"  저장된 데이터 파일: {len(data_files)}개")
        else:
            print("✗ 데이터 수집 실패")
            
        return True
        
    except Exception as e:
        print(f"✗ 데이터 수집 테스트 실패: {e}")
        return False

def test_trading_strategies():
    """트레이딩 전략 테스트"""
    print("\n" + "=" * 50)
    print("2. 트레이딩 전략 테스트")
    print("=" * 50)
    
    try:
        from trading_strategy import (
            MovingAverageCrossover, 
            RSIMeanReversion, 
            BollingerBandStrategy,
            StrategyManager
        )
        from data_collector import DataCollector
        
        # 샘플 데이터 생성
        collector = DataCollector()
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        import numpy as np
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(100) * 2)
        
        sample_data = pd.DataFrame({
            'Close': prices,
            'Open': prices * 0.99,
            'High': prices * 1.01,
            'Low': prices * 0.98,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        sample_data = collector.add_technical_indicators(sample_data)
        
        # 전략 테스트
        ma_strategy = MovingAverageCrossover(5, 20)
        rsi_strategy = RSIMeanReversion(30, 70)
        bb_strategy = BollingerBandStrategy()
        
        print("\n개별 전략 분석:")
        for strategy in [ma_strategy, rsi_strategy, bb_strategy]:
            signal = strategy.analyze(sample_data, "TEST")
            print(f"  • {strategy.name}: {signal.action.value} (신뢰도: {signal.confidence:.2f})")
        
        # 전략 매니저 테스트
        manager = StrategyManager()
        manager.add_strategy(ma_strategy, 1.0)
        manager.add_strategy(rsi_strategy, 0.8)
        manager.add_strategy(bb_strategy, 0.7)
        
        signals = manager.analyze_all(sample_data, "TEST")
        consensus = manager.get_consensus_signal(signals)
        
        print(f"\n전략 합의: {consensus.action.value} (신뢰도: {consensus.confidence:.2f})")
        print(f"이유: {consensus.reason}")
        
        # 포지션 사이즈 계산 테스트
        account_balance = 10000000
        entry_price = sample_data['Close'].iloc[-1]
        stop_loss = entry_price * 0.95
        
        position_size = ma_strategy.calculate_position_size(
            account_balance, entry_price, stop_loss
        )
        
        print(f"\n포지션 사이즈 계산:")
        print(f"  계좌 잔고: {account_balance:,.0f}원")
        print(f"  진입 가격: {entry_price:,.0f}원")
        print(f"  권장 포지션: {position_size}주")
        
        return True
        
    except Exception as e:
        print(f"✗ 트레이딩 전략 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backtesting():
    """백테스팅 테스트"""
    print("\n" + "=" * 50)
    print("3. 백테스팅 모듈 테스트")
    print("=" * 50)
    
    try:
        # 간단한 백테스팅 테스트
        print("백테스팅 모듈 임포트 확인...")
        from backtest_fixed import simple_backtest
        
        print("✓ 백테스팅 모듈 로드 성공")
        print("\n간단한 백테스팅 실행...")
        
        # 빠른 테스트를 위해 삼성전자만 테스트
        results, best = simple_backtest()
        
        if results:
            print("✓ 백테스팅 테스트 성공")
            return True
        else:
            print("✗ 백테스팅 결과 없음")
            return False
        
    except Exception as e:
        print(f"✗ 백테스팅 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_system():
    """메인 시스템 테스트"""
    print("\n" + "=" * 50)
    print("4. 메인 시스템 테스트")
    print("=" * 50)
    
    try:
        from main_fixed import SimpleTradingSystem
        
        print("시스템 초기화 테스트...")
        system = SimpleTradingSystem(config_file="config.json")
        
        print("✓ 시스템 초기화 성공")
        print(f"  전략: {system.strategy.name}")
        
        # 설정 파일 테스트
        import json
        with open("config.json", "r") as f:
            config = json.load(f)
        
        print("\n설정 파일 확인:")
        print(f"  초기 자본: {config.get('initial_capital', 10000000):,.0f}원")
        print(f"  모니터링 종목: {len(config.get('watchlist', []))}개")
        print(f"  리스크 per trade: {config.get('risk_per_trade', 0.02)*100}%")
        print(f"  손절: {config.get('stop_loss_percent', 0.05)*100}%")
        
        # 간단한 분석 테스트
        print("\n간단한 분석 테스트...")
        report = system.run_daily_analysis()
        
        if report:
            print("✓ 메인 시스템 테스트 성공")
            return True
        else:
            print("✗ 분석 리포트 생성 실패")
            return False
        
    except Exception as e:
        print(f"✗ 메인 시스템 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def install_requirements():
    """필요 패키지 설치 확인"""
    print("=" * 50)
    print("필요 패키지 설치 확인")
    print("=" * 50)
    
    try:
        import subprocess
        import sys
        
        requirements = [
            "yfinance",
            "pandas",
            "numpy",
            "ta",
            "matplotlib",
            "schedule",
            "scikit-learn"
        ]
        
        print("\n필요 패키지:")
        for req in requirements:
            try:
                __import__(req.replace("-", "_"))
                print(f"  ✓ {req}")
            except ImportError:
                print(f"  ✗ {req} (설치 필요)")
        
        print("\n설치 명령어:")
        print("  pip install yfinance pandas numpy ta matplotlib schedule scikit-learn")
        
        return True
        
    except Exception as e:
        print(f"패키지 확인 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("트레이더 마크 📊 - 자동 매매 시스템 테스트 스위트")
    print("=" * 60)
    
    # pandas 임포트 (테스트용)
    global pd
    import pandas as pd
    
    test_results = []
    
    # 패키지 설치 확인
    install_requirements()
    
    # 각 모듈 테스트
    test_results.append(("데이터 수집", test_data_collection()))
    test_results.append(("트레이딩 전략", test_trading_strategies()))
    test_results.append(("백테스팅", test_backtesting()))
    test_results.append(("메인 시스템", test_main_system()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in test_results:
        status = "✓ 통과" if passed else "✗ 실패"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과! 시스템이 정상적으로 준비되었습니다.")
        print("\n실행 방법:")
        print("1. 백테스팅: python backtest.py")
        print("2. 테스트 모드: python main.py --mode test")
        print("3. 실전 모드: python main.py --mode live")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 문제를 해결한 후 다시 시도해주세요.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()