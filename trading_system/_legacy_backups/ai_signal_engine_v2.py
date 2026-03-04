#!/usr/bin/env python3
"""
트레이더 마크 📊 - AI 합의 신호 엔진 V2 (완전 재설계)
진짜 독립적인 5개 전문가 에이전트
"""

import statistics
from datetime import datetime
from typing import Optional, List, Dict


def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """정석 RSI (Wilder's Smoothing)"""
    if len(prices) < period + 1:
        return 50.0
    
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # 첫 period 동안 단순 평균
    initial_gains = [max(c, 0) for c in changes[:period]]
    initial_losses = [abs(min(c, 0)) for c in changes[:period]]
    
    avg_gain = sum(initial_gains) / period
    avg_loss = sum(initial_losses) / period
    
    # 이후 Wilder's Smoothing (EMA 변형)
    for change in changes[period:]:
        gain = max(change, 0)
        loss = abs(min(change, 0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_multiplier: float = 2.0) -> Dict:
    """볼린저 밴드"""
    if len(prices) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "position": 0.5}
    
    recent = prices[-period:]
    middle = statistics.mean(recent)
    std = statistics.stdev(recent) if len(recent) > 1 else 0
    
    upper = middle + (std * std_multiplier)
    lower = middle - (std * std_multiplier)
    
    current = prices[-1]
    position = (current - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
    
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "position": position
    }


class TrendFollower:
    """추세 추종 전문가 - MA 크로스 중심"""
    
    def __init__(self):
        self.name = "TrendFollower"
        self.weight = 1.0
    
    def analyze(self, prices: List[float], **kwargs) -> Dict:
        if len(prices) < 50:
            return self._hold_signal()
        
        # 다양한 MA
        ma5 = statistics.mean(prices[-5:])
        ma10 = statistics.mean(prices[-10:])
        ma20 = statistics.mean(prices[-20:])
        ma50 = statistics.mean(prices[-50:])
        current = prices[-1]
        
        score = 0.0
        
        # 장기 추세 (MA50 기준)
        if current > ma50 * 1.01:  # 1% 이상 위
            score += 0.3
        elif current < ma50 * 0.99:  # 1% 이상 아래
            score -= 0.3
        
        # MA 배열 (골든크로스/데드크로스)
        if ma5 > ma10 > ma20:
            score += 0.4
        elif ma5 < ma10 < ma20:
            score -= 0.4
        
        # 현재가와 MA20 관계
        ma20_diff = (current - ma20) / ma20
        score += max(min(ma20_diff * 5, 0.3), -0.3)
        
        return self._make_signal(score, {
            "ma5": ma5,
            "ma20": ma20,
            "ma50": ma50,
        })
    
    def _make_signal(self, score: float, indicators: Dict) -> Dict:
        confidence = min(abs(score), 1.0)
        
        if score > 0.35:
            signal = "BUY"
        elif score < -0.35:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "agent": self.name,
            "signal": signal,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "weight": self.weight,
            "indicators": indicators
        }
    
    def _hold_signal(self) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 0.0,
            "weight": self.weight,
            "indicators": {}
        }


class MeanReversion:
    """평균 회귀 전문가 - RSI + 볼린저밴드 역발상"""
    
    def __init__(self):
        self.name = "MeanReversion"
        self.weight = 1.0
    
    def analyze(self, prices: List[float], **kwargs) -> Dict:
        if len(prices) < 20:
            return self._hold_signal()
        
        rsi = calculate_rsi(prices, 14)
        bb = calculate_bollinger_bands(prices, 20, 2.0)
        
        score = 0.0
        
        # RSI 역발상 (과매도 = 매수, 과매수 = 매도)
        if rsi < 20:
            score += 0.8
        elif rsi < 30:
            score += 0.5
        elif rsi < 40:
            score += 0.2
        elif rsi > 80:
            score -= 0.8
        elif rsi > 70:
            score -= 0.5
        elif rsi > 60:
            score -= 0.2
        
        # 볼린저밴드 역발상
        bb_pos = bb["position"]
        if bb_pos < 0.1:  # 하단 돌파
            score += 0.5
        elif bb_pos < 0.2:
            score += 0.3
        elif bb_pos > 0.9:  # 상단 돌파
            score -= 0.5
        elif bb_pos > 0.8:
            score -= 0.3
        
        return self._make_signal(score, {
            "rsi": rsi,
            "bb_position": bb_pos,
        })
    
    def _make_signal(self, score: float, indicators: Dict) -> Dict:
        confidence = min(abs(score) * 1.1, 1.0)  # 역발상은 신뢰도 높임
        
        if score > 0.4:
            signal = "BUY"
        elif score < -0.4:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "agent": self.name,
            "signal": signal,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "weight": self.weight,
            "indicators": indicators
        }
    
    def _hold_signal(self) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 0.0,
            "weight": self.weight,
            "indicators": {}
        }


