import time
import signal
import threading
from datetime import datetime
import traceback

from app.storage.db import DB
from app.config import settings
from app.monitor.telegram_logger import log_and_notify
from app.signal.ingest import ingest_and_create_signal
from app.execution.runtime import build_broker, resolve_expected_price
from app.execution.entry import execute_signal_impl
from app.execution.sync import sync_pending_entries_impl, sync_pending_exits_impl
from app.execution.triggers import (
    trigger_trailing_stop_orders_impl,
    trigger_opposite_signal_exit_orders_impl,
    trigger_time_exit_orders_impl,
    trigger_stop_loss_orders_impl,
)
from app.common.timeutil import parse_utc_ts, is_market_open, minutes_until_market_close


from app.execution.sync_logic import sync_entry_order_once, sync_exit_order_once

# 장 마감 N분 전부터 신규 진입 차단
ENTRY_CUTOFF_MINUTES = 15

# Graceful shutdown flag
_shutdown_event = threading.Event()


# --- 의존성 어댑터 (shared sync_logic 사용) ---
def _build_broker():
    return build_broker()


def _resolve_expected_price(broker, ticker: str):
    return resolve_expected_price(broker, ticker)


def _sync_entry_order_once(db, broker, *, position_id, signal_id, order_id, ticker, qty, broker_order_id):
    return sync_entry_order_once(db, broker, position_id=position_id, signal_id=signal_id,
                                order_id=order_id, ticker=ticker, qty=qty, 
                                broker_order_id=broker_order_id, log_and_notify=log_and_notify)


def _sync_exit_order_once(db, broker, *, position_id, signal_id, order_id, ticker, order_qty, broker_order_id):
    return sync_exit_order_once(db, broker, position_id=position_id, signal_id=signal_id,
                               order_id=order_id, ticker=ticker, order_qty=order_qty,
                               broker_order_id=broker_order_id, log_and_notify=log_and_notify)


def _handle_shutdown(signum, frame):
    """SIGTERM/SIGINT 시 안전하게 종료."""
    _shutdown_event.set()


def daemon_loop():
    # 시그널 핸들러 등록
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    broker = build_broker()
    log_and_notify(f"🚀 StockTrader Daemon Started [Mode: {settings.broker}]")

    db = DB("stock_trader.db")
    db.init()

    # 공유 broker 인스턴스를 클로저로 전달 (매번 새로 생성하지 않음)
    def _build_broker_shared():
        return broker

    # 초당 주기 (API 제한 및 리소스 절약 위해 1분마다 뉴스 확인)
    POLL_INTERVAL = 60
    
    # 익절 주기 (TRAILING STOP)
    TRAIL_INTERVAL = 30
    
    last_news_poll = 0
    last_trail_poll = 0

    while not _shutdown_event.is_set():
        try:
            now = time.time()

            # --- 장 운영시간 체크 (09:00~15:30 KST, 월~금, 공휴일 제외) ---
            if not is_market_open():
                _shutdown_event.wait(timeout=30)
                continue

            # --- 장 마감 임박 체크: 신규 진입 차단 ---
            remaining_min = minutes_until_market_close()
            entry_allowed = remaining_min is not None and remaining_min > ENTRY_CUTOFF_MINUTES

            # --- 1. 뉴스 갱신 및 신호 생성 (장 마감 임박 시 신규 진입 차단) ---
            if entry_allowed and now - last_news_poll >= POLL_INTERVAL:
                last_news_poll = now
                
                bundle = ingest_and_create_signal(db, log_and_notify)
                if bundle:
                    signal_id = bundle["signal_id"]
                    ticker = bundle["ticker"]
                    log_and_notify(f"💡 New Signal Generated: {ticker} (ID: {signal_id})")
                    
                    # 매수 실행
                    status = execute_signal_impl(
                        db,
                        signal_id,
                        ticker,
                        qty=1.0,
                        demo_auto_close=False,
                        _build_broker=_build_broker_shared,
                        _resolve_expected_price=_resolve_expected_price,
                        _sync_entry_order_once=_sync_entry_order_once,
                        log_and_notify=log_and_notify,
                        settings=settings,
                    )
                    log_and_notify(f"🛒 Execute Signal Status: {status}")
            elif not entry_allowed and remaining_min is not None:
                # 장 마감 임박 시 한 번만 알림
                if now - last_news_poll >= POLL_INTERVAL:
                    last_news_poll = now
                    log_and_notify(f"⏰ 장 마감 {remaining_min:.0f}분 전 — 신규 진입 차단 중")
            
            # --- 2. 체결 상태 동기화 (항상 실행) ---
            sync_pending_entries_impl(
                db,
                limit=100,
                broker=broker,
                _build_broker=_build_broker_shared,
                _resolve_expected_price=_resolve_expected_price,
                _sync_entry_order_once=_sync_entry_order_once,
                log_and_notify=log_and_notify,
            )
            
            sync_pending_exits_impl(
                db,
                limit=100,
                broker=broker,
                _build_broker=_build_broker_shared,
                _sync_exit_order_once=_sync_exit_order_once,
            )

            # --- 3. 위험 관리 및 강제 청산 루프 (항상 실행) ---
            if now - last_trail_poll >= TRAIL_INTERVAL:
                last_trail_poll = now
                
                from app.execution.runtime import collect_current_prices
                current_prices = collect_current_prices(db, broker)

                # 하드 스톱로스 (최우선)
                trigger_stop_loss_orders_impl(
                    db,
                    current_prices=current_prices,
                    stop_loss_pct=0.02,
                    limit=100,
                    broker=broker,
                    _build_broker=_build_broker_shared,
                    _sync_exit_order_once=_sync_exit_order_once,
                    log_and_notify=log_and_notify,
                )

                # 트레일링 스탑
                trigger_trailing_stop_orders_impl(
                    db,
                    current_prices=current_prices,
                    trailing_arm_pct=0.01,
                    trailing_gap_pct=0.005,
                    limit=100,
                    broker=broker,
                    _build_broker=_build_broker_shared,
                    _sync_exit_order_once=_sync_exit_order_once,
                    log_and_notify=log_and_notify,
                )
                
                # 보유 시간 제한 청산
                trigger_time_exit_orders_impl(
                    db,
                    max_hold_min=60 * 6,
                    limit=100,
                    broker=broker,
                    _build_broker=_build_broker_shared,
                    _resolve_expected_price=_resolve_expected_price,
                    _parse_sqlite_ts=parse_utc_ts,
                    _sync_exit_order_once=_sync_exit_order_once,
                    log_and_notify=log_and_notify,
                )

                # 반대 신호 발생 시 청산
                trigger_opposite_signal_exit_orders_impl(
                    db,
                    exit_score_threshold=70.0,
                    limit=100,
                    broker=broker,
                    _build_broker=_build_broker_shared,
                    _resolve_expected_price=_resolve_expected_price,
                    _sync_exit_order_once=_sync_exit_order_once,
                    log_and_notify=log_and_notify,
                )
                
            _shutdown_event.wait(timeout=5)
            
        except KeyboardInterrupt:
            _shutdown_event.set()
        except Exception as e:
            err_msg = traceback.format_exc()
            log_and_notify(f"⚠️ Daemon Exception: {e}\n{err_msg[:500]}")
            _shutdown_event.wait(timeout=15)

    log_and_notify("🛑 Daemon gracefully stopped.")
    db.close()

if __name__ == "__main__":
    daemon_loop()