import json
import time
import logging
from dataclasses import dataclass
from typing import Any
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .broker_base import BrokerBase, OrderRequest, OrderResult
from app.config import settings

_log = logging.getLogger("stock_trader.kis")


class KISBrokerError(RuntimeError):
    pass


@dataclass
class KISToken:
    access_token: str
    token_type: str = "Bearer"
    expires_at: float = 0.0  # Unix timestamp


def _build_session() -> requests.Session:
    """재시도 + keep-alive 설정된 Session 생성."""
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=2, pool_maxsize=5)
    s.mount("https://", adapter)
    return s


class KISBroker(BrokerBase):
    TOKEN_REFRESH_MARGIN_SEC = 300  # 만료 5분 전에 갱신
    MAX_TOKEN_RETRIES = 2  # 401 시 토큰 재발급 후 재시도 횟수

    @staticmethod
    def _to_float(v: Any) -> float:
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip().replace(",", "")
        if s == "":
            return 0.0
        try:
            return float(s)
        except Exception:
            return 0.0

    """한국투자증권(KIS) 브로커.

    - OAuth 토큰 발급
    - 현금주문(매수/매도)
    - 기본 헬스체크

    주의: 체결동기화(정정/취소/체결조회)는 후속 단계에서 확장.
    """

    def __init__(self):
        mode = (settings.kis_mode or "paper").lower()
        if settings.kis_base_url:
            self.base_url = settings.kis_base_url
        else:
            self.base_url = (
                "https://openapivts.koreainvestment.com:29443"
                if mode == "paper"
                else "https://openapi.koreainvestment.com:9443"
            )
        self.mode = mode
        self.session = _build_session()
        self._token: KISToken | None = None

    def _split_account(self) -> tuple[str, str]:
        raw = (settings.kis_account_no or "").strip()
        if "-" in raw:
            cano, prod = raw.split("-", 1)
            return cano.strip(), (prod.strip() or settings.kis_product_code)
        return raw, settings.kis_product_code

    def _ensure_credentials(self) -> None:
        if not settings.kis_app_key or not settings.kis_app_secret:
            raise KISBrokerError("KIS credentials missing")
        cano, _ = self._split_account()
        if not cano:
            raise KISBrokerError("KIS account number missing")

    def _issue_token(self) -> KISToken:
        self._ensure_credentials()
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
        }
        r = self.session.post(url, json=payload, timeout=8)
        if not r.ok:
            raise KISBrokerError(f"token issue failed: HTTP {r.status_code} {r.text[:200]}")
        data = r.json()
        token = data.get("access_token")
        if not token:
            raise KISBrokerError(f"token missing in response: {json.dumps(data, ensure_ascii=False)[:250]}")

        import time
        # KIS access_token_token_expired 는 "YYYY-MM-DD HH:MM:SS" 형태
        expires_str = data.get("access_token_token_expired", "")
        try:
            from datetime import datetime as _dt
            exp_dt = _dt.strptime(expires_str, "%Y-%m-%d %H:%M:%S")
            expires_at = exp_dt.timestamp()
        except Exception:
            # 파싱 실패 시 기본 23시간 후 만료 가정
            expires_at = time.time() + 23 * 3600

        self._token = KISToken(
            access_token=token,
            token_type=data.get("token_type", "Bearer"),
            expires_at=expires_at,
        )
        return self._token

    def _auth_header(self) -> dict[str, str]:
        tok = self._token
        if tok is None or time.time() >= tok.expires_at - self.TOKEN_REFRESH_MARGIN_SEC:
            tok = self._issue_token()
        return {"authorization": f"Bearer {tok.access_token}"}

    def _invalidate_token(self) -> None:
        """토큰을 무효화하여 다음 요청 시 재발급."""
        self._token = None

    def _request_with_auth_retry(
        self,
        method: str,
        url: str,
        *,
        headers: dict | None = None,
        params: dict | None = None,
        json_body: dict | None = None,
        timeout: int = 10,
    ) -> requests.Response:
        """401 응답 시 토큰 재발급 후 자동 재시도.

        네트워크 에러는 Session의 Retry 어댑터가 처리.
        """
        for attempt in range(self.MAX_TOKEN_RETRIES + 1):
            auth = self._auth_header()
            merged_headers = {
                **(headers or {}),
                **auth,
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "custtype": "P",
            }
            try:
                if method.upper() == "POST":
                    r = self.session.post(url, headers=merged_headers, json=json_body, timeout=timeout)
                else:
                    r = self.session.get(url, headers=merged_headers, params=params, timeout=timeout)

                if r.status_code == 401 and attempt < self.MAX_TOKEN_RETRIES:
                    _log.warning("KIS 401 — 토큰 재발급 시도 (%d/%d)", attempt + 1, self.MAX_TOKEN_RETRIES)
                    self._invalidate_token()
                    time.sleep(0.5)
                    continue
                return r
            except requests.exceptions.ConnectionError as e:
                if attempt < self.MAX_TOKEN_RETRIES:
                    _log.warning("KIS 연결 오류 — 재시도 (%d/%d): %s", attempt + 1, self.MAX_TOKEN_RETRIES, e)
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise KISBrokerError(f"KIS connection failed after retries: {e}") from e
        raise KISBrokerError("KIS request failed: max retries exceeded")

    def _tr_id_order(self, side: str) -> str:
        s = (side or "").upper()
        if self.mode == "paper":
            return "VTTT0802U" if s == "BUY" else "VTTT0801U"
        return "TTTC0802U" if s == "BUY" else "TTTC0801U"

    def _order_cash(self, req: OrderRequest) -> dict[str, Any]:
        cano, prdt = self._split_account()
        tr_id = self._tr_id_order(req.side)
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        qty = max(1, int(round(req.qty)))

        # 시장가(01) 고정. 지정가 확장은 후속 단계에서.
        body = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt,
            "PDNO": req.ticker,
            "ORD_DVSN": "01",
            "ORD_QTY": str(qty),
            "ORD_UNPR": "0",
        }
        r = self._request_with_auth_retry(
            "POST", url,
            headers={"tr_id": tr_id, "content-type": "application/json; charset=utf-8"},
            json_body=body,
            timeout=10,
        )
        if not r.ok:
            raise KISBrokerError(f"order failed: HTTP {r.status_code} {r.text[:200]}")
        return r.json()

    def send_order(self, req: OrderRequest) -> OrderResult:
        """주문 전송.

        실거래에서 주문 접수(ACK)와 체결(FILL)을 분리한다.
        rt_cd==0은 주문 접수 성공으로만 처리하며 status='SENT'를 반환한다.
        """
        data = self._order_cash(req)
        rt_cd = str(data.get("rt_cd", ""))
        if rt_cd != "0":
            msg = data.get("msg1") or data.get("msg_cd") or "KIS_ORDER_REJECTED"
            return OrderResult(status="REJECTED", filled_qty=0, avg_price=0.0, reason_code=str(msg))

        out = data.get("output", {}) if isinstance(data, dict) else {}
        ord_no = out.get("ODNO") or out.get("odno") or ""
        return OrderResult(
            status="SENT",
            filled_qty=0,
            avg_price=0.0,
            reason_code=f"ORDER_ACCEPTED:{ord_no}" if ord_no else "ORDER_ACCEPTED",
            broker_order_id=str(ord_no) if ord_no else None,
        )

    def inquire_order(self, broker_order_id: str, ticker: str, side: str = "BUY") -> OrderResult | None:
        """주문 체결 상태 조회 (best-effort).

        참고: KIS 계좌조회 API 응답 포맷은 계좌/상품/모드에 따라 달라질 수 있어
        필드 파싱은 방어적으로 처리한다.
        """
        if not broker_order_id:
            return None

        cano, prdt = self._split_account()
        today = datetime.now().strftime("%Y%m%d")
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
        params = {
            "CANO": cano,
            "ACNT_PRDT_CD": prdt,
            "INQR_STRT_DT": today,
            "INQR_END_DT": today,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "00",
            "PDNO": ticker,
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": str(broker_order_id),
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
        }

        try:
            r = self._request_with_auth_retry(
                "GET", url,
                headers={"tr_id": "VTTC8001R" if self.mode == "paper" else "TTTC8001R"},
                params=params,
                timeout=10,
            )
            if not r.ok:
                return None
            data = r.json() if r.text else {}
        except Exception:
            return None

        if isinstance(data, dict):
            rt_cd = str(data.get("rt_cd", "0"))
            if rt_cd and rt_cd != "0":
                msg = data.get("msg1") or data.get("msg_cd") or "KIS_INQUIRE_FAILED"
                return OrderResult(status="REJECTED", filled_qty=0, avg_price=0.0, reason_code=str(msg), broker_order_id=str(broker_order_id))

        rows = []
        if isinstance(data, dict):
            rows = data.get("output1") or data.get("output") or []
        if not isinstance(rows, list):
            return None

        row = None
        for item in rows:
            if str(item.get("odno") or item.get("ODNO") or "") == str(broker_order_id):
                row = item
                break
        if not row:
            return None

        ord_status = str(row.get("ord_sts") or row.get("ORD_STS") or "").upper()
        if ord_status in {"CANCELLED", "REJECTED", "EXPIRED", "취소", "거부"}:
            return OrderResult(status="REJECTED", filled_qty=0, avg_price=0.0, reason_code=ord_status or "ORDER_REJECTED", broker_order_id=str(broker_order_id))

        ord_qty = self._to_float(row.get("ord_qty") or row.get("ORD_QTY"))
        ccld_qty = self._to_float(row.get("tot_ccld_qty") or row.get("TOT_CCLD_QTY") or row.get("ccld_qty") or row.get("CCLD_QTY"))
        avg_price = self._to_float(row.get("avg_prvs") or row.get("avg_pric") or row.get("AVG_PRIC") or row.get("tot_ccld_unpr") or row.get("TOT_CCLD_UNPR"))

        if avg_price <= 0 and ccld_qty > 0:
            total_amt = self._to_float(row.get("tot_ccld_amt") or row.get("TOT_CCLD_AMT"))
            if total_amt > 0:
                avg_price = total_amt / max(ccld_qty, 1)

        if ccld_qty <= 0:
            return OrderResult(status="SENT", filled_qty=0, avg_price=0.0, broker_order_id=str(broker_order_id))
        if ord_qty > 0 and ccld_qty < ord_qty:
            return OrderResult(status="PARTIAL_FILLED", filled_qty=ccld_qty, avg_price=avg_price, broker_order_id=str(broker_order_id))
        return OrderResult(status="FILLED", filled_qty=ccld_qty or ord_qty, avg_price=avg_price, broker_order_id=str(broker_order_id))

    def get_last_price(self, ticker: str) -> float | None:
        """현재가 조회 (국내주식 현재가 시세)."""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
        params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": str(ticker)}
        try:
            r = self._request_with_auth_retry(
                "GET", url,
                headers={"tr_id": "FHKST01010100"},
                params=params,
                timeout=8,
            )
            if not r.ok:
                return None
            data = r.json() if r.text else {}
            out = data.get("output", {}) if isinstance(data, dict) else {}
            px = self._to_float(out.get("stck_prpr") or out.get("stck_clpr") or out.get("bstp_nmix_prpr"))
            return px if px > 0 else None
        except Exception:
            return None

    def get_recent_closes(self, ticker: str, count: int = 30) -> list[float] | None:
        """KIS API를 통해 과거 일봉 종가 배열을 반환 (오래된 순)."""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-price"
        
        # 참고: KIS API는 최신 데이터부터 내림차순으로 반환
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": str(ticker),
            "FID_PERIOD_DIV_CODE": "D",
            "FID_ORG_ADJ_PRC": "0",
        }
        
        try:
            r = self._request_with_auth_retry(
                "GET", url,
                headers={"tr_id": "FHKST01010400"},
                params=params,
                timeout=8,
            )
            if not r.ok:
                return None
            data = r.json() if r.text else {}
            out = data.get("output", [])
            if not out or not isinstance(out, list):
                return None
            
            closes = []
            for item in out[:count]:
                price = self._to_float(item.get("stck_clpr"))
                if price > 0:
                    closes.append(price)
            
            if not closes:
                return None
                
            # 가장 오래된 데이터가 배열 앞쪽에 오도록 역순 정렬
            closes.reverse()
            return closes
        except Exception:
            return None

    def health_check(self) -> dict:
        has_keys = bool(settings.kis_app_key and settings.kis_app_secret)
        has_account = bool(settings.kis_account_no)

        if has_keys and has_account:
            status = "OK"
            reason = None
        elif has_keys and not has_account:
            status = "WARN"
            reason = "MISSING_ACCOUNT"
        else:
            status = "CRITICAL"
            reason = "MISSING_CREDENTIALS"

        return {
            "status": status,
            "reason_code": reason,
            "checks": {
                "broker": "kis",
                "mode": self.mode,
                "base_url": self.base_url,
                "has_app_key": bool(settings.kis_app_key),
                "has_app_secret": bool(settings.kis_app_secret),
                "has_account_no": has_account,
                "product_code": settings.kis_product_code,
            },
        }
