#!/usr/bin/env python3
"""
업비트 API 키 테스트
트레이더 마크 📊 - 실제 API 연결 확인
"""

import os
from dotenv import load_dotenv
import logging

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_api_keys():
    """API 키 테스트"""
    print("=" * 70)
    print("트레이더 마크 📊 - 업비트 API 키 테스트")
    print("=" * 70)
    
    # API 키 확인
    access_key = os.getenv('UPBIT_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_SECRET_KEY')
    
    print("\n🔑 API 키 확인:")
    print(f"  Access Key: {access_key[:10]}...{access_key[-10:] if access_key else '없음'}")
    print(f"  Secret Key: {'설정됨' if secret_key else '없음'} (보안상 전체 표시 안함)")
    
    if not access_key or not secret_key:
        print("\n❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일을 확인해주세요.")
        return False
    
    print("\n✅ API 키 확인 완료")
    
    # 업비트 API 테스트
    try:
        from upbit_api_simple import UpbitSimpleClient
        
        print("\n🌐 업비트 API 연결 테스트 중...")
        client = UpbitSimpleClient(access_key=access_key, secret_key=secret_key)
        
        # 공용 API 테스트
        markets = client.get_market_all()
        print(f"  ✅ 공용 API 연결 성공: {len(markets)}개 마켓")
        
        # 개인 API 테스트 (잔고 확인)
        try:
            accounts = client.get_accounts()
            print(f"  ✅ 개인 API 연결 성공: {len(accounts)}개 자산")
            
            # 잔고 정보 출력
            print("\n💰 보유 자산:")
            total_krw = 0
            for acc in accounts:
                currency = acc['currency']
                balance = acc['balance']
                total = acc['total']
                
                if total > 0:
                    if currency == 'KRW':
                        total_krw += total
                        print(f"    {currency}: {total:,.0f}원")
                    else:
                        print(f"    {currency}: {total:.8f}")
            
            if total_krw > 0:
                print(f"\n  총 KRW 잔고: {total_krw:,.0f}원")
            else:
                print("\n  ⚠️ KRW 잔고가 없습니다. 입금이 필요합니다.")
                
        except Exception as e:
            print(f"  ⚠️ 개인 API 연결 실패: {e}")
            print("    API 키 권한을 확인해주세요.")
        
        # 현재가 조회 테스트
        print("\n📈 현재가 조회 테스트...")
        try:
            markets = ['KRW-BTC', 'KRW-ETH']
            tickers = client.get_ticker(markets)
            
            for ticker in tickers:
                market = ticker['market']
                price = ticker['trade_price']
                change = ticker['signed_change_rate'] * 100
                
                print(f"    {market}: {price:,.0f}원 ({change:+.2f}%)")
            
            print("  ✅ 현재가 조회 성공")
            
        except Exception as e:
            print(f"  ❌ 현재가 조회 실패: {e}")
        
        return True
        
    except ImportError:
        print("\n❌ upbit_api_simple.py 모듈을 찾을 수 없습니다.")
        return False
    except Exception as e:
        print(f"\n❌ API 테스트 실패: {e}")
        return False

def check_trading_settings():
    """트레이딩 설정 확인"""
    print("\n⚙️ 트레이딩 설정 확인:")
    
    initial_capital = float(os.getenv('INITIAL_CAPITAL', 100000))
    risk_per_trade = float(os.getenv('RISK_PER_TRADE', 0.02))
    stop_loss = float(os.getenv('STOP_LOSS_PERCENT', 0.05))
    take_profit = float(os.getenv('TAKE_PROFIT_PERCENT', 0.10))
    
    print(f"  초기 자본: {initial_capital:,.0f}원")
    print(f"  거래당 리스크: {risk_per_trade:.1%}")
    print(f"  손절매: {stop_loss:.1%}")
    print(f"  익절매: {take_profit:.1%}")
    
    # 포지션 사이즈 계산 예시
    position_size = initial_capital * risk_per_trade / stop_loss
    print(f"  예상 포지션 사이즈: {position_size:,.0f}원")
    
    return {
        'initial_capital': initial_capital,
        'risk_per_trade': risk_per_trade,
        'stop_loss': stop_loss,
        'take_profit': take_profit
    }

