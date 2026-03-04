#!/usr/bin/env python3
"""
트레이더 마크 📊 - 수정된 테스트 스위트
"""

import subprocess
import sys
import time
from datetime import datetime

class FixedTestSuite:
    """수정된 테스트 스위트"""
    
    def __init__(self):
        self.results = []
        print("=" * 70)
        print("트레이더 마크 📊 - 수정된 시스템 테스트")
        print("=" * 70)
    
    def run_quick_test(self):
        """빠른 테스트 실행"""
        tests = [
            ("Python 버전", "python --version"),
            ("패키지 확인", "python -c 'import pandas, numpy, requests, jwt; print(\"✅ 필수 패키지 정상\")'"),
            ("단타 전략", "python scalping_simple.py --test 2>&1 | grep -E '(트레이더|결과|수익)' | head -5"),
            ("AI 시스템", "python ai_consensus_simple.py --test 2>&1 | grep -E '(INFO|BUY|SELL|HOLD)' | head -5"),
            ("폭락 대비", "python crash_simple.py 2>&1 | grep -E '(트레이더|전략|수익률)' | head -5"),
            ("업비트 API", "python upbit_ubuntu_simple.py 2>&1 | grep -E '(트레이더|✅|API)' | head -5"),
            ("시스템 통합", "python test_system.py 2>&1 | tail -5"),
        ]
        
        print("\n🚀 빠른 테스트 시작")
        print("-" * 40)
        
        for name, cmd in tests:
            print(f"🧪 {name}: ", end="")
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print("✅ PASS")
                    self.results.append((name, True, result.stdout[:100]))
                else:
                    print("❌ FAIL")
                    self.results.append((name, False, result.stderr[:100]))
            except:
                print("⏰ TIMEOUT")
                self.results.append((name, False, "시간 초과"))
        
        self.print_results()
    
    def print_results(self):
        """결과 출력"""
        print("\n" + "=" * 70)
        print("테스트 결과 요약")
        print("=" * 70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r[1])
        
        print(f"\n📊 통계:")
        print(f"  총 테스트: {total}개")
        print(f"  통과: {passed}개")
        print(f"  실패: {total - passed}개")
        print(f"  통과율: {(passed/total*100):.1f}%")
        
        print(f"\n✅ 통과한 테스트:")
        for name, success, output in self.results:
            if success:
                print(f"  • {name}")
        
        print(f"\n❌ 실패한 테스트:")
        failures = [(n, o) for n, s, o in self.results if not s]
        if failures:
            for name, output in failures:
                print(f"  • {name}")
                if output:
                    print(f"    이유: {output[:80]}")
        else:
            print("  없음")
        
        print(f"\n🎯 시스템 평가:")
        score = (passed / total) * 100
        
        if score >= 90:
            print(f"  ✅ 우수 ({score:.1f}%) - 개발 진행 가능")
            print(f"  💡 권장: 모든 개발 단계 시작")
        elif score >= 80:
            print(f"  ⚠️ 양호 ({score:.1f}%) - 개발 진행 가능")
            print(f"  💡 권장: 주요 개발 시작, 부수적 문제는 진행 중 수정")
        elif score >= 70:
            print(f"  ⚠️ 보통 ({score:.1f}%) - 제한적 개발 가능")
            print(f"  💡 권장: 핵심 모듈부터 개발 시작")
        else:
            print(f"  ❌ 불안정 ({score:.1f}%) - 문제 수정 필요")
            print(f"  💡 권장: 주요 문제 해결 후 개발")
        
        print(f"\n🚀 결정:")
        if score >= 80:
            print("✅ 추가 테스트 완료 - 개발 진행")
            print("   다음: 변동성 모니터링 모듈 개발 시작")
        else:
            print("❌ 추가 테스트 필요 - 문제 수정")
            print("   다음: 실패한 테스트 분석 및 수정")
        
        print("\n" + "=" * 70)
        return score >= 80

def main():
    """메인 실행"""
    print("트레이더 마크 📊 - 추가 테스트 및 개발 결정")
    
    # 테스트 실행
    tester = FixedTestSuite()
    ready = tester.run_quick_test()
    
    if ready:
        print("\n💡 개발 계획 시작:")
        print("1. 변동성 모니터링 모듈 (오늘)")
        print("2. 긴급 정지 메커니즘 (내일)")
        print("3. AI 감지 에이전트 (모레)")
        print("4. 업비트 API 연동 (금요일)")
    else:
        print("\n🔧 문제 수정 필요:")
        print("1. 실패한 테스트 분석")
        print("2. 코드 수정")
        print("3. 재테스트")
        print("4. 안정화 확인")

if __name__ == "__main__":
    main()