from dataclasses import dataclass
import os
from pathlib import Path


def _parse_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _load_local_env() -> None:
    base = Path(__file__).resolve().parents[1]

    # python-dotenv 사용 가능하면 .env + .env.local 자동 로드
    try:
        from dotenv import load_dotenv
        load_dotenv(dotenv_path=base / ".env")
        load_dotenv(dotenv_path=base / ".env.local")
    except Exception:
        _parse_env_file(base / ".env")
        _parse_env_file(base / ".env.local")


_load_local_env()


@dataclass
class Settings:
    def __init__(self):
        # 환경변수에서 설정값 로드
        self._reload()
    
    def _reload(self):
        """환경변수에서 설정값을 다시 로드합니다."""
        self.database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/stock_trader")
        self.min_map_confidence: float = float(os.getenv("MIN_MAP_CONFIDENCE", "0.92"))
        self.risk_penalty_cap: float = float(os.getenv("RISK_PENALTY_CAP", "30"))
        self.telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", os.getenv("TelegramBotToken", ""))
        self.telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", os.getenv("TelegramChatId", ""))

        # 브로커 선택: paper | kis
        self.broker: str = os.getenv("BROKER", "paper").lower()

        # KIS (한국투자증권) 연동 설정
        self.kis_app_key: str = os.getenv("KIS_APP_KEY", "")
        self.kis_app_secret: str = os.getenv("KIS_APP_SECRET", "")
        self.kis_account_no: str = os.getenv("KIS_ACCOUNT_NO", "")
        self.kis_product_code: str = os.getenv("KIS_PRODUCT_CODE", "01")
        self.kis_mode: str = os.getenv("KIS_MODE", "paper")
        self.kis_base_url: str = os.getenv("KIS_BASE_URL", "")

        # Demo behavior
        self.enable_demo_auto_close: bool = os.getenv("ENABLE_DEMO_AUTO_CLOSE", "0").strip().lower() in {"1", "true", "yes", "on"}

        # Scheduler
        self.exit_cycle_interval_sec: int = int(os.getenv("EXIT_CYCLE_INTERVAL_SEC", "60"))

        # Risk limits
        self.risk_max_loss_per_trade: float = float(os.getenv("RISK_MAX_LOSS_PER_TRADE", "30000"))
        self.risk_daily_loss_limit: float = float(os.getenv("RISK_DAILY_LOSS_LIMIT", "100000"))
        self.risk_max_exposure_per_symbol: float = float(os.getenv("RISK_MAX_EXPOSURE_PER_SYMBOL", "300000"))
        self.risk_max_concurrent_positions: int = int(os.getenv("RISK_MAX_CONCURRENT_POSITIONS", "3"))
        self.risk_loss_streak_cooldown: int = int(os.getenv("RISK_LOSS_STREAK_COOLDOWN", "3"))
        self.risk_cooldown_minutes: int = int(os.getenv("RISK_COOLDOWN_MINUTES", "60"))
        self.risk_assumed_stop_loss_pct: float = float(os.getenv("RISK_ASSUMED_STOP_LOSS_PCT", "0.015"))
        self.risk_target_position_value: float = float(os.getenv("RISK_TARGET_POSITION_VALUE", "100000"))

        # News ingestion
        self.news_mode: str = os.getenv("NEWS_MODE", "sample").lower()  # sample | rss
        self.news_rss_url: str = os.getenv("NEWS_RSS_URL", "https://www.mk.co.kr/rss/30000001/")
    
    def reload(self):
        """설정을 다시 로드합니다 (런타임 환경변수 변경 시 호출)."""
        self._reload()


# 싱글턴 인스턴스 생성
_settings_instance = None

def get_settings() -> Settings:
    """Settings 싱글턴 인스턴스를 반환합니다."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

# 하위 호환성을 위한 별칭
settings = get_settings()