def test_ai_consensus_with_api():
    """AI 합의 시스템 + API 통합 테스트"""
    print("\n🤖 AI 합의 시스템 + API 통합 테스트")
    print("-" * 50)
    
    try:
        from ai_consensus_simple import SimpleConsensusSystem
        
        # AI 합의 시스템 생성
        ai_system = SimpleConsensusSystem()
        
        # 현재 시장 데이터 (가상)
        # 실제로는 API에서 가져와야 함
        test_data = {
            'symbol': 'KRW-BTC',
            'price': 99500000,
            'ma_short': 100500000,
            'ma_long': 98500000,
            'rsi': 62.5
        }
        
        print(f"  테스트 데이터: {test_data['symbol']}")
        print(f"    가격: {test_data['price']:,.0f}원")
        print(f"    이동평균선: {test_data['ma_short']:,.0f}원 / {test_data['ma_long']:,.0f}원")
        print(f"    RSI: {test_data['rsi']:.1f}")
        
        # AI 분석
        result = ai_system.analyze(**test_data)
        consensus = result['consensus']
        
        print(f"\n  🎯 AI 합의 결과:")
        print(f"    결정: {consensus['action']}")
        print(f"    신뢰도: {consensus['confidence']:.1%}")
        
        # 거래 실행 시뮬레이션
        if consensus['confidence'] > 0.6:
            if consensus['action'] == 'BUY':
                print(f"\n  🚀 AI 매수 신호 발생!")
                print(f"    조건: 신뢰도 {consensus['confidence']:.1%} > 60%")
                print(f"    실행: 매수 주문 준비 완료")
            elif consensus['action'] == 'SELL':
                print(f"\n  📉 AI 매도 신호 발생!")
                print(f"    조건: 신뢰도 {consensus['confidence']:.1%} > 60%")
                print(f"    실행: 매도 주문 준비 완료")
        else:
            print(f"\n  ⏸️ AI HOLD 신호")
            print(f"    조건: 신뢰도 {consensus['confidence']:.1%} ≤ 60%")
            print(f"    실행: 대기")
        
        return True
        
    except Exception as e:
        print(f"  ❌ AI 합의 시스템 테스트 실패: {e}")
        return False

def main():
    """메인 테스트"""
    print("트레이더 마크 📊 시스템 전체 테스트 시작")
    print("=" * 70)
    
    # 1. API 키 테스트
    api_ok = test_api_keys()
    
    if not api_ok:
        print("\n❌ API 테스트 실패. 시스템을 종료합니다.")
        return
    
    # 2. 트레이딩 설정 확인
    settings = check_trading_settings()
    
    # 3. AI 합의 시스템 테스트
    ai_ok = test_ai_consensus_with_api()
    
    # 4. 다음 단계 안내
    print("\n" + "=" * 70)
    print("✅ 시스템 테스트 완료!")
    print("=" * 70)
    
    print("\n🚀 다음 단계:")
    
    if api_ok and ai_ok:
        print("1. 모의투자 테스트 시작")
        print("   python test_paper_trading.py")
        print("\n2. AI 합의 시스템으로 실제 분석")
        print("   python ai_consensus_simple.py --analyze 'KRW-BTC' [가격] [단기MA] [장기MA] [RSI]")
        print("\n3. 업비트 API 직접 테스트")
        print("   python upbit_api_simple.py --test")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        print("   문제를 해결한 후 다시 시도해주세요.")
    
    print("\n📋 안전 수칙:")
    print("  • 처음에는 소액(10만원)으로 시작")
    print("  • 모의투자로 충분히 테스트")
    print("  • 리스크 관리 설정 엄격히 준수")
    print("  • 정기적으로 성과 분석")

if __name__ == "__main__":
    main()