class MomentumScalper:
    """모멘텀 스캘퍼 - 짧은 기간 가격 변화"""
    
    def __init__(self):
        self.name = "MomentumScalper"
        self.weight = 0.9
    
    def analyze(self, prices: List[float], volume_trend: float = 0.0, **kwargs) -> Dict:
        if len(prices) < 10:
            return self._hold_signal()
        
        current = prices[-1]
        
        # 짧은 모멘텀 (3봉, 5봉, 10봉)
        mom_3 = (current - prices[-4]) / prices[-4] if len(prices) >= 4 else 0
        mom_5 = (current - prices[-6]) / prices[-6] if len(prices) >= 6 else 0
        mom_10 = (current - prices[-11]) / prices[-11] if len(prices) >= 11 else 0
        
        score = 0.0
        
        # 짧은 모멘텀 가중
        score += mom_3 * 20  # 최근 3봉이 가장 중요
        score += mom_5 * 15
        score += mom_10 * 10
        
        # 거래량 추세 고려
        score += volume_trend * 0.5
        
        # 연속 상승/하락 체크
        recent_5 = prices[-5:]
        all_rising = all(recent_5[i] > recent_5[i-1] for i in range(1, len(recent_5)))
        all_falling = all(recent_5[i] < recent_5[i-1] for i in range(1, len(recent_5)))
        
        if all_rising:
            score += 0.4
        elif all_falling:
            score -= 0.4
        
        # 범위 제한
        score = max(min(score, 1.0), -1.0)
        
        return self._make_signal(score, {
            "momentum_3": round(mom_3, 4),
            "momentum_5": round(mom_5, 4),
            "momentum_10": round(mom_10, 4),
        })
    
    def _make_signal(self, score: float, indicators: Dict) -> Dict:
        confidence = min(abs(score) * 0.9, 1.0)  # 모멘텀은 노이즈 많아 신뢰도 낮춤
        
        if score > 0.35:
            signal = "BUY"
        elif score < -0.35:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "agent": self.name,
            "signal": signal,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "weight": self.weight,
            "indicators": indicators
        }
    
    def _hold_signal(self) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 0.0,
            "weight": self.weight,
            "indicators": {}
        }


class VolumeAnalyst:
    """거래량 전문가 - OBV 개념"""
    
    def __init__(self):
        self.name = "VolumeAnalyst"
        self.weight = 0.8
    
    def analyze(self, prices: List[float], volume_trend: float = 0.0, volatility: float = 0.0, **kwargs) -> Dict:
        if len(prices) < 5:
            return self._hold_signal()
        
        # 가격 변화
        price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
        
        score = 0.0
        
        # 가격 상승 + 거래량 증가 = 강세
        if price_change > 0.01 and volume_trend > 0.2:
            score += 0.6
        elif price_change > 0.005 and volume_trend > 0.1:
            score += 0.3
        
        # 가격 하락 + 거래량 증가 = 약세
        if price_change < -0.01 and volume_trend > 0.2:
            score -= 0.6
        elif price_change < -0.005 and volume_trend > 0.1:
            score -= 0.3
        
        # 높은 변동성 = 위험 신호
        if volatility > 0.05:
            score -= 0.3
        elif volatility > 0.03:
            score -= 0.15
        
        # 거래량 추세만으로도 판단
        score += volume_trend * 0.5
        
        return self._make_signal(score, {
            "volume_trend": round(volume_trend, 3),
            "volatility": round(volatility, 4),
            "price_change": round(price_change, 4),
        })
    
    def _make_signal(self, score: float, indicators: Dict) -> Dict:
        confidence = min(abs(score) * 0.7, 1.0)  # 거래량은 보조 지표
        
        if score > 0.25:
            signal = "BUY"
        elif score < -0.25:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "agent": self.name,
            "signal": signal,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "weight": self.weight,
            "indicators": indicators
        }
    
    def _hold_signal(self) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 0.0,
            "weight": self.weight,
            "indicators": {}
        }


