#!/usr/bin/env python3
"""
Ubuntu에서 업비트 API 간단 테스트
"""

import os
from dotenv import load_dotenv
import requests
import logging

# 환경 변수 로드
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_upbit_api():
    """업비트 API 기본 테스트"""
    print("=" * 70)
    print("Ubuntu에서 업비트 API 테스트")
    print("=" * 70)
    
    # API 키 확인
    access_key = os.getenv('UPBIT_ACCESS_KEY')
    secret_key = os.getenv('UPBIT_SECRET_KEY')
    
    print(f"\n🔑 API 키 확인:")
    print(f"  Access Key: {access_key[:10]}...{access_key[-10:] if access_key else '없음'}")
    print(f"  Secret Key: {'설정됨' if secret_key else '없음'}")
    
    if not access_key or not secret_key:
        print("\n❌ API 키가 설정되지 않았습니다.")
        print("   .env 파일을 확인해주세요.")
        return False
    
    print("\n✅ API 키 확인 완료")
    
    # 1. 공용 API 테스트 (인증 없음)
    print("\n1. 공용 API 테스트 (마켓 코드 조회)...")
    try:
        response = requests.get("https://api.upbit.com/v1/market/all")
        if response.status_code == 200:
            markets = response.json()
            krw_markets = [m for m in markets if m['market'].startswith('KRW-')]
            print(f"   ✅ 성공: {len(krw_markets)}개 KRW 마켓")
            print(f"      예시: {krw_markets[0]['market']} - {krw_markets[0]['korean_name']}")
        else:
            print(f"   ❌ 실패: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return False
    
    # 2. 현재가 조회 테스트
    print("\n2. 현재가 조회 테스트...")
    try:
        markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
        markets_str = ','.join(markets)
        
        response = requests.get(
            "https://api.upbit.com/v1/ticker",
            params={'markets': markets_str}
        )
        
        if response.status_code == 200:
            tickers = response.json()
            print(f"   ✅ 성공: {len(tickers)}개 종목")
            
            for ticker in tickers:
                market = ticker['market']
                price = ticker['trade_price']
                change = ticker['signed_change_rate'] * 100
                print(f"      {market}: {price:,.0f}원 ({change:+.2f}%)")
        else:
            print(f"   ❌ 실패: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return False
    
    # 3. 캔들 데이터 테스트
    print("\n3. 캔들 데이터 조회 테스트...")
    try:
        response = requests.get(
            "https://api.upbit.com/v1/candles/days",
            params={'market': 'KRW-BTC', 'count': 5}
        )
        
        if response.status_code == 200:
            candles = response.json()
            print(f"   ✅ 성공: {len(candles)}일 데이터")
            
            for i, candle in enumerate(candles):
                date = candle['candle_date_time_kst'][:10]
                open_price = candle['opening_price']
                close_price = candle['trade_price']
                change = ((close_price - open_price) / open_price) * 100
                
                print(f"      {date}: {open_price:,.0f} → {close_price:,.0f}원 ({change:+.1f}%)")
        else:
            print(f"   ❌ 실패: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✅ Ubuntu + 업비트 API 테스트 완료!")
    print("=" * 70)
    
    print("\n🎯 Ubuntu에서 가능한 작업:")
    print("• 실시간 데이터 수신 (WebSocket)")
    print("• AI 분석 기반 자동 매매")
    print("• 24/7 서버 운영")
    print("• Docker 컨테이너 배포")
    
    return True

def check_requirements():
    """필요 패키지 확인"""
    print("\n📦 필요 패키지 확인:")
    
    try:
        import requests
        print("  ✅ requests: 설치됨")
    except ImportError:
        print("  ❌ requests: 미설치 (pip install requests)")
    
    try:
        import jwt
        print("  ✅ pyjwt: 설치됨")
    except ImportError:
        print("  ❌ pyjwt: 미설치 (pip install pyjwt)")
    
    try:
        from dotenv import load_dotenv
        print("  ✅ python-dotenv: 설치됨")
    except ImportError:
        print("  ❌ python-dotenv: 미설치 (pip install python-dotenv)")

def main():
    """메인 함수"""
    print("트레이더 마크 📊 - Ubuntu 업비트 시스템 확인")
    
    # 필요 패키지 확인
    check_requirements()
    
    # API 테스트
    success = test_upbit_api()
    
    if success:
        print("\n🚀 다음 단계:")
        print("1. 계좌 입금 (업비트 앱/웹에서)")
        print("2. AI 합의 시스템 테스트: python ai_consensus_simple.py --test")
        print("3. 모의투자 시작: python paper_trading_engine.py --test")
        print("4. 실제 API 통합: python upbit_api_simple.py --test")
    else:
        print("\n⚠️ 테스트 실패. 문제를 해결한 후 다시 시도해주세요.")

if __name__ == "__main__":
    main()