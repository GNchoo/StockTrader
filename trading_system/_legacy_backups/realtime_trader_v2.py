#!/usr/bin/env python3
"""
트레이더 마크 📊 - 실시간 트레이더 v2
GitHub 검증 전략 적용:
  - ClucMay (볼린저 밴드 평균회귀)
  - Strategy005 (거래량 + RSI + Stochastic)
  - Supertrend (ATR 추세 추종)

아키텍처:
  - 10초: 현재가 조회 → 손절/익절 체크 (틱)
  - 60초: 5분봉 조회 → 전략 신호 생성 (캔들)
"""

import json, os, sys, time
from datetime import datetime
from pathlib import Path

from upbit_live_client import UpbitLiveClient
from paper_engine      import PaperEngine, INITIAL_CAPITAL, RISK_CONFIG, FEE_RATE
from strategy_engine   import Candle, decide, decide_b_majority

# ── 설정 ────────────────────────────────────────────────────
SYMBOLS         = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
TICK_INTERVAL   = 10    # 초: 현재가 조회 / 손절-익절 체크
CANDLE_INTERVAL = 60    # 초: 캔들 조회 / 전략 신호 생성
MIN_CONFIDENCE  = 0.70  # A전략 진입 최소 신뢰도 (상향)
MAX_TRADES_HOUR = 2     # 과매매 방지: 시간당 최대 거래 수 축소
MAX_OPEN_POSITIONS = 2  # 동시 보유 최대 포지션 수
MIN_HOLD_SEC    = 600   # 최소 보유 시간 (10분)
CANDLE_COUNT    = 200   # 캔들 수 (5분봉 200개 = 약 16시간)
ACTIVE_STRATEGY = "B"   # A 손절 과다 → B(다수결)을 실전 기본으로 전환
AB_STATE_FILE   = Path(__file__).parent / "ab_test_state.json"

# GitHub 상위 트레이딩봇(Freqtrade 등) 보호장치 참고
COOLDOWN_AFTER_EXIT_SEC = 300     # 청산 후 재진입 쿨다운(5분)
STOPLOSS_GUARD_WINDOW_SEC = 3600  # 최근 1시간 손절 카운트
STOPLOSS_GUARD_LIMIT = 3          # 손절 3회 이상이면
STOPLOSS_LOCK_SEC = 1800          # 30분 전역 진입 잠금
MAX_DRAWDOWN_PCT = 0.12           # 피크 대비 -12%면 진입 잠금

# 투자방식(수익 중심) 튜닝
INVESTMENT_PROFILE = "TREND_FOLLOWING_DEFENSIVE"
TRAILING_ARM_PNL = 0.015          # +1.5% 수익부터 트레일링 활성화
TRAILING_GAP = 0.010              # 고점 대비 1.0% 하락 시 청산


