#!/usr/bin/env python3
"""
트레이더 마크 📊 - 변동성 모니터링 단위 테스트
"""

import random
from volatility_monitor import (
    APIRateManager, PriceCollector,
    VolatilityCalculator, EmergencyStopManager,
    TechnicalSignalGenerator
)

def run_tests():
    print("=" * 60)
    print("트레이더 마크 📊 - 모니터링 모듈 단위 테스트")
    print("=" * 60)

    errors = []
    passed = 0

    # ── 1. API 제한 관리자 ─────────────────────────────────
    print("\n1. APIRateManager 테스트")
    api = APIRateManager()
    for _ in range(10):
        api.call("ticker")
    s = api.stats()
    if s["total"] == 10:
        print(f"   ✅ {s['total']}회 호출, 분당 {s['rate_per_min']:.1f}회")
        passed += 1
    else:
        print(f"   ❌ API 카운터 오류: {s['total']}")
        errors.append("APIRateManager 카운터 오류")

    # ── 2. 가격 수집기 ─────────────────────────────────────
    print("\n2. PriceCollector 테스트")
    pc = PriceCollector()
    for _ in range(25):
        pc.simulate_tick("KRW-BTC")
    prices = pc.get_prices("KRW-BTC", 20)
    change = pc.get_change("KRW-BTC")

    if len(prices) == 20:
        print(f"   ✅ 가격 {pc.current['KRW-BTC']:,.0f}원 | 직전 변화: {change:+.3%}")
        passed += 1
    else:
        print(f"   ❌ 가격 히스토리 오류: {len(prices)}개")
        errors.append("PriceCollector 히스토리 오류")

    # ── 3. 변동성 계산기 ───────────────────────────────────
    print("\n3. VolatilityCalculator 테스트")
    vc = VolatilityCalculator()
    vol = vc.update("KRW-BTC", prices)
    strat = vc.suggest_strategy(vol)
    desc  = vc.describe(vol)
    print(f"   ✅ 변동성 {vol:.3%} → {strat} ({desc})")
    passed += 1

    # 임계값 경계 테스트
    boundary_tests = [
        (0.02, "AGGRESSIVE"),
        (0.04, "MODERATE"),
        (0.06, "CONSERVATIVE"),
        (0.11, "EMERGENCY_STOP"),
    ]
    all_ok = True
    for vol_val, expected in boundary_tests:
        got = vc.suggest_strategy(vol_val)
        ok = got == expected
        mark = "✅" if ok else "❌"
        print(f"   {mark} 변동성 {vol_val:.0%} → {got}")
        if not ok:
            all_ok = False
            errors.append(f"전략 매핑 오류: vol={vol_val} 예상={expected} 결과={got}")
    if all_ok:
        passed += 1

    # ── 4. 긴급 정지 ───────────────────────────────────────
    print("\n4. EmergencyStopManager 테스트")

    em_normal = EmergencyStopManager()
    normal = em_normal.check({"KRW-BTC": 0.02}, 0.02, 0.03)
    mark = "✅" if not normal else "❌"
    print(f"   {mark} 정상 상황 → 정지 {'미발동' if not normal else '발동 (오류)'}")
    if not normal:
        passed += 1
    else:
        errors.append("EmergencyStop 정상 상황에서 발동됨")

    em_crash = EmergencyStopManager()
    crash = em_crash.check({"KRW-BTC": 0.02}, 0.02, 0.15)
    mark = "✅" if crash else "❌"
    print(f"   {mark} 시장 폭락 → 정지 {'발동' if crash else '미발동 (오류)'}")
    if crash:
        print(f"       이유: {em_crash.reason}")
        passed += 1
    else:
        errors.append("EmergencyStop 폭락 상황에서 미발동")

    em_loss = EmergencyStopManager()
    loss = em_loss.check({"KRW-BTC": 0.02}, 0.07, 0.0)
    mark = "✅" if loss else "❌"
    print(f"   {mark} 포트폴리오 7% 손실 → 정지 {'발동' if loss else '미발동 (오류)'}")
    if loss:
        passed += 1
    else:
        errors.append("EmergencyStop 손실 상황에서 미발동")

    em_vol = EmergencyStopManager()
    extreme_vol = em_vol.check({"KRW-BTC": 0.12}, 0.0, 0.0)
    mark = "✅" if extreme_vol else "❌"
    print(f"   {mark} 극단적 변동성 12% → 정지 {'발동' if extreme_vol else '미발동 (오류)'}")
    if extreme_vol:
        passed += 1
    else:
        errors.append("EmergencyStop 극단 변동성에서 미발동")

    # ── 5. 기술적 신호 ─────────────────────────────────────
    print("\n5. TechnicalSignalGenerator 테스트")
    sg = TechnicalSignalGenerator()

    up_prices = [100 + i * 0.5 + random.gauss(0, 0.2) for i in range(50)]
    sig = sg.analyze("KRW-BTC", up_prices, 0.02)
    print(f"   ✅ 상승: {sig['signal']} (신뢰도 {sig['confidence']:.0%}) | {sig['reason']}")
    print(f"      RSI: {sig.get('rsi', 'N/A')}")
    passed += 1

    down_prices = [100 - i * 0.5 + random.gauss(0, 0.2) for i in range(50)]
    sig2 = sg.analyze("KRW-ETH", down_prices, 0.02)
    print(f"   ✅ 하락: {sig2['signal']} (신뢰도 {sig2['confidence']:.0%}) | {sig2['reason']}")
    passed += 1

    few_prices = [100, 101, 99]
    sig3 = sg.analyze("KRW-XRP", few_prices, 0.02)
    print(f"   ✅ 데이터 부족: {sig3['signal']} ({sig3['reason']})")
    passed += 1

    # ── 결과 ───────────────────────────────────────────────
    total = passed + len(errors)
    print(f"\n{'='*60}")
    print(f"결과: {passed}/{total} 통과")
    if errors:
        print(f"❌ 실패 {len(errors)}개:")
        for e in errors:
            print(f"   • {e}")
    else:
        print("✅ 모든 단위 테스트 통과!")
    print(f"{'='*60}")

    return len(errors) == 0

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
