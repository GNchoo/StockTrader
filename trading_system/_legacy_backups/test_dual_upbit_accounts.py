#!/usr/bin/env python3
"""A/B 업비트 계정 연결 상태 점검 스크립트"""

from upbit_live_client import UpbitLiveClient


def check(account: str):
    try:
        cli = UpbitLiveClient(account=account)
        accts = cli.get_accounts()
        krw = 0.0
        for a in accts:
            if a.get("currency") == "KRW":
                krw = float(a.get("balance", 0) or 0)
                break
        print(f"✅ {account} 계정 인증 성공 | KRW 잔고: {krw:,.0f}원 | 자산 항목: {len(accts)}개")
        return True
    except Exception as e:
        print(f"❌ {account} 계정 인증 실패 | {e}")
        return False


if __name__ == "__main__":
    ok_a = check("A")
    ok_b = check("B")

    if ok_a and ok_b:
        print("\n🎯 두 계정 모두 실전 주문 가능 상태")
    else:
        print("\n⚠️ 일부 계정 미설정/인증 실패. .env 키를 확인하세요.")