class RiskController:
    """리스크 컨트롤러 - 극도로 보수적"""
    
    def __init__(self):
        self.name = "RiskController"
        self.weight = 1.5  # 가장 높은 가중치
    
    def analyze(self, prices: List[float], volatility: float = 0.0, **kwargs) -> Dict:
        if len(prices) < 20:
            return self._hold_signal()
        
        current = prices[-1]
        ma20 = statistics.mean(prices[-20:])
        
        score = 0.0
        
        # 기본적으로 HOLD 선호
        score -= 0.2
        
        # 높은 변동성 = 거래 금지
        if volatility > 0.08:
            score -= 0.6
        elif volatility > 0.05:
            score -= 0.4
        elif volatility > 0.03:
            score -= 0.2
        
        # MA20 대비 과도한 이탈 = 위험
        ma_diff = abs((current - ma20) / ma20)
        if ma_diff > 0.05:
            score -= 0.4
        elif ma_diff > 0.03:
            score -= 0.2
        
        # 급격한 최근 변화 = 위험
        if len(prices) >= 3:
            recent_change = abs((prices[-1] - prices[-3]) / prices[-3])
            if recent_change > 0.03:
                score -= 0.3
        
        # 안정적인 상승만 승인
        if len(prices) >= 10:
            recent = prices[-10:]
            rising_count = sum(1 for i in range(1, len(recent)) if recent[i] > recent[i-1])
            
            if rising_count >= 8 and volatility < 0.02:  # 매우 안정적
                score += 0.5
            elif rising_count >= 7 and volatility < 0.03:
                score += 0.3
            elif rising_count <= 2 and volatility < 0.02:
                score -= 0.5
            elif rising_count <= 3 and volatility < 0.03:
                score -= 0.3
        
        return self._make_signal(score, {
            "volatility": round(volatility, 4),
            "ma_diff": round(ma_diff, 4),
        })
    
    def _make_signal(self, score: float, indicators: Dict) -> Dict:
        confidence = min(abs(score), 1.0)
        
        # 매우 높은 임계값 (보수적)
        if score > 0.45:
            signal = "BUY"
        elif score < -0.45:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return {
            "agent": self.name,
            "signal": signal,
            "score": round(score, 3),
            "confidence": round(confidence, 3),
            "weight": self.weight,
            "indicators": indicators
        }
    
    def _hold_signal(self) -> Dict:
        return {
            "agent": self.name,
            "signal": "HOLD",
            "score": 0.0,
            "confidence": 1.0,  # HOLD는 항상 확신
            "weight": self.weight,
            "indicators": {}
        }


