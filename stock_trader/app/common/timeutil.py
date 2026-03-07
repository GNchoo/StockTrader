from datetime import datetime, timezone, timedelta, date, time as _time


# 한국 표준시(KST) 오프셋
KST = timezone(timedelta(hours=9))

# 정규장 시간
MARKET_OPEN = _time(9, 0)
MARKET_CLOSE = _time(15, 30)

# 한국 공휴일 (2025~2027, 음력 공휴일 포함)
# 매년 12월경 다음 해 공휴일을 추가할 것
_KR_HOLIDAYS: set[date] = {
    # ── 2025 ──
    date(2025, 1, 1),   # 신정
    date(2025, 1, 28),  # 설날 연휴
    date(2025, 1, 29),  # 설날
    date(2025, 1, 30),  # 설날 연휴
    date(2025, 3, 1),   # 삼일절
    date(2025, 3, 3),   # 삼일절 대체공휴일
    date(2025, 5, 5),   # 어린이날
    date(2025, 5, 5),   # 석가탄신일(5/5 음력4/8 겹침)
    date(2025, 5, 6),   # 대체공휴일
    date(2025, 6, 6),   # 현충일
    date(2025, 8, 15),  # 광복절
    date(2025, 10, 3),  # 개천절
    date(2025, 10, 5),  # 추석 연휴
    date(2025, 10, 6),  # 추석
    date(2025, 10, 7),  # 추석 연휴
    date(2025, 10, 8),  # 추석 대체공휴일
    date(2025, 10, 9),  # 한글날
    date(2025, 12, 25), # 성탄절

    # ── 2026 ──
    date(2026, 1, 1),   # 신정
    date(2026, 2, 16),  # 설날 연휴
    date(2026, 2, 17),  # 설날
    date(2026, 2, 18),  # 설날 연휴
    date(2026, 3, 1),   # 삼일절 (일요일)
    date(2026, 3, 2),   # 삼일절 대체공휴일
    date(2026, 5, 5),   # 어린이날
    date(2026, 5, 24),  # 석가탄신일 (일요일)
    date(2026, 5, 25),  # 석가탄신일 대체공휴일
    date(2026, 6, 6),   # 현충일 (토요일)
    date(2026, 8, 15),  # 광복절 (토요일)
    date(2026, 9, 24),  # 추석 연휴
    date(2026, 9, 25),  # 추석
    date(2026, 9, 26),  # 추석 연휴
    date(2026, 10, 3),  # 개천절 (토요일)
    date(2026, 10, 5),  # 개천절 대체공휴일
    date(2026, 10, 9),  # 한글날
    date(2026, 12, 25), # 성탄절

    # ── 2027 ──
    date(2027, 1, 1),   # 신정
    date(2027, 2, 6),   # 설날 연휴 (토요일)
    date(2027, 2, 7),   # 설날 (일요일)
    date(2027, 2, 8),   # 설날 연휴
    date(2027, 2, 9),   # 설날 대체공휴일
    date(2027, 3, 1),   # 삼일절
    date(2027, 5, 5),   # 어린이날
    date(2027, 5, 13),  # 석가탄신일
    date(2027, 6, 6),   # 현충일 (일요일)
    date(2027, 6, 7),   # 현충일 대체공휴일
    date(2027, 8, 15),  # 광복절 (일요일)
    date(2027, 8, 16),  # 광복절 대체공휴일
    date(2027, 10, 3),  # 개천절 (일요일)
    date(2027, 10, 4),  # 개천절 대체공휴일
    date(2027, 10, 9),  # 한글날 (토요일)
    date(2027, 10, 11), # 한글날 대체공휴일
    date(2027, 10, 14), # 추석 연휴
    date(2027, 10, 15), # 추석
    date(2027, 10, 16), # 추석 연휴
    date(2027, 12, 25), # 성탄절 (토요일)
}


def is_kr_holiday(d: date) -> bool:
    """한국 공휴일 여부를 반환합니다."""
    return d in _KR_HOLIDAYS


def parse_utc_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    s = str(ts).strip()
    if not s:
        return None

    dt = None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        pass

    if dt is None:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except Exception:
                continue

    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_market_open(now: datetime | None = None) -> bool:
    """한국 주식시장(KOSPI/KOSDAQ) 정규장 시간인지 확인.

    정규장: 월~금 09:00~15:30 KST (공휴일 제외)
    """
    kst_now = (now or datetime.now(KST)).astimezone(KST)
    # 토·일 제외
    if kst_now.weekday() >= 5:
        return False
    # 공휴일 제외
    if is_kr_holiday(kst_now.date()):
        return False
    t = kst_now.time()
    return MARKET_OPEN <= t <= MARKET_CLOSE


def minutes_until_market_close(now: datetime | None = None) -> float | None:
    """장 마감까지 남은 분을 반환. 장 외 시간이면 None."""
    if not is_market_open(now):
        return None
    kst_now = (now or datetime.now(KST)).astimezone(KST)
    close_dt = kst_now.replace(hour=15, minute=30, second=0, microsecond=0)
    return max(0.0, (close_dt - kst_now).total_seconds() / 60.0)
