#!/usr/bin/env python3
"""
트레이더 마크 📊 - 간단한 AI 합의 시스템
"""

import logging
from typing import Dict, List
from enum import Enum
import numpy as np
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradeAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class SimpleAIAgent:
    """간단한 AI 에이전트"""
    
    def __init__(self, name: str, role: str, weight: float = 1.0):
        self.name = name
        self.role = role
        self.weight = weight
        
        # 역할별 편향 설정
        self.bias = self._get_bias(role)
    
    def _get_bias(self, role: str) -> float:
        """역할별 편향"""
        biases = {
            'bull': 0.1,      # 낙관적 (+10%)
            'bear': -0.1,     # 비관적 (-10%)
            'analyst': 0.0,   # 중립
            'risk': -0.05,    # 리스크 관리 (약간 방어적)
        }
        return biases.get(role, 0.0)
    
    def analyze(self, price: float, ma_short: float, ma_long: float, rsi: float) -> Dict:
        """기술적 분석"""
        
        # 이동평균선 분석
        ma_ratio = ma_short / ma_long
        
        if ma_ratio > 1.02:  # 골든크로스
            base_action = TradeAction.BUY
            reason = f"골든크로스 (MA 비율: {ma_ratio:.3f})"
        elif ma_ratio < 0.98:  # 데드크로스
            base_action = TradeAction.SELL
            reason = f"데드크로스 (MA 비율: {ma_ratio:.3f})"
        else:
            base_action = TradeAction.HOLD
            reason = f"이동평균선 정렬 (MA 비율: {ma_ratio:.3f})"
        
        # RSI 분석
        if rsi < 30:
            if base_action == TradeAction.SELL:
                base_action = TradeAction.BUY
                reason += f", RSI 과매도({rsi:.1f})로 반전 기대"
            else:
                reason += f", RSI 과매도({rsi:.1f})"
        elif rsi > 70:
            if base_action == TradeAction.BUY:
                base_action = TradeAction.SELL
                reason += f", RSI 과매수({rsi:.1f})로 조정 예상"
            else:
                reason += f", RSI 과매수({rsi:.1f})"
        
        # 역할 편향 적용
        final_action = self._apply_bias(base_action)
        if final_action != base_action:
            reason += f" ({self.role} 관점 적용)"
        
        # 신뢰도 계산
        confidence = self._calculate_confidence(ma_ratio, rsi)
        
        return {
            'agent': self.name,
            'role': self.role,
            'action': final_action,
            'confidence': confidence,
            'reason': reason,
            'bias': self.bias
        }
    
    def _apply_bias(self, action: TradeAction) -> TradeAction:
        """편향 적용"""
        if self.bias > 0 and action == TradeAction.HOLD:
            return TradeAction.BUY
        elif self.bias < 0 and action == TradeAction.HOLD:
            return TradeAction.SELL
        else:
            return action
    
    def _calculate_confidence(self, ma_ratio: float, rsi: float) -> float:
        """신뢰도 계산"""
        confidence = 0.5
        
        # 이동평균선 신호 강도
        ma_strength = abs(ma_ratio - 1.0)
        if ma_strength > 0.05:
            confidence += 0.2
        
        # RSI 신호 강도
        rsi_strength = 0
        if rsi < 30 or rsi > 70:
            rsi_strength = 0.2
        elif rsi < 40 or rsi > 60:
            rsi_strength = 0.1
        
        confidence += rsi_strength
        
        # 역할별 신뢰도 조정
        if self.role == 'risk':
            confidence *= 0.9  # 리스크 관리자는 보수적
        
        return max(0.1, min(0.9, confidence))

class SimpleConsensusSystem:
    """간단한 합의 시스템"""
    
    def __init__(self):
        self.agents = []
        self.history = []
        
        # 기본 에이전트 생성
        self._create_default_agents()
    
    def _create_default_agents(self):
        """기본 에이전트 생성"""
        agents_config = [
            ('MA_Expert', 'analyst', 1.0),
            ('RSI_Analyst', 'analyst', 0.8),
            ('Bull_Trader', 'bull', 0.7),
            ('Bear_Trader', 'bear', 0.7),
            ('Risk_Manager', 'risk', 1.2)
        ]
        
        for name, role, weight in agents_config:
            agent = SimpleAIAgent(name, role, weight)
            self.agents.append(agent)
        
        logger.info(f"{len(self.agents)}개 AI 에이전트 생성 완료")
    
    def analyze(self, symbol: str, price: float, ma_short: float, ma_long: float, rsi: float) -> Dict:
        """합의 분석"""
        logger.info(f"AI 합의 분석 시작: {symbol}")
        
        # 각 에이전트 분석
        analyses = []
        for agent in self.agents:
            analysis = agent.analyze(price, ma_short, ma_long, rsi)
            analyses.append(analysis)
        
        # 투표 집계
        consensus = self._aggregate_votes(analyses)
        
        # 결과 저장
        result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'market_data': {
                'price': price,
                'ma_short': ma_short,
                'ma_long': ma_long,
                'rsi': rsi
            },
            'consensus': consensus,
            'agent_analyses': analyses
        }
        
        self.history.append(result)
        logger.info(f"AI 합의 완료: {consensus['action']} (신뢰도: {consensus['confidence']:.1%})")
        
        return result
    
    def _aggregate_votes(self, analyses: List[Dict]) -> Dict:
        """투표 집계"""
        votes = {action: 0.0 for action in TradeAction}
        
        for analysis in analyses:
            action = analysis['action']
            confidence = analysis['confidence']
            weight = analysis.get('weight', 1.0)
            
            votes[action] += confidence * weight
        
        # 정규화
        total = sum(votes.values())
        if total > 0:
            for action in votes:
                votes[action] /= total
        
        # 최종 결정
        winning_action = max(votes.items(), key=lambda x: x[1])[0]
        confidence = votes[winning_action]
        
        # 이유 수집
        reasons = []
        for analysis in analyses:
            if analysis['action'] == winning_action:
                reasons.append(f"{analysis['agent']}: {analysis['reason']}")
        
        # 최대 3개 이유
        if len(reasons) > 3:
            reasons = reasons[:3]
        
        return {
            'action': winning_action.value,
            'confidence': confidence,
            'reasons': reasons,
            'vote_distribution': {k.value: v for k, v in votes.items()}
        }
    
    def get_summary(self) -> Dict:
        """시스템 요약"""
        if not self.history:
            return {"message": "아직 분석 기록이 없습니다."}
        
        recent = self.history[-5:] if len(self.history) > 5 else self.history
        
        action_counts = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        for record in recent:
            action = record['consensus']['action']
            action_counts[action] += 1
        
        return {
            'total_analyses': len(self.history),
            'recent_actions': action_counts,
            'active_agents': len(self.agents),
            'last_analysis': self.history[-1]['consensus'] if self.history else None
        }