class ABShadowTracker:
    """B전략(실험형) 섀도우 포트폴리오 - 실제 주문 없이 성과 비교"""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.data = self._load()
        self.entry_times = {}
        for symbol, pos in self.data.get("positions", {}).items():
            opened_at = pos.get("opened_at")
            if not opened_at:
                continue
            try:
                self.entry_times[symbol] = datetime.fromisoformat(opened_at).timestamp()
            except Exception:
                pass

    def _load(self):
        if self.filepath.exists():
            try:
                return json.loads(self.filepath.read_text())
            except Exception:
                pass
        return {
            "mode": "B_majority_shadow",
            "capital": float(INITIAL_CAPITAL),
            "initial_capital": float(INITIAL_CAPITAL),
            "positions": {},
            "trade_log": [],
            "updated_at": datetime.now().isoformat(),
        }

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat()
        self.filepath.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))

    def open_position(self, symbol: str, price: float, strategy: str):
        if symbol in self.data["positions"]:
            return
        cfg = RISK_CONFIG.get(strategy, RISK_CONFIG["MODERATE"])
        order_krw = self.data["capital"] * cfg["pos_pct"]
        if order_krw < 5000 or order_krw > self.data["capital"]:
            return

        buy_fee = order_krw * FEE_RATE
        volume = (order_krw - buy_fee) / price
        self.data["capital"] -= order_krw
        self.data["positions"][symbol] = {
            "entry": price,
            "volume": volume,
            "cost": order_krw,
            "sl": price * (1 - cfg["sl"]),
            "tp": price * (1 + cfg["tp"]),
            "strategy": strategy,
            "opened_at": datetime.now().isoformat(),
        }
        self.entry_times[symbol] = time.time()
        self.data["trade_log"].append({
            "date": datetime.now().isoformat(),
            "side": "BUY",
            "symbol": symbol,
            "price": price,
            "volume": volume,
            "reason": "B_SIGNAL",
        })

    def close_position(self, symbol: str, price: float, reason: str):
        pos = self.data["positions"].get(symbol)
        if not pos:
            return
        value = pos["volume"] * price
        sell_fee = value * FEE_RATE
        net = value - sell_fee
        self.data["capital"] += net
        profit = net - pos["cost"]
        self.data["trade_log"].append({
            "date": datetime.now().isoformat(),
            "side": "SELL",
            "symbol": symbol,
            "price": price,
            "volume": pos["volume"],
            "profit": profit,
            "reason": reason,
        })
        del self.data["positions"][symbol]
        self.entry_times.pop(symbol, None)

    def check_exits(self, symbol: str, price: float):
        pos = self.data["positions"].get(symbol)
        if not pos:
            return
        if price <= pos["sl"]:
            self.close_position(symbol, price, "STOP_LOSS")
        elif price >= pos["tp"]:
            self.close_position(symbol, price, "TAKE_PROFIT")

    def process_signal(self, symbol: str, price: float, result: dict, strategy: str, min_hold_sec: int):
        signal = result.get("signal")
        if signal == "BUY" and symbol not in self.data["positions"]:
            self.open_position(symbol, price, strategy)
        elif signal == "SELL" and symbol in self.data["positions"]:
            hold = time.time() - self.entry_times.get(symbol, time.time())
            if hold >= min_hold_sec:
                self.close_position(symbol, price, "AI_SELL")

    def summary(self):
        tl = self.data.get("trade_log", [])
        sells = [t for t in tl if t.get("side") == "SELL"]
        wins = sum(1 for t in sells if float(t.get("profit", 0)) > 0)
        wr = (wins / len(sells) * 100) if sells else 0.0
        ret = (self.data["capital"] / self.data["initial_capital"] - 1) * 100
        return {
            "capital": self.data["capital"],
            "return_pct": ret,
            "trades": len(tl),
            "sell_trades": len(sells),
            "win_rate": wr,
            "positions": self.data.get("positions", {}),
            "updated_at": self.data.get("updated_at"),
        }


