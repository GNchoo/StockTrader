#!/usr/bin/env python3
"""
업비트 API 간단 테스트
"""

import requests
import json
import time
from datetime import datetime

def test_upbit_api():
    """업비트 공용 API 테스트"""
    
    print("=" * 70)
    print("업비트 API 간단 테스트")
    print("=" * 70)
    
    base_url = "https://api.upbit.com/v1"
    
    # 1. 마켓 코드 조회
    print("\n1. 마켓 코드 조회...")
    try:
        response = requests.get(f"{base_url}/market/all")
        response.raise_for_status()
        markets = response.json()
        
        # KRW 마켓만 필터링
        krw_markets = [m for m in markets if m['market'].startswith('KRW-')]
        print(f"✅ KRW 마켓 {len(krw_markets)}개 조회 완료")
        
        # 상위 10개 마켓 정보
        print("\n상위 10개 KRW 마켓:")
        for i, market in enumerate(krw_markets[:10], 1):
            print(f"  {i:2}. {market['market']:12} - {market.get('korean_name', 'N/A')}")
    
    except Exception as e:
        print(f"❌ 마켓 코드 조회 실패: {e}")
        return
    
    # 2. 현재가 조회 (비트코인, 이더리움)
    print("\n2. 현재가 조회...")
    try:
        markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA']
        params = {'markets': ','.join(markets)}
        
        response = requests.get(f"{base_url}/ticker", params=params)
        response.raise_for_status()
        tickers = response.json()
        
        print("현재가 정보:")
        for ticker in tickers:
            market = ticker['market']
            price = ticker['trade_price']
            change = ticker['signed_change_rate'] * 100
            volume = ticker['acc_trade_price_24h'] / 1000000  # 백만원 단위
            
            print(f"  {market:10}: {price:>12,.0f}원 ({change:>+7.2f}%), 거래대금 {volume:>8.1f}백만원")
    
    except Exception as e:
        print(f"❌ 현재가 조회 실패: {e}")
    
    # 3. 캔들 데이터 조회 (비트코인 일봉)
    print("\n3. 캔들 데이터 조회 (비트코인 일봉)...")
    try:
        params = {
            'market': 'KRW-BTC',
            'count': 5,
            'to': datetime.now().isoformat() + 'Z'
        }
        
        response = requests.get(f"{base_url}/candles/days", params=params)
        response.raise_for_status()
        candles = response.json()
        
        # 시간순 정렬
        candles.sort(key=lambda x: x['candle_date_time_kst'])
        
        print("비트코인 최근 5일 차트:")
        for candle in candles:
            date = candle['candle_date_time_kst']
            open_price = candle['opening_price']
            close_price = candle['trade_price']
            high_price = candle['high_price']
            low_price = candle['low_price']
            volume = candle['candle_acc_trade_volume']
            
            change = ((close_price - open_price) / open_price) * 100
            change_symbol = '📈' if change > 0 else '📉' if change < 0 else '➖'
            
            print(f"  {date[:10]}: {open_price:>12,.0f} → {close_price:>12,.0f}원 {change_symbol} ({change:>+7.2f}%)")
            print(f"     고가: {high_price:>12,.0f}, 저가: {low_price:>12,.0f}, 거래량: {volume:>10.4f}")
            print()
    
    except Exception as e:
        print(f"❌ 캔들 데이터 조회 실패: {e}")
    
    # 4. 호가 정보 조회
    print("\n4. 호가 정보 조회...")
    try:
        markets = ['KRW-BTC', 'KRW-ETH']
        params = {'markets': ','.join(markets)}
        
        response = requests.get(f"{base_url}/orderbook", params=params)
        response.raise_for_status()
        orderbooks = response.json()
        
        for orderbook in orderbooks:
            market = orderbook['market']
            bids = orderbook['orderbook_units'][:3]  # 매수 호가 상위 3개
            asks = orderbook['orderbook_units'][:3]  # 매도 호가 상위 3개
            
            print(f"\n{market} 호가:")
            print("  매수 호가 (Bid):")
            for bid in bids:
                price = bid['bid_price']
                size = bid['bid_size']
                print(f"    {price:>12,.0f}원 × {size:.8f}")
            
            print("  매도 호가 (Ask):")
            for ask in asks:
                price = ask['ask_price']
                size = ask['ask_size']
                print(f"    {price:>12,.0f}원 × {size:.8f}")
    
    except Exception as e:
        print(f"❌ 호가 정보 조회 실패: {e}")
    
    # 5. 거래소 상태 확인
    print("\n5. 거래소 상태 확인...")
    try:
        # 업비트 상태 페이지 (비공식)
        status_url = "https://status.upbit.com/api/v1/status"
        response = requests.get(status_url, timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            print("✅ 업비트 서버 상태 정상")
            
            # 간단한 상태 정보 출력
            if 'indicators' in status_data:
                indicators = status_data['indicators']
                print(f"  서버 응답 시간: {indicators.get('response_time', 'N/A')}ms")
                print(f"  가용성: {indicators.get('availability', 'N/A')}%")
        else:
            print("⚠️  상태 정보를 가져올 수 없습니다")
    
    except Exception as e:
        print(f"⚠️  상태 확인 실패 (무시 가능): {e}")
    
    print("\n" + "=" * 70)
    print("테스트 완료!")
    print("=" * 70)
    
    # API 사용 팁
    print("\n📋 API 사용 팁:")
    print("1. 업비트 개발자 센터: https://upbit.com/service_center/open_api_guide")
    print("2. API 키 발급 필요: Access Key, Secret Key")
    print("3. 요청 제한: 분당 600회, 초당 10회")
    print("4. 테스트넷: 별도 테스트넷 없음 (소액으로 실전 테스트 권장)")
    print("5. 수수료: 메이커/테이커 모두 0.05%")

def check_api_limits():
    """API 제한 확인"""
    print("\n🔧 API 요청 제한 정보:")
    print("  • 분당 최대 요청: 600회")
    print("  • 초당 최대 요청: 10회")
    print("  • WebSocket: 실시간 데이터 추천")
    print("  • 캔들 데이터: 최대 200개씩 조회")
    print("\n⚠️  주의사항:")
    print("  • 과도한 요청 시 IP 차단 가능")
    print("  • 적절한 딜레이 사용 권장 (최소 0.1초)")
    print("  • 실시간 데이터는 WebSocket 사용")

if __name__ == "__main__":
    test_upbit_api()
    check_api_limits()
    
    # 다음 단계 안내
    print("\n🚀 다음 단계:")
    print("1. 업비트 계정 생성 및 본인인증")
    print("2. 개발자 센터에서 API 키 발급")
    print("3. .env 파일에 API 키 저장")
    print("4. 자동 트레이딩 시스템 개발 시작")
    print("\n실행 예시:")
    print("  export UPBIT_ACCESS_KEY=your_access_key")
    print("  export UPBIT_SECRET_KEY=your_secret_key")
    print("  python api_upbit_client.py")