def test_simple_consensus():
    """간단한 테스트"""
    print("=" * 70)
    print("트레이더 마크 📊 - AI 합의 시스템 (간단 버전)")
    print("=" * 70)
    
    # 시스템 생성
    system = SimpleConsensusSystem()
    
    # 테스트 데이터
    test_cases = [
        {
            'symbol': 'KRW-BTC',
            'price': 99500000,
            'ma_short': 102000000,  # 골든크로스
            'ma_long': 98000000,
            'rsi': 65.5
        },
        {
            'symbol': 'KRW-ETH',
            'price': 2920000,
            'ma_short': 2850000,    # 데드크로스
            'ma_long': 2950000,
            'rsi': 35.0
        },
        {
            'symbol': 'KRW-XRP',
            'price': 2160,
            'ma_short': 2150,       # 정렬 상태
            'ma_long': 2160,
            'rsi': 45.0
        }
    ]
    
    for test in test_cases:
        print(f"\n📊 {test['symbol']} 분석:")
        print(f"  가격: {test['price']:,.0f}원")
        print(f"  이동평균선: {test['ma_short']:,.0f}원 / {test['ma_long']:,.0f}원")
        print(f"  RSI: {test['rsi']:.1f}")
        
        result = system.analyze(**test)
        consensus = result['consensus']
        
        print(f"\n  🤖 AI 합의 결과:")
        print(f"    결정: {consensus['action']}")
        print(f"    신뢰도: {consensus['confidence']:.1%}")
        
        print(f"    이유:")
        for i, reason in enumerate(consensus['reasons'], 1):
            print(f"      {i}. {reason}")
        
        print(f"    투표 분포:")
        for action, ratio in consensus['vote_distribution'].items():
            print(f"      {action}: {ratio:.1%}")
    
    # 시스템 요약
    print("\n📈 시스템 요약:")
    summary = system.get_summary()
    print(f"  총 분석: {summary['total_analyses']}회")
    print(f"  활성 에이전트: {summary['active_agents']}개")
    
    if summary['recent_actions']:
        print(f"  최근 액션 분포:")
        for action, count in summary['recent_actions'].items():
            print(f"    {action}: {count}회")
    
    print("\n" + "=" * 70)
    print("✅ AI 합의 시스템 테스트 완료!")
    print("=" * 70)

def quick_analysis(symbol: str, price: float, ma_short: float, ma_long: float, rsi: float):
    """빠른 분석"""
    system = SimpleConsensusSystem()
    result = system.analyze(symbol, price, ma_short, ma_long, rsi)
    
    consensus = result['consensus']
    
    print(f"\n🎯 {symbol} AI 합의 분석 결과:")
    print(f"  결정: {consensus['action']}")
    print(f"  신뢰도: {consensus['confidence']:.1%}")
    
    print(f"  주요 이유:")
    for reason in consensus['reasons']:
        print(f"    • {reason}")
    
    return consensus

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AI 합의 시스템')
    parser.add_argument('--test', action='store_true', help='테스트 실행')
    parser.add_argument('--analyze', nargs=5, help='빠른 분석 (종목 가격 단기MA 장기MA RSI)')
    
    args = parser.parse_args()
    
    if args.test:
        test_simple_consensus()
    elif args.analyze:
        symbol = args.analyze[0]
        price = float(args.analyze[1])
        ma_short = float(args.analyze[2])
        ma_long = float(args.analyze[3])
        rsi = float(args.analyze[4])
        
        quick_analysis(symbol, price, ma_short, ma_long, rsi)
    else:
        print("사용법:")
        print("  python ai_consensus_simple.py --test")
        print("  python ai_consensus_simple.py --analyze 'KRW-BTC' 99500000 102000000 98000000 65.5")
        print("\n예시:")
        print("  python ai_consensus_simple.py --test")
        print("  python ai_consensus_simple.py --analyze '005930.KS' 181200 182000 180000 62.5")