class AISignalEngine:
    """
    5개 진짜 독립적인 전문가 시스템
    - TrendFollower: 추세 추종 (MA 크로스)
    - MeanReversion: 평균 회귀 (RSI + BB 역발상)
    - MomentumScalper: 모멘텀 스캘핑 (짧은 기간)
    - VolumeAnalyst: 거래량 분석 (OBV 개념)
    - RiskController: 리스크 관리 (HOLD 편향, 가중치 1.5×)
    """
    
    def __init__(self):
        self.agents = [
            TrendFollower(),
            MeanReversion(),
            MomentumScalper(),
            VolumeAnalyst(),
            RiskController(),
        ]
        self.history: List[Dict] = []
    
    def decide(self, symbol: str, prices: List[float], volatility: float,
               volume_trend: float = 0.0, strategy: str = "MODERATE") -> Dict:
        """전문가 합의 → 최종 신호"""
        
        if strategy == "EMERGENCY_STOP":
            return self._emergency_signal(symbol)
        
        # 최소 신뢰도 (더욱 상향)
        min_conf = {
            "AGGRESSIVE": 0.75,
            "MODERATE": 0.80,
            "CONSERVATIVE": 0.85
        }.get(strategy, 0.80)
        
        # 각 에이전트 분석
        results = []
        for agent in self.agents:
            result = agent.analyze(
                prices=prices,
                volatility=volatility,
                volume_trend=volume_trend
            )
            results.append(result)
        
        # 가중 투표
        weighted_scores = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}
        total_weight = sum(agent.weight for agent in self.agents)
        
        for result in results:
            sig = result["signal"]
            weight = result["weight"]
            conf = result["confidence"]
            weighted_scores[sig] += weight * conf
        
        # 정규화
        total = sum(weighted_scores.values())
        if total > 0:
            vote_pct = {k: v / total for k, v in weighted_scores.items()}
        else:
            vote_pct = {"BUY": 0.0, "SELL": 0.0, "HOLD": 1.0}
        
        # 최종 결정
        best_signal = max(vote_pct, key=vote_pct.get)
        best_conf = vote_pct[best_signal]
        
        # 강한 합의 (85% 이상)
        unanimous = best_conf >= 0.85
        
        # 신뢰도 기준 미달 시 HOLD
        if best_conf < min_conf:
            final_signal = "HOLD"
            final_conf = best_conf
            reason = f"신뢰도 {best_conf:.0%} < 기준 {min_conf:.0%}"
        else:
            final_signal = best_signal
            final_conf = best_conf
            reason = self._build_reason(results, final_signal)
        
        decision = {
            "symbol": symbol,
            "signal": final_signal,
            "confidence": round(final_conf, 3),
            "reason": reason,
            "unanimous": unanimous,
            "votes": {k: round(v, 3) for k, v in vote_pct.items()},
            "agents": results,
            "strategy": strategy,
            "min_conf": min_conf,
            "timestamp": datetime.now(),
        }
        
        self.history.append(decision)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        return decision
    
    def _build_reason(self, results: List[Dict], signal: str) -> str:
        """이유 구성"""
        supporters = [r for r in results if r["signal"] == signal]
        
        if not supporters:
            return "합의 없음"
        
        # 가장 확신하는 에이전트
        top = max(supporters, key=lambda r: r["confidence"])
        
        parts = [f"{top['agent']}({top['confidence']:.0%})"]
        
        # 주요 지표
        if "indicators" in top and top["indicators"]:
            ind = top["indicators"]
            if "rsi" in ind:
                parts.append(f"RSI {ind['rsi']:.1f}")
            if "momentum_3" in ind:
                parts.append(f"Mom {ind['momentum_3']:.2%}")
        
        return " | ".join(parts)
    
    def _emergency_signal(self, symbol: str) -> Dict:
        return {
            "symbol": symbol,
            "signal": "HOLD",
            "confidence": 0.0,
            "reason": "긴급 정지",
            "unanimous": False,
            "votes": {"BUY": 0.0, "SELL": 0.0, "HOLD": 1.0},
            "agents": [],
            "timestamp": datetime.now(),
        }
    
    def format_decision(self, d: Dict) -> str:
        """결정 포맷"""
        ts = d["timestamp"].strftime("%H:%M:%S")
        conf = d["confidence"]
        sig = d["signal"]
        icon = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}.get(sig, "⚪")
        
        lines = [
            f"[{ts}] {icon} {d['symbol']} → {sig} ({conf:.0%})",
            f"         이유: {d['reason']}",
            f"         투표: BUY {d['votes'].get('BUY',0):.0%} | "
            f"SELL {d['votes'].get('SELL',0):.0%} | "
            f"HOLD {d['votes'].get('HOLD',0):.0%}",
            f"         전략: {d.get('strategy','?')} | "
            f"강한합의: {'✅' if d['unanimous'] else '❌'}",
        ]
        return "\n".join(lines)
