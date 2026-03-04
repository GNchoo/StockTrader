#!/usr/bin/env python3
"""
업비트 API 간단 클라이언트
트레이더 마크 📊 - 실제 거래 연동
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
import hmac
import hashlib
import jwt
import uuid
import requests

# .env 자동 로드 (python-dotenv 우선, 없으면 수동 파싱 fallback)
ENV_FILE = os.path.join(os.path.dirname(__file__), '.env')
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_FILE)
except Exception:
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UpbitAPIError(Exception):
    """업비트 API 에러"""
    pass

class UpbitSimpleClient:
    """업비트 간단 API 클라이언트"""
    
    def __init__(self, access_key: str = None, secret_key: str = None):
        """
        업비트 API 클라이언트 초기화
        
        Args:
            access_key: API Access Key
            secret_key: API Secret Key
        """
        self.base_url = "https://api.upbit.com/v1"
        
        # API 키 설정
        self.access_key = access_key or os.getenv('UPBIT_ACCESS_KEY')
        self.secret_key = secret_key or os.getenv('UPBIT_SECRET_KEY')
        
        if self.access_key and self.secret_key:
            logger.info("업비트 API 클라이언트 초기화 (인증 모드)")
        else:
            logger.info("업비트 API 클라이언트 초기화 (읽기 전용 모드)")
        
        # 세션 설정
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'TraderMark/1.0'
        })
    
    def _generate_token(self, query: Dict = None) -> str:
        """JWT 토큰 생성"""
        if not self.access_key or not self.secret_key:
            raise UpbitAPIError("API 키가 설정되지 않았습니다.")
        
        payload = {
            'access_key': self.access_key,
            'nonce': str(uuid.uuid4()),
        }
        
        if query:
            query_hash = hashlib.sha512()
            query_hash.update(json.dumps(query, separators=(',', ':')).encode())
            payload['query_hash'] = query_hash.hexdigest()
            payload['query_hash_alg'] = 'SHA512'
        
        jwt_token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        
        if isinstance(jwt_token, bytes):
            jwt_token = jwt_token.decode('utf-8')
        
        return jwt_token
    
    def _make_request(self, method: str, endpoint: str, 
                     params: Dict = None, data: Dict = None,
                     requires_auth: bool = False) -> Dict:
        """API 요청 실행"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        headers = {}
        if requires_auth:
            if not self.access_key or not self.secret_key:
                raise UpbitAPIError("인증이 필요한 요청입니다. API 키를 설정해주세요.")
            
            token = self._generate_token(params if method == 'GET' else data)
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            if method == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, params=params, headers=headers)
            else:
                raise UpbitAPIError(f"지원하지 않는 메서드: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, dict) and 'error' in result:
                error_msg = result.get('error', {}).get('message', '알 수 없는 오류')
                raise UpbitAPIError(f"API 오류: {error_msg}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API 요청 실패: {e}")
            raise UpbitAPIError(f"네트워크 오류: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            raise UpbitAPIError(f"응답 파싱 오류: {e}")
    
    # 공용 API 메서드
    def get_market_all(self) -> List[Dict]:
        """전체 마켓 코드 조회"""
        endpoint = "market/all"
        result = self._make_request('GET', endpoint)
        
        krw_markets = [m for m in result if m['market'].startswith('KRW-')]
        logger.info(f"KRW 마켓 {len(krw_markets)}개 조회 완료")
        return krw_markets
    
    def get_ticker(self, markets: List[str]) -> List[Dict]:
        """현재가 정보 조회"""
        endpoint = "ticker"
        params = {'markets': ','.join(markets)}
        result = self._make_request('GET', endpoint, params=params)
        
        logger.info(f"{len(markets)}개 종목 현재가 조회 완료")
        return result
    
    def get_candles(self, market: str, interval: str = 'days', count: int = 200) -> List[Dict]:
        """캔들 데이터 조회"""
        # 업비트 API 엔드포인트: candles/{minutes, days, weeks, months}
        endpoint = f"candles/{interval}"
        params = {
            'market': market,
            'count': min(count, 200)
        }
        
        result = self._make_request('GET', endpoint, params=params)
        if result:
            result.sort(key=lambda x: x['candle_date_time_utc'])
        
        logger.info(f"{market} {interval} 캔들 {len(result)}개 조회 완료")
        return result
    
    # 개인 API 메서드
    def get_accounts(self) -> List[Dict]:
        """전체 계좌 조회"""
        endpoint = "accounts"
        result = self._make_request('GET', endpoint, requires_auth=True)
        
        accounts = []
        for acc in result:
            currency = acc['currency']
            balance = float(acc['balance'])
            locked = float(acc['locked'])
            
            if balance > 0 or locked > 0:
                accounts.append({
                    'currency': currency,
                    'balance': balance,
                    'locked': locked,
                    'total': balance + locked,
                    'available': balance
                })
        
        logger.info(f"계좌 조회 완료: {len(accounts)}개 자산")
        return accounts
    
    def place_order(self, market: str, side: str, volume: float, 
                   price: float = None, ord_type: str = 'limit') -> Dict:
        """주문하기"""
        endpoint = "orders"
        
        data = {
            'market': market,
            'side': side,
            'volume': str(volume),
            'ord_type': ord_type
        }
        
        if ord_type == 'limit' and price:
            data['price'] = str(price)
        elif ord_type == 'price':
            data['price'] = str(price)
        
        result = self._make_request('POST', endpoint, data=data, requires_auth=True)
        
        order_info = {
            'uuid': result.get('uuid'),
            'market': result.get('market'),
            'side': result.get('side'),
            'ord_type': result.get('ord_type'),
            'price': float(result.get('price', 0)),
            'volume': float(result.get('volume', 0)),
            'state': result.get('state'),
            'created_at': result.get('created_at')
        }
        
        logger.info(f"주문 완료: {market} {side} {volume} ({ord_type})")
        return order_info
    
    def test_connection(self) -> bool:
        """API 연결 테스트"""
        try:
            markets = self.get_market_all()
            if len(markets) > 0:
                logger.info(f"공용 API 연결 성공: {len(markets)}개 마켓")
                
                if self.access_key and self.secret_key:
                    try:
                        accounts = self.get_accounts()
                        logger.info(f"개인 API 연결 성공: {len(accounts)}개 계좌")
                        return True
                    except Exception as e:
                        logger.warning(f"개인 API 연결 실패: {e}")
                        return True
                
                return True
            else:
                logger.error("공용 API 연결 실패")
                return False
                
        except Exception as e:
            logger.error(f"API 연결 테스트 실패: {e}")
            return False

def test_client():
    """클라이언트 테스트"""
    print("=" * 70)
    print("업비트 API 클라이언트 테스트")
    print("=" * 70)
    
    # 클라이언트 생성
    client = UpbitSimpleClient()
    
    # 1. 연결 테스트
    print("\n1. API 연결 테스트...")
    if client.test_connection():
        print("✅ API 연결 성공")
    else:
        print("❌ API 연결 실패")
        return
    
    # 2. 마켓 정보
    print("\n2. 마켓 정보 조회...")
    try:
        markets = client.get_market_all()
        print(f"✅ KRW 마켓 {len(markets)}개 조회 완료")
        
        print("\n상위 5개 마켓:")
        for i, market in enumerate(markets[:5], 1):
            print(f"  {i}. {market['market']} - {market.get('korean_name', 'N/A')}")
    
    except Exception as e:
        print(f"❌ 마켓 정보 조회 실패: {e}")
    
    # 3. 현재가 조회
    print("\n3. 현재가 조회...")
    try:
        markets = ['KRW-BTC', 'KRW-ETH', 'KRW-XRP']
        tickers = client.get_ticker(markets)
        
        for ticker in tickers:
            market = ticker['market']
            price = ticker['trade_price']
            change = ticker['signed_change_rate'] * 100
            
            print(f"  {market}: {price:,.0f}원 ({change:+.2f}%)")
    
    except Exception as e:
        print(f"❌ 현재가 조회 실패: {e}")
    
    # 4. 캔들 데이터
    print("\n4. 캔들 데이터 조회...")
    try:
        candles = client.get_candles('KRW-BTC', interval='days', count=3)
        
        print("비트코인 최근 3일:")
        for candle in candles:
            date = candle['candle_date_time_kst'][:10]
            open_price = candle['opening_price']
            close_price = candle['trade_price']
            change = ((close_price - open_price) / open_price) * 100
            
            print(f"  {date}: {open_price:,.0f} → {close_price:,.0f}원 ({change:+.2f}%)")
    
    except Exception as e:
        print(f"❌ 캔들 데이터 조회 실패: {e}")
    
    print("\n" + "=" * 70)
    print("테스트 완료!")
    print("=" * 70)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='업비트 API 클라이언트')
    parser.add_argument('--test', action='store_true', help='API 연결 테스트')
    
    args = parser.parse_args()
    
    if args.test:
        test_client()
    else:
        print("사용법: python upbit_api_simple.py --test")
        print("\n환경 변수 설정:")
        print("  export UPBIT_ACCESS_KEY=your_access_key")
        print("  export UPBIT_SECRET_KEY=your_secret_key")
        print("\n또는 .env 파일 생성:")
        print("  UPBIT_ACCESS_KEY=your_access_key")
        print("  UPBIT_SECRET_KEY=your_secret_key")