class RealtimeTraderV2:
    def __init__(self):
        self.upbit        = UpbitLiveClient()
        self.paper        = PaperEngine()
        self.ab_shadow    = ABShadowTracker(AB_STATE_FILE)
        self.last_prices  = {}      # symbol → 현재가
        self.entry_times  = {}      # symbol → 진입 timestamp
        self.trade_counts = {}      # "YYYY-MM-DD-HH" → count
        self.last_candle_fetch = 0  # 마지막 캔들 조회 시각
        self.candle_cache = {}      # symbol → [Candle, ...]
        self.running      = True

        # 보호장치 상태
        self.cooldown_until = {}    # symbol -> timestamp
        self.stoploss_events = []   # [timestamp, ...]
        self.global_lock_until = 0  # timestamp
        self.peak_equity = self.paper.portfolio.capital

        # 재시작 후 기존 포지션 보유시간 복원 (opened_at 기반)
        restored = 0
        for symbol, pos in self.paper.portfolio.positions.items():
            opened_at = pos.get("opened_at")
            if not opened_at:
                continue
            try:
                self.entry_times[symbol] = datetime.fromisoformat(opened_at).timestamp()
                restored += 1
            except Exception:
                pass

        print("=" * 60)
        print("트레이더 마크 📊 - 실시간 트레이더 v2")
        print(f"전략: MA(5,20) + RSI + Supertrend (검증형)")
        print(f"심볼: {', '.join(SYMBOLS)}")
        print(f"현재가 체크: {TICK_INTERVAL}초 | 캔들 분석: {CANDLE_INTERVAL}초")
        print(f"신뢰도 기준: {MIN_CONFIDENCE*100:.0f}% | 최소 보유: {MIN_HOLD_SEC}초")
        print(f"현재 자본: {self.paper.portfolio.capital:,.0f}원")
        bsum = self.ab_shadow.summary()
        print(f"B(실험) 자본: {bsum['capital']:,.0f}원 | 수익률 {bsum['return_pct']:+.2f}%")
        if restored:
            print(f"기존 포지션 보유시간 복원: {restored}개")
        print("=" * 60)

    # ── 캔들 조회 ───────────────────────────────────────────
    def fetch_candles(self, symbol: str) -> list:
        """업비트 5분봉 조회 → Candle 리스트"""
        try:
            raw = self.upbit.get_candles(symbol, unit=5, count=CANDLE_COUNT)
            if not raw or not isinstance(raw, list):
                return []
            candles = []
            for r in reversed(raw):  # 최신이 먼저 오므로 역순
                candles.append(Candle(
                    open   = float(r.get("opening_price", 0)),
                    high   = float(r.get("high_price", 0)),
                    low    = float(r.get("low_price", 0)),
                    close  = float(r.get("trade_price", 0)),
                    volume = float(r.get("candle_acc_trade_volume", 0)),
                ))
            return candles
        except Exception as e:
            print(f"  캔들 조회 오류 {symbol}: {e}")
            return []

    def _sma(self, values: list, period: int):
        if len(values) < period:
            return None
        return sum(values[-period:]) / period

    def classify_regime(self, symbol: str) -> str:
        candles = self.candle_cache.get(symbol, [])
        if len(candles) < 80:
            return "UNKNOWN"
        closes = [c.close for c in candles]
        ma20 = self._sma(closes, 20)
        ma60 = self._sma(closes, 60)
        ma20_prev = sum(closes[-40:-20]) / 20
        slope = (ma20 - ma20_prev) / ma20_prev if ma20_prev else 0

        if ma20 and ma60 and ma20 > ma60 and slope > 0.002:
            return "UPTREND"
        if ma20 and ma60 and ma20 < ma60 and slope < -0.002:
            return "DOWNTREND"
        return "RANGE"

    def choose_entry_strategy(self, symbol: str, confidence: float) -> str:
        candles = self.candle_cache.get(symbol, [])
        if len(candles) >= 20:
            closes = [c.close for c in candles[-20:]]
            vol_pct = (max(closes) - min(closes)) / min(closes) * 100
            if vol_pct >= 5:
                strategy = "CONSERVATIVE"
            elif vol_pct >= 2:
                strategy = "MODERATE"
            else:
                strategy = "AGGRESSIVE"
        else:
            strategy = "MODERATE"

        # 수익 중심이지만 방어적으로: 신뢰도 낮거나 변동 큰 코인은 보수화
        if confidence < 0.62 and strategy == "AGGRESSIVE":
            strategy = "MODERATE"
        if symbol == "KRW-XRP" and strategy == "AGGRESSIVE":
            strategy = "MODERATE"
        return strategy

    # ── 거래 제한 체크 ──────────────────────────────────────
    def can_trade(self) -> bool:
        key = datetime.now().strftime("%Y-%m-%d-%H")
        return self.trade_counts.get(key, 0) < MAX_TRADES_HOUR

    def record_trade(self):
        key = datetime.now().strftime("%Y-%m-%d-%H")
        self.trade_counts[key] = self.trade_counts.get(key, 0) + 1

    def current_equity(self) -> float:
        equity = self.paper.portfolio.capital
        for symbol, pos in self.paper.portfolio.positions.items():
            price = self.last_prices.get(symbol)
            if price:
                equity += pos["volume"] * price
        self.peak_equity = max(self.peak_equity, equity)
        return equity

    def is_global_locked(self) -> bool:
        now_ts = time.time()
        if now_ts < self.global_lock_until:
            return True

        eq = self.current_equity()
        dd = (self.peak_equity - eq) / self.peak_equity if self.peak_equity > 0 else 0
        if dd >= MAX_DRAWDOWN_PCT:
            self.global_lock_until = now_ts + STOPLOSS_LOCK_SEC
            print(f"  🛑 DrawdownGuard 발동: DD {dd:.2%} (잠금 {STOPLOSS_LOCK_SEC//60}분)")
            return True
        return False

    def mark_stoploss_event(self):
        now_ts = time.time()
        self.stoploss_events.append(now_ts)
        self.stoploss_events = [t for t in self.stoploss_events if now_ts - t <= STOPLOSS_GUARD_WINDOW_SEC]
        if len(self.stoploss_events) >= STOPLOSS_GUARD_LIMIT:
            self.global_lock_until = max(self.global_lock_until, now_ts + STOPLOSS_LOCK_SEC)
            print(f"  🛑 StoplossGuard 발동: 최근 1시간 손절 {len(self.stoploss_events)}회")

    # ── 신호 처리 ───────────────────────────────────────────
    def process_signal(self, symbol: str, price: float, result: dict):
        signal     = result["signal"]
        confidence = result["confidence"]
        reason     = result["reason"]
        now_ts     = time.time()
        positions  = self.paper.portfolio.positions
        ts         = datetime.now().strftime("%H:%M:%S")

        if signal == "BUY" and symbol not in positions:
            if len(positions) >= MAX_OPEN_POSITIONS:
                return
            if not self.can_trade():
                return
            if self.is_global_locked():
                return
            if now_ts < self.cooldown_until.get(symbol, 0):
                return

            regime = self.classify_regime(symbol)
            if INVESTMENT_PROFILE == "TREND_FOLLOWING_DEFENSIVE":
                if regime == "DOWNTREND":
                    return
                if regime == "RANGE" and confidence < 0.70:
                    return

            strategy = self.choose_entry_strategy(symbol, confidence)

            print(f"[{ts}] 🟢 BUY {symbol}")
            print(f"     신뢰도: {confidence:.0%} | 전략: {strategy} | 레짐:{regime} | {reason}")

            self.paper.open_position(symbol, price, strategy)
            self.entry_times[symbol] = now_ts
            self.record_trade()
            self.paper.portfolio.save()

        elif signal == "SELL" and symbol in positions:
            if symbol not in self.entry_times:
                opened_at = positions[symbol].get("opened_at")
                if opened_at:
                    try:
                        self.entry_times[symbol] = datetime.fromisoformat(opened_at).timestamp()
                    except Exception:
                        pass

            hold_sec = now_ts - self.entry_times.get(symbol, now_ts)
            if hold_sec < MIN_HOLD_SEC:
                print(f"  ⏳ {symbol} 최소 보유 대기 ({hold_sec:.0f}/{MIN_HOLD_SEC}초)")
                return
            if not self.can_trade():
                return

            print(f"[{ts}] 🔴 SELL {symbol}")
            print(f"     신뢰도: {confidence:.0%} | 보유: {hold_sec:.0f}초 | {reason}")

            self.paper.close_position(symbol, price, "AI_SELL")
            self.cooldown_until[symbol] = time.time() + COOLDOWN_AFTER_EXIT_SEC
            self.entry_times.pop(symbol, None)
            self.record_trade()
            self.paper.portfolio.save()

    # ── 메인 루프 ───────────────────────────────────────────
    def run(self):
        tick_count = 0

        try:
            while self.running:
                tick_count += 1
                now_ts = time.time()
                ts     = datetime.now().strftime("%H:%M:%S")

                # ── 현재가 먼저 조회 ────────────────────────
                print(f"\n[{ts}] 💹 현재가 조회")
                for symbol in SYMBOLS:
                    try:
                        tickers = self.upbit.get_ticker([symbol])
                        if tickers:
                            self.last_prices[symbol] = float(tickers[0]["trade_price"])
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"  {symbol} 가격 오류: {e}")

                # ── 캔들 조회 (60초마다) ─────────────────────
                fetch_candles_now = (now_ts - self.last_candle_fetch) >= CANDLE_INTERVAL
                if fetch_candles_now:
                    print(f"[{ts}] 📊 캔들 분석 시작")
                    self.last_candle_fetch = now_ts

                    for symbol in SYMBOLS:
                        try:
                            candles = self.fetch_candles(symbol)
                            if candles:
                                self.candle_cache[symbol] = candles
                                result_a = decide(candles, MIN_CONFIDENCE)
                                result_b = decide_b_majority(candles, 0.55)
                                sig = result_a["signal"]
                                conf = result_a["confidence"]

                                print(f"  {symbol}: A={sig} ({conf:.0%}) | {result_a['reason'][:54]}")
                                print(f"          B={result_b['signal']} ({result_b['confidence']:.0%}) | {result_b['reason'][:46]}")

                                for strat, info in result_a["signals"].items():
                                    if info["action"] != "HOLD":
                                        print(f"    └ A-{strat}: {info['action']} ({info['conf']:.0%}) {info['reason'][:36]}")

                                price = self.last_prices.get(symbol)
                                if price:
                                    if len(candles) >= 20:
                                        closes = [c.close for c in candles[-20:]]
                                        vol_pct = (max(closes) - min(closes)) / min(closes) * 100
                                        if vol_pct >= 5:
                                            b_strategy = "CONSERVATIVE"
                                        elif vol_pct >= 2:
                                            b_strategy = "MODERATE"
                                        else:
                                            b_strategy = "AGGRESSIVE"
                                    else:
                                        b_strategy = "MODERATE"

                                    # 성능 개선: B전략을 실전 기본으로 전환
                                    live_result = result_b if ACTIVE_STRATEGY == "B" else result_a
                                    self.process_signal(symbol, price, live_result)

                                    # 비교용 섀도우는 항상 B 전략 로그 유지
                                    self.ab_shadow.process_signal(symbol, price, result_b, b_strategy, MIN_HOLD_SEC)
                                else:
                                    print(f"  {symbol}: 현재가 없어 신호 대기")
                            else:
                                print(f"  {symbol}: 캔들 조회 실패")

                            time.sleep(0.3)
                        except Exception as e:
                            print(f"  {symbol} 분석 오류: {e}")

                # ── 포지션 상태 출력 ────────────────────────
                print(f"[{ts}] 📈 포지션 현황")
                for symbol in SYMBOLS:
                    price = self.last_prices.get(symbol, 0)
                    pos = self.paper.portfolio.positions.get(symbol)
                    if pos:
                        pnl = (price - pos["entry"]) / pos["entry"] * 100
                        entry_ts = self.entry_times.get(symbol)
                        if entry_ts is None and pos.get("opened_at"):
                            try:
                                entry_ts = datetime.fromisoformat(pos["opened_at"]).timestamp()
                                self.entry_times[symbol] = entry_ts
                            except Exception:
                                entry_ts = time.time()
                        hold = time.time() - (entry_ts if entry_ts is not None else time.time())
                        print(f"  {symbol}: {price:>12,.0f}원  PnL {pnl:+.2f}% ({hold:.0f}초 보유)")
                    elif price:
                        print(f"  {symbol}: {price:>12,.0f}원")

                # 트레일링 스탑 업데이트 (수익 보호)
                positions = self.paper.portfolio.positions
                if positions:
                    for symbol in list(positions.keys()):
                        pos = positions.get(symbol)
                        price = self.last_prices.get(symbol)
                        if not pos or not price:
                            continue
                        hwm = max(float(pos.get("high_watermark", pos.get("entry", price))), price)
                        pos["high_watermark"] = hwm
                        pnl = (price - pos.get("entry", price)) / pos.get("entry", price)
                        if pnl >= TRAILING_ARM_PNL:
                            trailing_sl = hwm * (1 - TRAILING_GAP)
                            # 기존 SL보다 높고, 가능하면 손익분기 이상으로 상향
                            new_sl = max(pos.get("sl", 0), trailing_sl, pos.get("bep", 0))
                            pos["sl"] = new_sl

                # 손절/익절 체크 (A) - 사유별 보호장치 연동
                if positions:
                    for symbol in list(positions.keys()):
                        pos = positions.get(symbol)
                        price = self.last_prices.get(symbol)
                        if not pos or not price:
                            continue
                        if price <= pos.get("sl", 0):
                            trailing_armed = pos.get("sl", 0) >= pos.get("bep", 10**18)
                            reason = "TRAILING_STOP" if trailing_armed else "STOP_LOSS"
                            self.paper.close_position(symbol, price, reason)
                            self.cooldown_until[symbol] = time.time() + COOLDOWN_AFTER_EXIT_SEC
                            if reason == "STOP_LOSS":
                                self.mark_stoploss_event()
                            self.entry_times.pop(symbol, None)
                        elif price >= pos.get("tp", 10**18):
                            self.paper.close_position(symbol, price, "TAKE_PROFIT")
                            self.cooldown_until[symbol] = time.time() + COOLDOWN_AFTER_EXIT_SEC
                            self.entry_times.pop(symbol, None)

                # 손절/익절 체크 (B shadow)
                b_positions = self.ab_shadow.data.get("positions", {})
                if b_positions:
                    for symbol in list(b_positions.keys()):
                        price = self.last_prices.get(symbol)
                        if price:
                            self.ab_shadow.check_exits(symbol, price)

                # 저장 (매 사이클)
                self.paper.portfolio.save()
                self.ab_shadow.save()

                cap = self.paper.portfolio.capital
                bsum = self.ab_shadow.summary()
                lock_remain = max(0, int(self.global_lock_until - time.time()))
                print(f"  A자본: {cap:,.0f}원 | A거래: {len(self.paper.portfolio.data['trade_log'])}회")
                print(f"  B자본: {bsum['capital']:,.0f}원 | B거래: {bsum['trades']}회 | B수익률 {bsum['return_pct']:+.2f}%")
                if lock_remain > 0:
                    print(f"  🛡️ 전역 진입잠금: {lock_remain}s 남음")
                print("-" * 60)

                time.sleep(TICK_INTERVAL)

        except KeyboardInterrupt:
            print("\n👋 종료")
        except Exception as e:
            print(f"❌ 치명적 오류: {e}")
            import traceback; traceback.print_exc()
        finally:
            self.paper.portfolio.save()
            self.ab_shadow.save()
            print("포트폴리오 저장 완료")


if __name__ == "__main__":
    trader = RealtimeTraderV2()
    trader.run()
