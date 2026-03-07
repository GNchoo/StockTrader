#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=========================================="
echo " StockTrader Preflight Check"
echo "=========================================="

PYTHONPATH="$ROOT" python3 - <<'PY'
import sys
import os

# ── 1. 환경변수 점검 ──────────────────────────────────────
print("\n[1/6] 환경변수 점검...")
from app.config import settings

broker_name = (settings.broker or "paper").lower()
print(f"  BROKER = {broker_name}")
print(f"  KIS_MODE = {settings.kis_mode}")
print(f"  NEWS_MODE = {settings.news_mode}")

errors = []
warnings = []

if broker_name == "kis":
    if not settings.kis_app_key:
        errors.append("KIS_APP_KEY 미설정")
    if not settings.kis_app_secret:
        errors.append("KIS_APP_SECRET 미설정")
    if not settings.kis_account_no:
        errors.append("KIS_ACCOUNT_NO 미설정")
    if settings.kis_mode == "live":
        print("  ⚠️  KIS_MODE=live — 실거래 모드입니다!")

if not settings.telegram_bot_token or not settings.telegram_chat_id:
    warnings.append("텔레그램 미설정 (알림 수신 불가)")

if settings.news_mode == "sample":
    warnings.append("NEWS_MODE=sample — 실제 뉴스가 아닌 내장 샘플 뉴스 사용 중")

# ── 2. 브로커 헬스체크 ───────────────────────────────────
print("\n[2/6] 브로커 헬스체크...")
from app.execution.runtime import build_broker
broker = build_broker()
health = broker.health_check()
status = str(health.get("status", "")).upper()
print(f"  status = {status}")
print(f"  checks = {health.get('checks', {})}")

if status == "CRITICAL":
    errors.append(f"브로커 상태 CRITICAL: {health.get('reason_code', 'unknown')}")
elif status == "WARN":
    warnings.append(f"브로커 상태 WARN: {health.get('reason_code', 'unknown')}")

# ── 3. 데이터베이스 점검 ─────────────────────────────────
print("\n[3/6] 데이터베이스 점검...")
from app.storage.db import DB
try:
    db = DB("stock_trader.db")
    db.init()
    # WAL 모드 확인
    journal = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    print(f"  journal_mode = {journal}")
    if journal != "wal":
        warnings.append(f"SQLite journal_mode={journal} (WAL 권장)")
    # 테이블 존재 확인
    tables = [r[0] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    required = ["news_events", "event_tickers", "signal_scores", "positions", "orders", "position_events", "risk_state"]
    missing = [t for t in required if t not in tables]
    if missing:
        errors.append(f"누락된 테이블: {missing}")
    else:
        print(f"  테이블 {len(required)}개 확인 완료")
    db.close()
except Exception as e:
    errors.append(f"DB 초기화 실패: {e}")

# ── 4. 장 운영시간 모듈 점검 ─────────────────────────────
print("\n[4/6] 장 운영시간 모듈 점검...")
from app.common.timeutil import is_market_open, is_kr_holiday, minutes_until_market_close
from datetime import date, datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
now_kst = datetime.now(KST)
print(f"  현재 KST: {now_kst.strftime('%Y-%m-%d %H:%M:%S %A')}")
print(f"  장 운영 중: {is_market_open()}")
print(f"  오늘 공휴일: {is_kr_holiday(now_kst.date())}")
remaining = minutes_until_market_close()
if remaining is not None:
    print(f"  장 마감까지: {remaining:.0f}분")

# 2026년 공휴일 수 확인
from app.common.timeutil import _KR_HOLIDAYS
holidays_this_year = [d for d in _KR_HOLIDAYS if d.year == now_kst.year]
print(f"  {now_kst.year}년 공휴일: {len(holidays_this_year)}일 등록됨")
if len(holidays_this_year) < 10:
    warnings.append(f"{now_kst.year}년 공휴일이 {len(holidays_this_year)}일만 등록됨 (확인 필요)")

# ── 5. 리스크 파라미터 점검 ──────────────────────────────
print("\n[5/6] 리스크 파라미터 점검...")
print(f"  일일 손실 한도: {settings.risk_daily_loss_limit:,.0f}원")
print(f"  건당 최대 손실: {settings.risk_max_loss_per_trade:,.0f}원")
print(f"  종목당 최대 노출: {settings.risk_max_exposure_per_symbol:,.0f}원")
print(f"  동시 포지션: {settings.risk_max_concurrent_positions}개")
print(f"  목표 포지션 가치: {settings.risk_target_position_value:,.0f}원")
print(f"  연속 손실 쿨다운: {settings.risk_loss_streak_cooldown}회 → {settings.risk_cooldown_minutes}분")

if settings.risk_target_position_value > settings.risk_max_exposure_per_symbol:
    warnings.append("RISK_TARGET_POSITION_VALUE > RISK_MAX_EXPOSURE_PER_SYMBOL (진입 즉시 차단될 수 있음)")

# ── 6. 모듈 임포트 점검 ─────────────────────────────────
print("\n[6/6] 핵심 모듈 임포트 점검...")
critical_modules = [
    "app.daemon",
    "app.main",
    "app.execution.sync_logic",
    "app.execution.triggers",
    "app.signal.ingest",
    "app.signal.decision",
    "app.signal.technical",
]
for m in critical_modules:
    try:
        __import__(m)
        print(f"  ✓ {m}")
    except Exception as e:
        errors.append(f"임포트 실패: {m} → {e}")
        print(f"  ✗ {m}: {e}")

# ── 결과 요약 ────────────────────────────────────────────
print("\n==========================================")
if errors:
    print(f"❌ PREFLIGHT FAILED — {len(errors)}개 오류:")
    for e in errors:
        print(f"   • {e}")
    if warnings:
        print(f"\n⚠️  {len(warnings)}개 경고:")
        for w in warnings:
            print(f"   • {w}")
    sys.exit(1)

if warnings:
    print(f"⚠️  PREFLIGHT PASS (경고 {len(warnings)}개):")
    for w in warnings:
        print(f"   • {w}")
else:
    print("✅ PREFLIGHT OK — 모든 점검 통과")
print("==========================================")
PY
