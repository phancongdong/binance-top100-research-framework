"""SOURCE COPY WITH PRIVATE FIBONACCI MATERIAL REMOVED.

This is a selectively redacted copy of the supplied original script, not a new
demo implementation. Non-Fibonacci operational code and project imports remain.
Private route data, selection files/hashes, associated strategy construction and
frozen route assertions were removed. Empty named containers preserve references;
they contain no private Fibonacci parameters or instrument selections.

The remaining strategies and operational code are intentionally retained at the
owner's request. This file still depends on the original private project modules.
It is for code review, not a runnable/deployable release. The new guard below
stops import/execution before project initialization or any external activity.
"""
from __future__ import annotations

raise RuntimeError("Review-only source copy: private configuration removed; execution disabled")


import hashlib

import json

import math

import os

import sys

import tempfile

import time

import warnings

from datetime import datetime, timedelta, timezone

from collections import Counter

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

import requests

requests.packages.urllib3.util.connection.HAS_IPV6 = False

def _request_exception_in_chain(
    exc: BaseException,
) -> Optional[requests.RequestException]:
    current: Optional[BaseException] = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, requests.RequestException):
            return current
        current = current.__cause__ or (
            None if current.__suppress_context__ else current.__context__
        )
    return None

def _safe_exception_text(exc: BaseException) -> str:
    """Never expose signed request URLs through transport exceptions."""
    request_exc = _request_exception_in_chain(exc)
    if request_exc is None:
        return str(exc)
    response = getattr(request_exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int) and status_code > 0:
        return f"{type(request_exc).__name__} (HTTP {status_code})"
    return type(request_exc).__name__

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings("ignore")

from core.types import (
    BarSeries, Timeframe, AssetClass, MarketRegime, Direction,
    OrderSide, PositionSide,
)

from core.data.bar import from_numpy, aggregate_aligned, closed_bars_only

from core.backtest.executor import ExecutionSimulator

from core.errors import (
    AuthError,
    MarginError,
    OrderRejectedError,
    RateLimitExchangeError,
    UnsupportedTimeframeError,
)

from core.execution.bingx_executor import BingXExecutor

from core.utils.time import now_utc

from strategies.payid import PAYID

from strategies.smc_mtf import SMCMultiTimeframe

from strategies.examples.pure_breakout import PureBreakout

from strategies.examples.eth_low_vol_breakout import ETHLowVolBreakout

# REDACTED: private strategy import.

from strategies.examples.pure_mean_reversion import PureMeanReversion

from strategies.examples.pure_trend_follow import PureTrendFollow

# REDACTED: removed private strategy material or identifying configuration.
from strategies.examples.vps_recovery_routes import DualMomentumRecovery, RecoveryLowVolBreakout, ResidualBreakoutRecovery, XAUFixedBarrierDualMomentum, XAUFixedBarrierLowVolBreakout

from scripts.smc_mtf_telegram import (
    TelegramReporter,
    send_tg,
    telegram_configured,
)

def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

CRYPTO_WHITELIST_MAP = {
    "BTCUSDT": "BTC-USDT",
    "ETHUSDT": "ETH-USDT",
    "SOLUSDT": "SOL-USDT",
    "RUNEUSDT": "RUNE-USDT",
    "TLMUSDT": "TLM-USDT",
    "FETUSDT": "FET-USDT",
    "INJUSDT": "INJ-USDT",
    "ZECUSDT": "ZEC-USDT",
    "BNBUSDT": "BNB-USDT",
    "DOGEUSDT": "DOGE-USDT",
    "TRXUSDT": "TRX-USDT",
    "SUIUSDT": "SUI-USDT",
    "ADAUSDT": "ADA-USDT",
    "WLDUSDT": "WLD-USDT",
    "TAOUSDT": "TAO-USDT",
    # BingX lists PEPE as a 1,000-token contract. Percentage moves and the
    # REDACTED: private strategy note.
    "PEPEUSDT": "1000PEPE-USDT",
    "SYNUSDT": "SYN-USDT",
    "VANRYUSDT": "VANRY-USDT",
    "HBARUSDT": "HBAR-USDT",
    "DOTUSDT": "DOT-USDT",
    "ONEUSDT": "ONE-USDT",
    "COTIUSDT": "COTI-USDT",
    "1INCHUSDT": "1INCH-USDT",
    "DUSKUSDT": "DUSK-USDT",
    "KAVAUSDT": "KAVA-USDT",
    "ANKRUSDT": "ANKR-USDT",
    "CHRUSDT": "CHR-USDT",
    "CKBUSDT": "CKB-USDT",
    "EGLDUSDT": "EGLD-USDT",
    "GRTUSDT": "GRT-USDT",
    "IOSTUSDT": "IOST-USDT",
    "IOTAUSDT": "IOTA-USDT",
    "JSTUSDT": "JST-USDT",
    "KSMUSDT": "KSM-USDT",
    "LUNAUSDT": "LUNA-USDT",
    "RSRUSDT": "RSR-USDT",
    # BingX lists SHIB perpetuals under the 1,000-token contract.
    "SHIBUSDT": "1000SHIB-USDT",
    "STXUSDT": "STX-USDT",
    "THETAUSDT": "THETA-USDT",
    "YFIUSDT": "YFI-USDT",
    "MEWUSDT": "MEW-USDT",
    # BONK stays the logical symbol. BingX exposes the verified 1,000-token
    # REDACTED: private strategy note.
    "BONKUSDT": "1000BONK-USDT",
    "GALAUSDT": "GALA-USDT",
    "APEUSDT": "APE-USDT",
    "MINAUSDT": "MINA-USDT",
}

CRYPTO_CONTRACT_PROVENANCE: Dict[str, Dict[str, Any]] = {
    "BONKUSDT": {
        "exchange_symbol": "1000BONK-USDT",
        "source_symbol": "1000BONKUSDT",
        "price_multiplier": 1000,
        "base_quantity_multiplier": 1000,
        "effective_utc": "2023-11-23T09:00:00Z",
        "source": "BingX public contract metadata plus frozen overlap proof",
    },
}

UNSUPPORTED_WHITELIST = {
    "XECUSDT": "BingX perpetual contract unavailable at deployment time",
}

REQUIRED_CRYPTO_MAP = dict(CRYPTO_WHITELIST_MAP)

BINGX_FOREX_MAP = {
    "AUDJPY": "NCFXAUD2JPY-USDT",
    "AUDUSD": "NCFXAUD2USD-USDT",
    "CADJPY": "NCFXCAD2JPY-USDT",
    "EURCAD": "NCFXEUR2CAD-USDT",
    "EURCHF": "NCFXEUR2CHF-USDT",
    "EURGBP": "NCFXEUR2GBP-USDT",
    "EURJPY": "NCFXEUR2JPY-USDT",
    "EURSGD": "NCFXEURSGD2USD-USDT",
    "EURUSD": "NCFXEUR2USD-USDT",
    "GBPCHF": "NCFXGBP2CHF-USDT",
    "GBPJPY": "NCFXGBP2JPY-USDT",
    "GBPSGD": "NCFXGBPSGD2USD-USDT",
    "GBPUSD": "NCFXGBP2USD-USDT",
    "NZDCAD": "NCFXNZD2CAD-USDT",
    "NZDUSD": "NCFXNZD2USD-USDT",
    "USDCAD": "NCFXUSD2CAD-USDT",
    "USDCHF": "NCFXUSD2CHF-USDT",
    "USDJPY": "NCFXUSD2JPY-USDT",
    "USDSGD": "NCFXUSDSGD2USD-USDT",
    "USDZAR": "NCFXUSD2ZAR-USDT",
    "USDTRY": "NCFXUSD2TRY-USDT",
    "USDTWD": "NCFXUSD2TWD-USDT",
}

BINGX_COMMODITY_MAP = {
    "XAUUSD": "NCCOGOLD2USD-USDT",
}

SYMBOLS: Dict[str, AssetClass] = {
    **{symbol: AssetClass.FOREX for symbol in BINGX_FOREX_MAP},
    **{symbol: AssetClass.COMMODITY for symbol in BINGX_COMMODITY_MAP},
}

FIXED_SYMBOLS = dict(SYMBOLS)

FIXED_BINGX_MAP = {
    **REQUIRED_CRYPTO_MAP,
    **BINGX_FOREX_MAP,
    **BINGX_COMMODITY_MAP,
}

OPTIONAL_INACTIVE_BINGX_SYMBOLS = frozenset({"VANRYUSDT"})

TERMINAL_LIVE_INTENT_STATUSES = frozenset({"CLOSED", "REJECTED", "FAILED"})

CRYPTO_SYMBOLS: set = set(CRYPTO_WHITELIST_MAP)

FOREX_SYMBOLS = set(BINGX_FOREX_MAP)

COMMODITY_SYMBOLS = set(BINGX_COMMODITY_MAP)

SMC_MTF_MIN_SCORES: Dict[str, int] = {
    "SOLUSDT": 50,
}

SMC_ENTRY_SYMBOLS: Tuple[str, ...] = tuple(SMC_MTF_MIN_SCORES)

SMC_D1_SYMBOLS: Tuple[str, ...] = ("BTCUSDT", "ETHUSDT")

PAYID_D1_MIN_SCORES: Dict[str, int] = {
    "EURUSD": 45,
    "GBPUSD": 40,
}

TF_D1_SYMBOLS: Tuple[str, ...] = ("USDJPY", "XAUUSD")

MR_D1_SYMBOLS: Tuple[str, ...] = ("GBPUSD", "AUDUSD")

BREAKOUT_D1_SYMBOLS: Tuple[str, ...] = ("BTCUSDT",)

LVB_SYMBOLS: Tuple[str, ...] = ("ETHUSDT", "PEPEUSDT")

RECOVERY_LVB_ROUTES: Tuple[Tuple[str, str, Optional[Direction]], ...] = (
    ("ZECUSDT", "CR_LVB_30_LONG", Direction.LONG),
    ("YFIUSDT", "CR_LVB_30_LONG", Direction.LONG),
    ("TAOUSDT", "CR_LVB_30", None),
    ("MEWUSDT", "CR_LVB_30", None),
)

RECOVERY_DUAL_MOMENTUM_SYMBOLS: Tuple[str, ...] = ("COTIUSDT", "VANRYUSDT")

RECOVERY_RESIDUAL_SYMBOLS: Tuple[str, ...] = ("IOTAUSDT", "DOGEUSDT")

# REDACTED: removed private strategy material or identifying configuration.
RECOVERY_DIRECTIONAL_FIB_ROUTES: Tuple[Tuple[str, str, Direction], ...] = ()

RECOVERY_XAU_DM_SYMBOLS: Tuple[str, ...] = ("XAUUSD",)

RECOVERY_XAU_LVB_SYMBOLS: Tuple[str, ...] = ("XAUUSD",)

# REDACTED: removed private strategy material or identifying configuration.
RECOVERY_ROUTE_IDS: frozenset[str] = frozenset({'CR_LVB_30_LONG:ZECUSDT', 'CR_LVB_30_LONG:YFIUSDT', 'CR_LVB_30:TAOUSDT', 'RESIDUAL_BREAKOUT:IOTAUSDT', 'RESIDUAL_BREAKOUT:DOGEUSDT', 'CR_DM_21_63:COTIUSDT', 'CR_DM_21_63:VANRYUSDT', 'CR_LVB_30:MEWUSDT', 'XAU_FIXED_BARRIER_DM:XAUUSD', 'XAU_LVB_60:XAUUSD'})

# REDACTED: removed private strategy material or identifying configuration.
RECOVERY_PROMOTED_ROUTE_IDS: frozenset[str] = RECOVERY_ROUTE_IDS | frozenset({*()})

# REDACTED: removed private strategy material or identifying configuration.
RECOVERY_ENTRY_ACTIVATION_TIME = None

# REDACTED: removed private strategy material or identifying configuration.
RECOVERY_MIGRATION_ROUTES: Dict[str, str] = {'XAU_LVB_60:XAUUSD': 'XAU_FIXED_BARRIER_DM:XAUUSD'}

BINANCE_RESIDUAL_FACTOR_SYMBOLS: Tuple[str, ...] = (
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "ZECUSDT", "XRPUSDT", "BNBUSDT",
    "DOGEUSDT", "MUBUSDT", "NEARUSDT", "TRXUSDT", "DEXEUSDT", "SUIUSDT",
    "ADAUSDT", "WLDUSDT", "TAOUSDT", "LTCUSDT", "AAVEUSDT", "LINKUSDT",
    "OPNUSDT", "PEPEUSDT", "XAUTUSDT", "TREEUSDT", "UNIUSDT", "PUMPUSDT",
    "ZBTUSDT", "PAXGUSDT", "SPCXBUSDT", "TOWNSUSDT", "XLMUSDT", "SYNUSDT",
    "AVAXUSDT", "ENAUSDT", "DODOUSDT", "SXTUSDT", "ALLOUSDT", "KAITOUSDT",
    "XPLUSDT", "SNDKBUSDT", "SKHYBUSDT", "ARBUSDT", "YFIUSDT", "IOTAUSDT",
    "COTIUSDT", "VANRYUSDT", "THETAUSDT", "MEWUSDT", "ONEUSDT",
)

MR_MAX_HOLD_BARS = 15

BREAKOUT_MAX_HOLD_BARS = 30

# REDACTED: removed private strategy material or identifying configuration.
FIBONACCI_ROUTES: Dict[str, Tuple[Timeframe, float, float]] = {}

# REDACTED: removed private strategy material or identifying configuration.
ETH_H1_FIB_ENABLED = False

# REDACTED: removed private strategy material or identifying configuration.
FIBONACCI_EXTRA_ROUTES: Tuple[Tuple[str, Timeframe, float, float], ...] = ()

# REDACTED: removed private strategy material or identifying configuration.
def iter_fibonacci_routes() -> Tuple[Tuple[str, Timeframe, float, float], ...]:
    """REDACTED: private strategy configuration and dependent implementation."""
    return ()

# REDACTED: removed private strategy material or identifying configuration.
FIBONACCI_MULTI_TIMEFRAME_SYMBOLS = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
FIBONACCI_EXPLICIT_TIMEFRAME_ROUTE_SYMBOLS = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
def strategy_route_id(strategy_name: str, symbol: str, timeframe: Optional[Any]=None) -> str:
    route = f'{strategy_name}:{symbol}'
    pass
    return route

def strategy_instance_route_id(
    strategy: Any,
    symbol: str,
    timeframe: Optional[Any] = None,
) -> str:
    override = getattr(strategy, "route_id_override", None)
    if override:
        return str(override)
    return strategy_route_id(str(strategy.name), symbol, timeframe)

WHITELIST_SYMBOLS = frozenset(
    set(SMC_ENTRY_SYMBOLS)
    | set(SMC_D1_SYMBOLS)
    | set(PAYID_D1_MIN_SCORES)
    | set(TF_D1_SYMBOLS)
    | set(MR_D1_SYMBOLS)
    | set(BREAKOUT_D1_SYMBOLS)
    | set(LVB_SYMBOLS)
    | {symbol for symbol, _, _, _ in iter_fibonacci_routes()}
)

def _unique_symbols(*groups: Tuple[str, ...]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(symbol for group in groups for symbol in group))

def default_crypto_strategy_symbols() -> Tuple[str, ...]:
    """Dynamic default routing was removed; every crypto route is explicit."""
    return ()

def current_smc_entry_symbols() -> Tuple[str, ...]:
    return SMC_ENTRY_SYMBOLS

def current_tf_d1_symbols() -> Tuple[str, ...]:
    return TF_D1_SYMBOLS

# REDACTED: removed private strategy material or identifying configuration.
def current_allowed_routes() -> frozenset[str]:
    return frozenset({f'SMC_MTF_V2:{symbol}' for symbol in current_smc_entry_symbols()} | {f'SMC_MTF_V2:{symbol}' for symbol in SMC_D1_SYMBOLS} | {f'PAYID_V2:{symbol}' for symbol in PAYID_D1_MIN_SCORES} | {f'PURE_TREND_FOLLOW:{symbol}' for symbol in current_tf_d1_symbols()} | {f'PURE_MEAN_REVERSION:{symbol}' for symbol in MR_D1_SYMBOLS} | {f'PURE_BREAKOUT:{symbol}' for symbol in BREAKOUT_D1_SYMBOLS} | {f'CR_LVB_30:{symbol}' for symbol in LVB_SYMBOLS} | set(RECOVERY_ROUTE_IDS) | set())

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_SELECTION_PATH = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_SELECTION_FILE_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_SELECTION_DIGEST_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_SELECTION_FILE_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_SELECTION_DIGEST_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_REPORT_VI_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_SOURCE_VERDICTS_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_SOURCE_MANIFEST_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
CRYPTO4WATCH_SOURCE_MANIFEST_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
CRYPTO4WATCH_INPUT_MANIFEST_SHA256 = ''

# REDACTED: removed private strategy material or identifying configuration.
CRYPTO4WATCH_SOURCE_ARTIFACT_SHA256: Dict[str, str] = ''

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_ENTRY_ACTIVATION_TIME = None

# REDACTED: removed private strategy material or identifying configuration.
CRYPTO4WATCH_ENTRY_ACTIVATION_TIME = None

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_TIMEFRAMES: Dict[str, Timeframe] = {}

# REDACTED: removed private strategy material or identifying configuration.
def _exact58_fibonacci_parameters(config_id: str) -> Tuple[int, float, float]:
    """REDACTED: private strategy configuration and dependent implementation."""
    raise RuntimeError('Private configuration removed from this review copy')

# REDACTED: removed private strategy material or identifying configuration.
def _load_exact62_selection() -> Tuple[Dict[str, Any], ...]:
    """REDACTED: private strategy configuration and dependent implementation."""
    return ()

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_SELECTION: Tuple[Dict[str, Any], ...] = {}

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_ROUTE_IDS: frozenset[str] = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
EXACT62_SELECTION_BY_ROUTE: Dict[str, Dict[str, Any]] = {}

# REDACTED: removed private strategy material or identifying configuration.
CRYPTO4WATCH_ROUTE_IDS: frozenset[str] = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
EXACT58_ROUTE_IDS: frozenset[str] = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
SINGLE_ENTRY_PATH_PREFERRED_ROUTES: Dict[str, str] = {'COTIUSDT__BOTH__H4': 'CR_DM_21_63:COTIUSDT', 'DOGEUSDT__BOTH__H4': 'RESIDUAL_BREAKOUT:DOGEUSDT', 'ETHUSDT__BOTH__H8': 'CR_LVB_30:ETHUSDT', 'IOTAUSDT__BOTH__H4': 'RESIDUAL_BREAKOUT:IOTAUSDT', 'MEWUSDT__BOTH__D1': 'CR_LVB_30:MEWUSDT', 'TAOUSDT__BOTH__H4': 'CR_LVB_30:TAOUSDT', 'XAUUSD__BOTH__H1': 'XAU_LVB_60:XAUUSD'}

# REDACTED: removed private strategy material or identifying configuration.
FIBONACCI_ENTRY_ROUTES: frozenset[str] = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
FULL_SAMPLE_NEGATIVE_FIBONACCI_ENTRY_ROUTES: frozenset[str] = frozenset()

# REDACTED: removed private strategy material or identifying configuration.
LEGACY_RECOVERY_FIBONACCI_MANAGEMENT_ROUTES: frozenset[str] = frozenset()

LVB_ENTRY_ROUTES: frozenset[str] = frozenset(
    f"CR_LVB_30:{symbol}" for symbol in LVB_SYMBOLS
)

# REDACTED: removed private strategy material or identifying configuration.
OPERATOR_PAUSED_ENTRY_ROUTES: frozenset[str] = frozenset({'CR_DM_21_63:VANRYUSDT'})

REPLACED_RECOVERY_ENTRY_ROUTES: frozenset[str] = frozenset({
    "XAU_FIXED_BARRIER_DM:XAUUSD",
})

OPERATOR_EXCLUDED_ENTRY_SYMBOLS: frozenset[str] = frozenset({
    "VANRYUSDT",
    "USDTRY",
})

# REDACTED: removed private strategy material or identifying configuration.
OPERATOR_EXCLUDED_ENTRY_ROUTES: frozenset[str] = frozenset({'CR_DM_21_63:VANRYUSDT'})

LIVE_ENTRY_ROUTES: frozenset[str] = (
    EXACT62_ROUTE_IDS - OPERATOR_EXCLUDED_ENTRY_ROUTES
)

LIVE_APPROVED_ROUTES: frozenset[str] = current_allowed_routes()

LIVE_ENTRY_DISABLED_ROUTES: frozenset[str] = (
    LIVE_APPROVED_ROUTES - LIVE_ENTRY_ROUTES
)

YAHOO_MAP = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "EURCHF": "EURCHF=X",
    "GBPSGD": "GBPSGD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "USDTRY": "TRY=X",
    "USDTWD": "TWD=X",
}

BINGX_MAP: Dict[str, str] = dict(FIXED_BINGX_MAP)

SYMBOLS.update({symbol: AssetClass.CRYPTO for symbol in REQUIRED_CRYPTO_MAP})

STABLECOINS = {"USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDD", "USDE", "PYUSD", "USD1", "USD"}

def fetch_top50_crypto(force: bool = False) -> list:
    """Load the frozen crypto whitelist without expanding the scan universe."""
    del force  # Retained for compatibility with the previous refresh API.
    BINGX_MAP.update(CRYPTO_WHITELIST_MAP)
    CRYPTO_SYMBOLS.clear()
    CRYPTO_SYMBOLS.update(CRYPTO_WHITELIST_MAP)
    for symbol in CRYPTO_WHITELIST_MAP:
        SYMBOLS[symbol] = AssetClass.CRYPTO
    bases = [symbol[:-4] for symbol in CRYPTO_WHITELIST_MAP]
    print(f"  Crypto whitelist loaded: {len(bases)} supported symbols")
    return bases

HTF_TF = Timeframe.H4

LTF_TF = Timeframe.H1

D1_TF = Timeframe.D1

LEGACY_SMC_TF = Timeframe.M15

# REDACTED: removed private strategy material or identifying configuration.
YAHOO_D1_SIGNAL_ROUTES = frozenset({'PURE_TREND_FOLLOW:USDJPY', 'PURE_TREND_FOLLOW:XAUUSD'})

CAPITAL = 1_000_000

RISK_PER_TRADE = 0.005

POSITION_MODES = ("capped-symbol", "unlimited-route")

POSITION_MODE = os.getenv("AITRADE_POSITION_MODE", "capped-symbol").strip().lower()

if POSITION_MODE not in POSITION_MODES:
    raise RuntimeError(
        f"AITRADE_POSITION_MODE must be one of {', '.join(POSITION_MODES)}"
    )

MAX_POSITIONS = 6

MAX_CRYPTO_POSITIONS = 3

MAX_FOREX_GOLD_POSITIONS = 3

MAX_SMC_POSITIONS = 4

SL_ATR_MULT = 1.5

TP_ATR_MULT = 3.0

MIN_SCORE = 50

SMC_MAX_HOLD_BARS = 72

SMC_CONFIRMATION_MODE = "either"

SMC_TRAILING_ENABLED = True

SMC_TRAIL_ACTIVATION_R = 1.5

SMC_TRAIL_DISTANCE_R = 0.5

MIN_STOP_ATR = 0.50

MAX_CRYPTO_LEVERAGE = 3.0

RECALCULATE_FILL_RISK = True

LIVE_SLIPPAGE_BUFFER_BPS = 10.0

ENTRY_ENABLED = _env_bool("AITRADE_ENTRY_ENABLED", False)

VERBOSE_SCAN = _env_bool("AITRADE_VERBOSE_SCAN", False)

LIVE_RISK_FRACTION = 0.007

LIVE_MARGIN_UTILIZATION = 0.95

LIVE_FILL_RISK_TOLERANCE = 1.02

LIVE_MINIMUM_ORDER_RISK_OVERRIDE = True

# REDACTED: removed private strategy material or identifying configuration.
LIVE_CLIENT_ORDER_PREFIX = 'REDACTED'

LTF_ANALYSIS_DAYS = 7

HTF_ANALYSIS_DAYS = 60

PAPER_REPLAY_DAYS = 7

D1_ANALYSIS_DAYS = 730

D1_REPLAY_DAYS = 365

# REDACTED: removed private strategy material or identifying configuration.
STRATEGY_PRIORITY = {'SMC_MTF_V2': 6, 'PAYID_V2': 5, 'PURE_TREND_FOLLOW': 5, 'CR_LVB_30': 4, 'CR_LVB_30_LONG': 4, 'CR_DM_21_63': 4, 'RESIDUAL_BREAKOUT': 4, 'XAU_FIXED_BARRIER_DM': 4, 'XAU_LVB_60': 4, 'PURE_MEAN_REVERSION': 3, 'PURE_BREAKOUT': 2}

# REDACTED: removed private strategy material or identifying configuration.
ROUTE_PRIORITY = {'SMC_MTF_V2:BTCUSDT': 10, 'SMC_MTF_V2:ETHUSDT': 10, 'PAYID_V2:GBPUSD': 10, 'PURE_TREND_FOLLOW:USDJPY': 10, 'PURE_TREND_FOLLOW:XAUUSD': 10, 'CR_LVB_30:ETHUSDT': 7, 'CR_LVB_30:PEPEUSDT': 7}

live_executor: Optional[BingXExecutor] = None

external_reservations: Dict[str, dict] = {}

_live_leverage_profiles: Dict[Tuple[str, str], dict] = {}

def scan_trace(message: str) -> None:
    """Print detailed cycle progress without changing scanner decisions."""
    if VERBOSE_SCAN:
        print(f"  [SCAN] {message}")

def signal_route(signal: dict) -> Optional[str]:
    explicit = signal.get("route_id") or signal.get("route_id_override")
    if explicit:
        return str(explicit)
    strategy_name = signal.get("strategy_name")
    symbol = signal.get("symbol")
    if not strategy_name or not symbol:
        return None
    return strategy_route_id(
        str(strategy_name),
        str(symbol),
        signal.get("timeframe"),
    )

def signal_selection_path(signal: dict) -> Optional[str]:
    route = signal_route(signal)
    selected = EXACT62_SELECTION_BY_ROUTE.get(str(route))
    return str(selected["path_id"]) if selected is not None else None

def single_entry_path(signal: dict) -> Optional[str]:
    path_id = signal_selection_path(signal)
    return path_id if path_id in SINGLE_ENTRY_PATH_PREFERRED_ROUTES else None

def unlimited_route_mode() -> bool:
    return POSITION_MODE == "unlimited-route"

def state_key_for_signal(signal: dict) -> str:
    route = signal_route(signal)
    if unlimited_route_mode() and route is not None:
        return route
    return str(signal.get("symbol", route or "UNKNOWN"))

def state_key_for_position(position: dict, fallback: str = "") -> str:
    route = position.get("route_id")
    if not route:
        route = strategy_route_id(
            str(position.get("strategy_name", "SMC_MTF_V2")),
            str(position.get("symbol", fallback)),
            position.get("timeframe"),
        )
    if unlimited_route_mode() and route:
        return str(route)
    return str(position.get("symbol", fallback or route))

def position_route(position: dict) -> str:
    return state_key_for_position(position, str(position.get("symbol", "")))

def live_risk_budget(equity: float) -> float:
    """Risk a fixed fraction of current BingX equity on every live route."""
    try:
        value = float(equity)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, value) * LIVE_RISK_FRACTION if math.isfinite(value) else 0.0

def live_fill_risk_limit(plan: dict) -> float:
    approved_risk = (
        plan["planned_risk"]
        if plan.get("minimum_override")
        else plan["risk_budget"]
    )
    return float(approved_risk) * LIVE_FILL_RISK_TOLERANCE

def route_is_allowed(signal: dict) -> bool:
    route = signal_route(signal)
    return route is None or route in current_allowed_routes()

def route_is_live_approved(signal: dict) -> bool:
    route = signal_route(signal)
    return route is not None and route in LIVE_APPROVED_ROUTES

def route_is_entry_enabled(signal: dict) -> bool:
    route = signal_route(signal)
    return route is None or route not in LIVE_ENTRY_DISABLED_ROUTES

# REDACTED: removed private strategy material or identifying configuration.
def recovery_migration_block(signal: dict) -> Optional[str]:
    """REDACTED: private strategy reference removed."""
    route = signal_route(signal)
    if route in EXACT62_ROUTE_IDS:
        return None
    legacy_route = RECOVERY_MIGRATION_ROUTES.get(str(route))
    if legacy_route is None:
        return None
    legacy = state.positions.get(legacy_route)
    if isinstance(legacy, dict) and legacy.get('status') == 'OPEN':
        return f'MIGRATION_WAIT:{legacy_route}'
    return None

# REDACTED: removed private strategy material or identifying configuration.
UPDATED_ROUTE_ENTRY_ACTIVATION_TIME = None

# REDACTED: removed private strategy material or identifying configuration.
UPDATED_ROUTE_ENTRY_ACTIVATION_TIMES: Dict[str, datetime] = {'XAU_LVB_60:XAUUSD': UPDATED_ROUTE_ENTRY_ACTIVATION_TIME}

def recovery_activation_block(signal: dict) -> Optional[str]:
    """Never catch up a promoted or newly updated pre-activation signal."""
    route = signal_route(signal)
    if route in CRYPTO4WATCH_ROUTE_IDS:
        activation_time = CRYPTO4WATCH_ENTRY_ACTIVATION_TIME
    elif route in EXACT58_ROUTE_IDS:
        activation_time = EXACT58_ENTRY_ACTIVATION_TIME
    else:
        activation_time = UPDATED_ROUTE_ENTRY_ACTIVATION_TIMES.get(str(route))
    if activation_time is None and route in RECOVERY_PROMOTED_ROUTE_IDS:
        activation_time = RECOVERY_ENTRY_ACTIVATION_TIME
    if activation_time is None:
        return None
    decision_time = signal.get("decision_time", signal.get("signal_time"))
    parsed = AutoTradeState._parse_datetime(decision_time)
    if parsed is None or parsed < activation_time:
        return "RECOVERY_PRE_ACTIVATION"
    return None

def entry_max_hold(signal: dict, default: int = 24) -> int:
    strategy_name = signal.get("strategy_name")
    if strategy_name == "PURE_MEAN_REVERSION":
        return MR_MAX_HOLD_BARS
    if strategy_name == "PURE_BREAKOUT":
        return BREAKOUT_MAX_HOLD_BARS
    return int(signal.get("max_hold", default))

def mark_signal_already_processed(signal: dict) -> dict:
    """Keep a setup visible in reports without presenting it as actionable."""
    result = dict(signal)
    result["already_processed"] = True
    result["trade_eligible"] = False
    result["effective_score"] = 0.0
    result["blocked_by"] = "ALREADY_PROCESSED"
    return result

def mark_signal_entry_disabled(signal: dict) -> dict:
    """Keep disabled-route setups visible while preventing new positions."""
    result = dict(signal)
    result["preview_only"] = True
    result["below_threshold"] = True
    result["trade_eligible"] = False
    result["effective_score"] = 0.0
    result["blocked_by"] = "ROUTE_ENTRY_DISABLED"
    return result

def mark_signal_migration_blocked(signal: dict, reason: str) -> dict:
    """Report a fresh replacement signal without allowing a second route leg."""
    result = dict(signal)
    result["preview_only"] = True
    result["below_threshold"] = True
    result["trade_eligible"] = False
    result["effective_score"] = 0.0
    result["blocked_by"] = reason
    return result

def signal_atr(signal: dict) -> float:
    """Return explicit ATR, with a safe migration path for queued D1 signals."""
    try:
        atr = float(signal.get("atr", 0.0))
    except (TypeError, ValueError):
        atr = 0.0
    if np.isfinite(atr) and atr > 0:
        return atr

    # Legacy queued signals may not persist ATR. Fixed-ATR strategies can
    # recover it exactly from their stop distance.
    stop_multipliers = {
        "PRICE_ACTION_BASIC": 1.5,
        "PURE_TREND_FOLLOW": 2.0,
        "PAYID_V2": 1.5,
        "PURE_MEAN_REVERSION": 1.5,
        "PURE_BREAKOUT": 1.5,
    }
    multiplier = stop_multipliers.get(signal.get("strategy_name"))
    if multiplier is None:
        return 0.0
    try:
        signal_price = float(signal["current_price"])
        stop_loss = float(signal["sl"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    recovered = abs(signal_price - stop_loss) / multiplier
    return recovered if np.isfinite(recovered) and recovered > 0 else 0.0

def ensure_state_symbol_mappings() -> None:
    """Keep legacy open/pending crypto positions manageable after whitelisting."""
    tracked_symbols = {
        str(record.get("symbol", key))
        for key, record in (
            list(state.positions.items()) + list(state.pending_signals.items())
        )
    }
    for symbol in tracked_symbols:
        if not symbol.endswith("USDT"):
            continue
        base = symbol[:-4]
        BINGX_MAP.setdefault(symbol, f"{base}-USDT")
        CRYPTO_SYMBOLS.add(symbol)
        SYMBOLS[symbol] = AssetClass.CRYPTO

def refresh_runtime_symbols(
    *,
    force: bool = False,
    executor: Optional[BingXExecutor] = None,
) -> list:
    """Reload the frozen whitelist without dropping mappings for live positions."""
    top50 = fetch_top50_crypto(force=force)
    ensure_state_symbol_mappings()
    if executor is not None:
        executor.update_symbol_map(BINGX_MAP)
    return top50

def _route_ids_for_symbol(routes, symbol: str) -> Tuple[str, ...]:
    return tuple(
        sorted(
            route
            for route in routes
            if len(str(route).split(":")) >= 2
            and str(route).split(":")[1] == symbol
        )
    )

def _record_matches_contract(
    key: str,
    record: dict,
    internal_symbol: str,
    exchange_symbol: str,
) -> bool:
    tokens = (
        str(key),
        str(record.get("symbol", "")),
        str(record.get("exchange_symbol", "")),
    )
    internal = internal_symbol.upper()
    exchange = exchange_symbol.upper()
    return any(
        internal in token.upper() or exchange in token.upper()
        for token in tokens
    )

def _preflight_live_state_snapshot() -> AutoTradeState:
    if state.state_filename == "live_state.json":
        return state
    snapshot = AutoTradeState("live_state.json")
    snapshot.load()
    return snapshot

def _missing_contract_exposure_reasons(
    internal_symbol: str,
    exchange_symbol: str,
    positions: List[dict],
    orders: List[dict],
) -> Tuple[str, ...]:
    snapshot = _preflight_live_state_snapshot()
    reasons: List[str] = []
    state_positions = sum(
        1
        for key, record in snapshot.positions.items()
        if str(record.get("status", "OPEN")).upper() != "CLOSED"
        and _record_matches_contract(key, record, internal_symbol, exchange_symbol)
    )
    state_pending = sum(
        1
        for key, record in snapshot.pending_signals.items()
        if _record_matches_contract(key, record, internal_symbol, exchange_symbol)
    )
    state_intents = sum(
        1
        for key, record in snapshot.order_intents.items()
        if str(record.get("status", "UNKNOWN")).upper()
        not in TERMINAL_LIVE_INTENT_STATUSES
        and _record_matches_contract(key, record, internal_symbol, exchange_symbol)
    )
    exchange_positions = sum(
        1
        for record in positions
        if _record_matches_contract("", record, internal_symbol, exchange_symbol)
    )
    exchange_orders = sum(
        1
        for record in orders
        if _record_matches_contract("", record, internal_symbol, exchange_symbol)
    )
    for name, count in (
        ("state_positions", state_positions),
        ("state_pending", state_pending),
        ("state_intents", state_intents),
        ("exchange_positions", exchange_positions),
        ("exchange_orders", exchange_orders),
    ):
        if count:
            reasons.append(f"{name}={count}")
    return tuple(reasons)

def smc_runtime_parameters() -> Dict[str, Any]:
    return {
        "min_score": MIN_SCORE,
        "max_hold_bars": SMC_MAX_HOLD_BARS,
        "sl_atr_mult": SL_ATR_MULT,
        "tp_atr_mult": TP_ATR_MULT,
        "confirmation_mode": SMC_CONFIRMATION_MODE,
        "htf_lookback_msb": 30,
        "htf_lookback_ob": 20,
        "fvg_max_bars": 10,
        "htf_structure_weight": 20,
        "htf_bos_weight": 10,
        "htf_ob_weight": 20,
        "htf_fvg_weight": 15,
        "htf_discount_weight": 5,
        "ltf_sweep_weight": 15,
        "ltf_reversal_weight": 15,
        "ltf_momentum_weight": 10,
    }

def smc_mtf_parameters(symbol: str) -> Dict[str, Any]:
    params = smc_runtime_parameters()
    params["min_score"] = SMC_MTF_MIN_SCORES[symbol]
    return params

def smc_d1_parameters() -> Dict[str, Any]:
    """Frozen single-timeframe settings used in the 6.5-year D1 backtest."""
    return {
        "min_score": 50,
        "max_hold_bars": 24,
        "sl_atr_mult": 1.5,
        "tp_atr_mult": 3.0,
    }

def _ensure_smc_trailing_state(position: dict) -> bool:
    """Attach fixed-R trailing state without changing non-SMC exits."""
    if (
        not SMC_TRAILING_ENABLED
        or position.get("strategy_name") != "SMC_MTF_V2"
        or position.get("timeframe") != LTF_TF.value
    ):
        return False
    if any(key not in position for key in ("entry_price", "sl", "direction")):
        return False

    changed = False
    entry_price = float(position["entry_price"])
    initial_sl = float(position.get("initial_sl", position["sl"]))
    initial_risk = float(position.get("initial_risk", abs(entry_price - initial_sl)))
    if initial_risk <= 0:
        return False

    defaults = {
        "initial_sl": initial_sl,
        "initial_risk": initial_risk,
        "trail_activation_r": SMC_TRAIL_ACTIVATION_R,
        "trail_distance_r": SMC_TRAIL_DISTANCE_R,
        "trail_distance": SMC_TRAIL_DISTANCE_R * initial_risk,
        "highest_since_entry": entry_price,
        "lowest_since_entry": entry_price,
        "trailing_stop_active": False,
    }
    if position["direction"] == "LONG":
        defaults["trail_activation_price"] = (
            entry_price + SMC_TRAIL_ACTIVATION_R * initial_risk
        )
    else:
        defaults["trail_activation_price"] = (
            entry_price - SMC_TRAIL_ACTIVATION_R * initial_risk
        )

    for key, value in defaults.items():
        if key not in position:
            position[key] = value
            changed = True
    return changed

def _update_smc_trailing_after_bar(position: dict, candle: Candle) -> bool:
    """Move the stop from a completed bar; it is used starting next bar."""
    if (
        not SMC_TRAILING_ENABLED
        or position.get("strategy_name") != "SMC_MTF_V2"
        or position.get("timeframe") != LTF_TF.value
    ):
        return False
    _ensure_smc_trailing_state(position)
    activation = position.get("trail_activation_price")
    distance = position.get("trail_distance")
    if activation is None or distance is None:
        return False

    changed = False
    if position["direction"] == "LONG":
        if candle.high > float(position.get("highest_since_entry", position["entry_price"])):
            position["highest_since_entry"] = candle.high
            changed = True
        if candle.low < float(position.get("lowest_since_entry", position["entry_price"])):
            position["lowest_since_entry"] = candle.low
            changed = True
        if candle.high > float(activation):
            new_sl = candle.high - float(distance)
            if new_sl > float(position["sl"]):
                position["sl"] = new_sl
                position["trailing_stop_active"] = True
                changed = True
    else:
        if candle.low < float(position.get("lowest_since_entry", position["entry_price"])):
            position["lowest_since_entry"] = candle.low
            changed = True
        if candle.high > float(position.get("highest_since_entry", position["entry_price"])):
            position["highest_since_entry"] = candle.high
            changed = True
        if candle.low < float(activation):
            new_sl = candle.low + float(distance)
            if new_sl < float(position["sl"]):
                position["sl"] = new_sl
                position["trailing_stop_active"] = True
                changed = True
    return changed

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "auto_trade_smc_mtf")

os.makedirs(LOG_DIR, exist_ok=True)

LIVE_ORDER_HISTORY_PATH = os.path.join(LOG_DIR, "live_order_history.jsonl")

def _append_live_order_history(
    event: str,
    *,
    required: bool = False,
    **details: Any,
) -> bool:
    """Append one durable, credential-free live order event on the VPS."""
    record = {
        "schema_version": 1,
        "recorded_at": now_utc().isoformat().replace("+00:00", "Z"),
        "event": event,
        **details,
    }
    try:
        directory = os.path.dirname(os.path.abspath(LIVE_ORDER_HISTORY_PATH))
        os.makedirs(directory, exist_ok=True)
        with open(LIVE_ORDER_HISTORY_PATH, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True, separators=(",", ":"), default=str))
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
    except OSError as exc:
        print(f"  LIVE ORDER HISTORY ERROR: {exc}")
        if required:
            raise RuntimeError("Live order history is not writable") from exc
        return False
    return True

class AutoTradeState:
    _DATETIME_FIELDS = {
        "timestamp", "signal_time", "decision_time", "signal_bar_time",
        "queued_at", "execution_time", "entry_time", "exit_time", "last_processed_bar",
        "created_at", "filled_at", "closed_at", "recovered_at",
    }

    def __init__(self, state_filename: str = "state.json"):
        self.state_filename = state_filename
        self.mode = "LIVE" if state_filename == "live_state.json" else "PAPER"
        self.positions: Dict[str, dict] = {}  # symbol or route -> position info
        self.last_signal: Dict[str, dict] = {}
        self.paper_equity: float = CAPITAL
        self.total_pnl: float = 0.0
        self.trade_log: List[dict] = []
        self.pending_signals: Dict[str, dict] = {}
        self.last_processed_bar: Dict[str, str] = {}
        self.order_intents: Dict[str, dict] = {}

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "positions": self.positions,
            "last_signal": self.last_signal,
            "paper_equity": self.paper_equity,
            "total_pnl": self.total_pnl,
            "trades": self.trade_log[-100:],
            "pending_signals": self.pending_signals,
            "last_processed_bar": self.last_processed_bar,
            "order_intents": self.order_intents,
        }

    def _path(self, path: Optional[str] = None) -> str:
        return os.fspath(path or os.path.join(LOG_DIR, self.state_filename))

    @staticmethod
    def _parse_datetime(value):
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _restore_record(cls, record: dict) -> dict:
        restored = dict(record)
        for key in cls._DATETIME_FIELDS:
            if key not in restored or restored[key] is None:
                continue
            parsed = cls._parse_datetime(restored[key])
            if parsed is not None:
                restored[key] = parsed
        return restored

    @classmethod
    def _restore_mapping(cls, value) -> Dict[str, dict]:
        if not isinstance(value, dict):
            return {}
        return {
            str(symbol): cls._restore_record(record)
            for symbol, record in value.items()
            if isinstance(record, dict)
        }

    def load(self, path: Optional[str] = None) -> bool:
        path = self._path(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                raise ValueError("state root must be an object")

            positions = self._restore_mapping(payload.get("positions", {}))
            for original_key, position in positions.items():
                position.setdefault("symbol", original_key)
                # Older state files only recorded entry_time.
                if position.get("execution_time") is None:
                    position["execution_time"] = position.get("entry_time")
                position.setdefault("entry_commission", 0.0)
                position.setdefault("bars_held", 0)
                position.setdefault("max_hold", 24)
                position.setdefault("last_processed_bar", None)
                try:
                    Timeframe(position.get("timeframe"))
                except (TypeError, ValueError):
                    position["timeframe"] = LEGACY_SMC_TF.value
                if not position.get("strategy_name"):
                    position["strategy_name"] = "SMC_MTF_V2"
                position.setdefault(
                    "route_id",
                    strategy_route_id(
                        str(position["strategy_name"]),
                        str(position["symbol"]),
                        position.get("timeframe"),
                    ),
                )
                position.setdefault("score", 0)
                position.setdefault("reasons", "")
                _ensure_smc_trailing_state(position)

            pending_signals = self._restore_mapping(payload.get("pending_signals", {}))
            pending_signals = {
                symbol: signal for symbol, signal in pending_signals.items()
                if isinstance(signal.get("signal_bar_time"), datetime)
            }
            for original_key, signal in pending_signals.items():
                signal.setdefault("symbol", original_key)
                try:
                    Timeframe(signal.get("timeframe"))
                except (TypeError, ValueError):
                    signal["timeframe"] = LEGACY_SMC_TF.value
                if not signal.get("strategy_name"):
                    signal["strategy_name"] = "SMC_MTF_V2"
                signal.setdefault("route_id", signal_route(signal))
            last_signal = self._restore_mapping(payload.get("last_signal", {}))

            trades_raw = payload.get("trades", payload.get("trade_log", []))
            trades = [
                self._restore_record(trade)
                for trade in trades_raw
                if isinstance(trade, dict)
            ] if isinstance(trades_raw, list) else []

            last_processed_raw = payload.get("last_processed_bar", {})
            last_processed = dict(last_processed_raw) if isinstance(last_processed_raw, dict) else {}
            order_intents = self._restore_mapping(payload.get("order_intents", {}))
            paper_equity = float(payload.get("paper_equity", CAPITAL))
            total_pnl = float(payload.get("total_pnl", 0.0))
        except FileNotFoundError:
            return False
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            print(f"  State restore skipped ({path}): {exc}")
            return False

        if unlimited_route_mode():
            positions = {
                state_key_for_position(position, key): position
                for key, position in positions.items()
            }
            pending_signals = {
                state_key_for_signal(signal): signal
                for signal in pending_signals.values()
            }
            migrated_last_processed: Dict[str, str] = {}
            for key, position in positions.items():
                legacy_key = str(position.get("symbol", key))
                value = last_processed.get(key, last_processed.get(legacy_key))
                if value is not None:
                    migrated_last_processed[key] = value
            last_processed = migrated_last_processed

        self.positions = positions
        self.last_signal = last_signal
        self.paper_equity = paper_equity
        self.total_pnl = total_pnl
        self.trade_log = trades
        self.pending_signals = pending_signals
        self.last_processed_bar = last_processed
        self.order_intents = order_intents
        return True

    def save(self, path: Optional[str] = None) -> None:
        path = self._path(path)
        directory = os.path.dirname(os.path.abspath(path))
        os.makedirs(directory, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

state = AutoTradeState()

tg = TelegramReporter()

def is_market_open(symbol: str) -> bool:
    now = now_utc()
    weekday = now.weekday()  # 0=Mon, 6=Sun
    hour = now.hour

    # Crypto: 24/7
    if symbol in CRYPTO_SYMBOLS:
        return True

    # Forex: closed Friday 22:00 UTC through Sunday 21:59 UTC.
    if symbol in FOREX_SYMBOLS:
        if weekday == 4 and hour >= 22:
            return False
        if weekday == 5:
            return False
        if weekday == 6 and hour < 22:
            return False
        return True

    # Gold: closed Friday 22:00 UTC through Sunday 22:59 UTC.
    if symbol in COMMODITY_SYMBOLS:
        if weekday == 4 and hour >= 22:
            return False
        if weekday == 5:
            return False
        if weekday == 6 and hour < 23:
            return False
        return True

    return True

def detect_regime(series: BarSeries) -> MarketRegime:
    if len(series) < 50:
        return MarketRegime.UNKNOWN
    closes = np.array([c.close for c in series.candles])
    highs = np.array([c.high for c in series.candles])
    lows = np.array([c.low for c in series.candles])

    # Volatility regime: ATR% vs 50-period SMA
    atr = np.mean(highs[-20:] - lows[-20:])
    atr_pct = atr / closes[-1] * 100
    hist_atr = [np.mean(highs[i-20:i] - lows[i-20:i]) / closes[i-1] * 100
                for i in range(50, len(closes)) if i >= 20]
    if hist_atr:
        atr_percentile = sum(1 for v in hist_atr if v < atr_pct) / len(hist_atr)
        if atr_percentile > 0.8:
            return MarketRegime.HIGH_VOL
        if atr_percentile < 0.2:
            return MarketRegime.LOW_VOL

    # Trend regime: EMA50 vs EMA200
    if len(closes) >= 200:
        ema50 = np.mean(closes[-50:])
        ema200 = np.mean(closes[-200:])
        if closes[-1] > ema50 > ema200:
            return MarketRegime.BULL
        if closes[-1] < ema50 < ema200:
            return MarketRegime.BEAR

    # Range: ADX-like
    lookback = min(50, len(closes))
    highs_range = highs[-lookback:]
    lows_range = lows[-lookback:]
    range_pct = (max(highs_range) - min(lows_range)) / closes[-1] * 100
    if range_pct < 5:
        return MarketRegime.RANGE

    return MarketRegime.TRENDING if closes[-1] > np.mean(closes[-20:]) else MarketRegime.MEAN_REVERTING

def portfolio_bucket(symbol: str) -> str:
    """Group crypto separately while forex and gold share one bucket."""
    return "CRYPTO" if symbol.endswith("USDT") or symbol in CRYPTO_SYMBOLS else "FOREX_GOLD"

def _capacity_block(new_symbol: str, reserved: Dict[str, dict]) -> Optional[str]:
    if unlimited_route_mode():
        return None
    if len(reserved) >= MAX_POSITIONS:
        return f"max {MAX_POSITIONS} total positions"

    bucket = portfolio_bucket(new_symbol)
    bucket_limit = (
        MAX_CRYPTO_POSITIONS if bucket == "CRYPTO" else MAX_FOREX_GOLD_POSITIONS
    )
    bucket_count = sum(
        1
        for key, record in reserved.items()
        if portfolio_bucket(str(record.get("symbol", key))) == bucket
    )
    if bucket_count >= bucket_limit:
        label = "crypto" if bucket == "CRYPTO" else "forex/gold"
        return f"max {bucket_limit} {label} positions"
    return None

def _tracked_strategy_count(strategy_name: str) -> int:
    tracked = [
        position
        for position in state.positions.values()
        if position.get("status") == "OPEN"
    ]
    tracked.extend(state.pending_signals.values())
    return sum(
        1
        for position in tracked
        if position.get("strategy_name", "SMC_MTF_V2") == strategy_name
    )

def all_reserved_positions() -> Dict[str, dict]:
    open_positions = {
        key: position
        for key, position in state.positions.items()
        if position.get("status") == "OPEN"
    }
    return {**external_reservations, **open_positions, **state.pending_signals}

def symbol_is_reserved(symbol: str) -> bool:
    return any(
        str(record.get("symbol", key)) == symbol
        for key, record in all_reserved_positions().items()
    )

def route_is_reserved(signal: dict) -> bool:
    return state_key_for_signal(signal) in all_reserved_positions()

def single_entry_path_reservation_block(signal: dict) -> Optional[str]:
    """Block a sibling when a configured shared path is already reserved."""
    path_id = single_entry_path(signal)
    if path_id is None:
        return None
    for key, record in all_reserved_positions().items():
        reserved_route = signal_route(record)
        if reserved_route is None and str(key) in EXACT62_SELECTION_BY_ROUTE:
            reserved_route = str(key)
        selected = EXACT62_SELECTION_BY_ROUTE.get(str(reserved_route))
        if selected is None or str(selected["path_id"]) != path_id:
            continue
        return f"SINGLE_ENTRY_PATH:{path_id}:OPEN_PENDING:{reserved_route}"
    return None

def _external_side_block(symbol: str, direction: Optional[str]) -> Optional[str]:
    if not direction:
        return None
    for reservation in external_reservations.values():
        if (
            reservation.get("symbol") == symbol
            and str(reservation.get("direction", "")).upper() == direction.upper()
        ):
            return f"external {symbol} {direction.upper()} exposure"
    return None

def external_reservation_key(symbol: str, direction: str) -> str:
    return (
        f"EXTERNAL:{symbol}:{direction.upper()}"
        if unlimited_route_mode()
        else symbol
    )

def portfolio_heat_block(
    new_symbol: str,
    new_strategy: Optional[str] = None,
    new_timeframe: Optional[Any] = None,
    new_direction: Optional[str] = None,
    new_route_id: Optional[str] = None,
) -> Optional[str]:
    reserved = all_reserved_positions()

    route = str(new_route_id) if new_route_id else (
        strategy_route_id(
            str(new_strategy or ""),
            new_symbol,
            new_timeframe,
        )
        if new_strategy
        else None
    )
    reservation_key = route if unlimited_route_mode() and route else new_symbol
    if reservation_key in reserved:
        return f"already open/pending {reservation_key}"

    if unlimited_route_mode():
        return _external_side_block(new_symbol, new_direction)

    if (
        new_strategy == "SMC_MTF_V2"
        and _tracked_strategy_count("SMC_MTF_V2") >= MAX_SMC_POSITIONS
    ):
        return (
            f"max {MAX_SMC_POSITIONS} SMC positions "
            f"({MAX_POSITIONS - MAX_SMC_POSITIONS} slots reserved for TF/PA)"
        )

    return _capacity_block(new_symbol, reserved)

def check_portfolio_heat(
    new_symbol: str,
    new_direction: str,
    new_strategy: Optional[str] = None,
    new_timeframe: Optional[Any] = None,
) -> bool:
    block = portfolio_heat_block(
        new_symbol,
        new_strategy,
        new_timeframe,
        new_direction,
    )
    if block:
        print(f"  PORTFOLIO: {block}, skip")
        return False

    return True

def portfolio_heat_block_signal(signal: dict) -> Optional[str]:
    path_block = single_entry_path_reservation_block(signal)
    if path_block:
        return path_block
    return portfolio_heat_block(
        str(signal["symbol"]),
        signal.get("strategy_name"),
        signal.get("timeframe"),
        signal.get("direction"),
        signal_route(signal),
    )

def mark_portfolio_blocked(
    scan_results: Dict[str, Optional[Dict]],
    symbol: str,
    reason: str,
    route: Optional[str] = None,
) -> None:
    """Keep blocked signals visible without presenting them as actionable."""
    for result in scan_results.values():
        if not isinstance(result, dict) or result.get("symbol") != symbol:
            continue
        if route is not None and signal_route(result) != route:
            continue
        result["preview_only"] = True
        result["below_threshold"] = True
        result["effective_score"] = 0
        result["trade_eligible"] = False
        result["blocked_by"] = reason

_bingx_last_request = 0.0

_yahoo_last_request = 0.0

_binance_spot_last_request = 0.0

_binance_residual_factor_cache: Dict[str, Any] = {}

BINGX_MAX_KLINES = 1000

BINANCE_SPOT_MAX_KLINES = 1000

BINANCE_SPOT_KLINE_URLS = (
    "https://api.binance.com/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
)

BINANCE_FUTURES_KLINE_URL = "https://fapi.binance.com/fapi/v1/klines"

def _bingx_limit_for(tf: Timeframe, days: int) -> int:
    bars_per_day = max(1, 1440 // tf.minutes())
    requested = max(1, int(days)) * bars_per_day + 2
    return min(BINGX_MAX_KLINES, requested)

def fetch_bingx_klines(symbol: str, interval: str, limit: int = 100, include_forming: bool = False) -> Optional[BarSeries]:
    global _bingx_last_request
    bingx_sym = BINGX_MAP.get(symbol)
    if bingx_sym is None:
        return None

    elapsed = time.time() - _bingx_last_request
    if elapsed < 0.3:
        time.sleep(0.3 - elapsed)

    url = "https://open-api.bingx.com/openApi/swap/v2/quote/klines"
    params = {"symbol": bingx_sym, "interval": interval, "limit": limit}
    try:
        resp = requests.get(url, params=params, timeout=5)
        _bingx_last_request = time.time()
    except requests.Timeout:
        print(f"  BingX timeout {symbol} {interval}")
        return None
    except Exception as e:
        print(f"  BingX error {symbol}: {_safe_exception_text(e)}")
        return None

    if resp.status_code != 200:
        print(f"  BingX {symbol}: HTTP {resp.status_code}")
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if data.get("code") != 0:
        return None

    bars = data.get("data")
    if not bars:
        return None

    try:
        timestamps = np.array([datetime.fromtimestamp(b["time"] / 1000, tz=timezone.utc) for b in bars])
        opens = np.array([float(b["open"]) for b in bars])
        highs = np.array([float(b["high"]) for b in bars])
        lows = np.array([float(b["low"]) for b in bars])
        closes = np.array([float(b["close"]) for b in bars])
        volumes = np.array([float(b["volume"]) for b in bars])
    except (KeyError, ValueError, TypeError) as e:
        print(f"  BingX parse error {symbol}: {e}")
        return None

    interval_tf = {
        "15m": Timeframe.M15,
        "1h": Timeframe.H1,
        "4h": Timeframe.H4,
        "8h": Timeframe.H8,
        "1d": Timeframe.D1,
    }.get(interval)
    if interval_tf is None:
        raise UnsupportedTimeframeError(f"Unsupported BingX interval: {interval}")
    order = np.argsort(timestamps)
    try:
        series = from_numpy(
            timestamps=timestamps[order], open=opens[order], high=highs[order], low=lows[order],
            close=closes[order], volume=volumes[order],
            symbol=symbol, timeframe=interval_tf,
            asset_class=SYMBOLS.get(symbol, AssetClass.CRYPTO), provider="bingx",
        )
    except TypeError:
        series = from_numpy(
            timestamps=timestamps[order], open=opens[order], high=highs[order], low=lows[order],
            close=closes[order], volume=volumes[order],
            symbol=symbol, timeframe=interval_tf,
            asset_class=SYMBOLS.get(symbol, AssetClass.CRYPTO),
        )
    if include_forming:
        return series
    closed = closed_bars_only(series, now_utc())
    return closed if len(closed) else None

def fetch_binance_spot_h4(
    symbol: str,
    *,
    limit: int = BINANCE_SPOT_MAX_KLINES,
) -> Optional[BarSeries]:
    """Fetch factor H4 bars with frozen-source and delisting fallbacks."""
    global _binance_spot_last_request
    payload = None
    provider = "binance_spot"
    for url in BINANCE_SPOT_KLINE_URLS:
        elapsed = time.time() - _binance_spot_last_request
        if elapsed < 0.08:
            time.sleep(0.08 - elapsed)
        try:
            response = requests.get(
                url,
                params={"symbol": symbol, "interval": "4h", "limit": limit},
                timeout=8,
            )
            _binance_spot_last_request = time.time()
            if response.status_code != 200:
                continue
            candidate = response.json()
            if isinstance(candidate, list) and candidate:
                payload = candidate
                break
        except (requests.RequestException, ValueError):
            continue
    if payload is None and symbol in BINGX_MAP:
        bingx_fallback = fetch_bingx_klines(
            symbol,
            "4h",
            limit=limit,
            include_forming=False,
        )
        if bingx_fallback is not None:
            print(f"  Residual factor source fallback: {symbol} BingX Swap")
            return bingx_fallback
    if payload is None:
        elapsed = time.time() - _binance_spot_last_request
        if elapsed < 0.08:
            time.sleep(0.08 - elapsed)
        try:
            response = requests.get(
                BINANCE_FUTURES_KLINE_URL,
                params={"symbol": symbol, "interval": "4h", "limit": limit},
                timeout=8,
            )
            _binance_spot_last_request = time.time()
            candidate = response.json() if response.status_code == 200 else None
            if isinstance(candidate, list) and candidate:
                payload = candidate
                provider = "binance_futures_factor_fallback"
                print(f"  Residual factor source fallback: {symbol} Binance Futures")
        except (requests.RequestException, ValueError):
            pass
    if payload is None:
        print(f"  Binance Spot H4 unavailable: {symbol}")
        return None

    try:
        timestamps = np.array([
            datetime.fromtimestamp(float(row[0]) / 1000.0, tz=timezone.utc)
            for row in payload
        ])
        opens = np.array([float(row[1]) for row in payload])
        highs = np.array([float(row[2]) for row in payload])
        lows = np.array([float(row[3]) for row in payload])
        closes = np.array([float(row[4]) for row in payload])
        volumes = np.array([float(row[5]) for row in payload])
    except (IndexError, TypeError, ValueError) as exc:
        print(f"  Binance Spot H4 parse error {symbol}: {exc}")
        return None
    order = np.argsort(timestamps)
    series = from_numpy(
        timestamps=timestamps[order],
        open=opens[order],
        high=highs[order],
        low=lows[order],
        close=closes[order],
        volume=volumes[order],
        symbol=symbol,
        timeframe=Timeframe.H4,
        asset_class=AssetClass.CRYPTO,
        provider=provider,
    )
    closed = closed_bars_only(series, now_utc())
    return closed if len(closed) else None

def _latest_closed_h4_open(reference: Optional[datetime] = None) -> datetime:
    current = reference or now_utc()
    current = current.astimezone(timezone.utc)
    seconds = int(current.timestamp())
    bucket = seconds - seconds % (4 * 60 * 60)
    return datetime.fromtimestamp(bucket - 4 * 60 * 60, tz=timezone.utc)

def get_binance_residual_factor(*, force: bool = False) -> Optional[Dict[datetime, float]]:
    """Build the exact equal-weight 47-symbol H4 log-return factor."""
    expected_latest = _latest_closed_h4_open()
    cached_latest = _binance_residual_factor_cache.get("latest")
    cached_values = _binance_residual_factor_cache.get("values")
    if not force and cached_latest == expected_latest and isinstance(cached_values, dict):
        return dict(cached_values)

    series_by_symbol: Dict[str, BarSeries] = {}
    missing: List[str] = []
    stale: List[str] = []
    for symbol in BINANCE_RESIDUAL_FACTOR_SYMBOLS:
        series = fetch_binance_spot_h4(symbol)
        if series is None or len(series) < 2:
            missing.append(symbol)
            continue
        if series.candles[-1].timestamp != expected_latest:
            stale.append(symbol)
            continue
        series_by_symbol[symbol] = series
    if missing or stale:
        details = []
        if missing:
            details.append(f"missing={','.join(missing)}")
        if stale:
            details.append(f"stale={','.join(stale)}")
        print(f"  Residual factor fail-closed: {'; '.join(details)}")
        return None

    sums: Dict[datetime, float] = {}
    counts: Dict[datetime, int] = {}
    for series in series_by_symbol.values():
        previous_close: Optional[float] = None
        for candle in series.candles:
            close = float(candle.close)
            if previous_close is not None and previous_close > 0 and close > 0:
                timestamp = candle.timestamp
                value = math.log(close / previous_close)
                if math.isfinite(value):
                    sums[timestamp] = sums.get(timestamp, 0.0) + value
                    counts[timestamp] = counts.get(timestamp, 0) + 1
            previous_close = close
    factor = {
        timestamp: total / counts[timestamp]
        for timestamp, total in sums.items()
        if counts.get(timestamp, 0) > 0
    }
    if expected_latest not in factor or len(factor) < 300:
        print("  Residual factor fail-closed: insufficient aligned H4 returns")
        return None
    _binance_residual_factor_cache.clear()
    _binance_residual_factor_cache.update({
        "latest": expected_latest,
        "values": factor,
    })
    return dict(factor)

def fetch_yahoo(symbol: str, tf: Timeframe, days: int = 7, include_forming: bool = False) -> Optional[BarSeries]:
    global _yahoo_last_request
    yahoo_sym = YAHOO_MAP.get(symbol, f"{symbol}-USD")

    end = now_utc()
    start = end - timedelta(days=days)

    source_tf = Timeframe.H1 if tf == Timeframe.H4 else tf
    source_days = days

    interval_map = {Timeframe.M15: "15m", Timeframe.H1: "60m", Timeframe.D1: "1d"}
    interval = interval_map.get(source_tf)
    if interval is None:
        raise UnsupportedTimeframeError(f"Yahoo cannot provide {tf.value}")

    p1 = int((end - timedelta(days=source_days)).timestamp())
    p2 = int(end.timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
    params = {"period1": p1, "period2": p2, "interval": interval, "events": "history"}
    headers = {"User-Agent": "Mozilla/5.0"}

    elapsed = time.time() - _yahoo_last_request
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        _yahoo_last_request = time.time()
        if resp.status_code != 200:
            return None

        data = resp.json()
        result = data["chart"]["result"][0]
        ts = result["timestamp"]
        quotes = result["indicators"]["quote"][0]

        o = np.array([x if x else np.nan for x in quotes.get("open", [])])
        h = np.array([x if x else np.nan for x in quotes.get("high", [])])
        l = np.array([x if x else np.nan for x in quotes.get("low", [])])
        c = np.array([x if x else np.nan for x in quotes.get("close", [])])
        v = np.array([x if x else 0 for x in quotes.get("volume", [])])
        mask = ~(np.isnan(o) | np.isnan(h) | np.isnan(l) | np.isnan(c))
        # Yahoo occasionally emits malformed OHLC rows. Filter them before
        # constructing BarSeries so one bad candle cannot disable a symbol.
        mask &= (
            (o > 0)
            & (h > 0)
            & (l > 0)
            & (c > 0)
            & (v >= 0)
            & (h >= l)
            & (h >= np.maximum(o, c))
            & (l <= np.minimum(o, c))
        )
        timestamps = np.array([datetime.fromtimestamp(t, tz=timezone.utc) for t in ts])

        # Yahoo can repeat its latest intraday timestamp while updating a bar.
        # Keep the last observation for each timestamp and restore time order.
        last_index_by_timestamp = {
            timestamps[i]: i for i in np.flatnonzero(mask)
        }
        keep = np.array(
            sorted(last_index_by_timestamp.values(), key=lambda i: timestamps[i]),
            dtype=int,
        )
        if len(keep) == 0:
            return None

        series = from_numpy(
            timestamps=timestamps[keep], open=o[keep], high=h[keep], low=l[keep],
            close=c[keep], volume=v[keep],
            symbol=symbol, timeframe=source_tf,
            asset_class=SYMBOLS.get(symbol, AssetClass.COMMODITY),
            provider="yahoo",
        )

        if tf == Timeframe.H4 and source_tf == Timeframe.H1:
            series = aggregate_aligned(series, Timeframe.H4, drop_incomplete=True)

        if include_forming:
            return series
        closed = closed_bars_only(series, now_utc())
        return closed if len(closed) else None
    except Exception as e:
        print(f"  Yahoo fetch error {symbol}: {_safe_exception_text(e)}")
        return None

def fetch_data(symbol: str, tf: Timeframe, days: int, include_forming: bool = False) -> Optional[BarSeries]:
    if symbol in BINGX_MAP:
        if tf in {Timeframe.H6, Timeframe.H12}:
            source = fetch_bingx_klines(
                symbol,
                "1h",
                limit=BINGX_MAX_KLINES,
                include_forming=include_forming,
            )
            if source is None:
                return None
            aggregated = aggregate_aligned(
                source,
                tf,
                drop_incomplete=True,
            )
            if include_forming:
                return aggregated
            closed = closed_bars_only(aggregated, now_utc())
            return closed if len(closed) else None
        interval_map = {
            Timeframe.M15: "15m",
            Timeframe.H1: "1h",
            Timeframe.H4: "4h",
            Timeframe.H8: "8h",
            Timeframe.D1: "1d",
        }
        interval = interval_map.get(tf)
        if interval is None:
            raise UnsupportedTimeframeError(f"BingX cannot provide {tf.value}")
        limit = _bingx_limit_for(tf, days)
        return fetch_bingx_klines(symbol, interval, limit=limit, include_forming=include_forming)
    return fetch_yahoo(symbol, tf, days=days, include_forming=include_forming)

def signal_data_provider(strategy_name: str, symbol: str, timeframe: Timeframe) -> str:
    route = f"{strategy_name}:{symbol}"
    if timeframe == D1_TF and route in YAHOO_D1_SIGNAL_ROUTES:
        return "yahoo"
    return "bingx" if symbol in BINGX_MAP else "yahoo"

def fetch_signal_data(
    strategy_name: str,
    symbol: str,
    timeframe: Timeframe,
    days: int,
) -> Optional[BarSeries]:
    if signal_data_provider(strategy_name, symbol, timeframe) == "yahoo":
        return fetch_yahoo(symbol, timeframe, days=days)
    return fetch_data(symbol, timeframe, days)

_htf_cache: Dict[str, dict] = {}

def get_htf_cached(symbol: str) -> Optional[BarSeries]:
    global _htf_cache
    cached = _htf_cache.get(symbol)
    if cached is not None:
        latest = fetch_data(symbol, HTF_TF, 1)
        if latest and len(latest) > 0:
            latest_bar_time = latest.candles[-1].timestamp
            if latest_bar_time == cached["last_bar_time"]:
                return cached["htf"]
    htf = fetch_data(symbol, HTF_TF, HTF_ANALYSIS_DAYS)
    if htf and len(htf) > 0:
        _htf_cache[symbol] = {"htf": htf, "last_bar_time": htf.candles[-1].timestamp}
    return htf

def analyze_symbol(
    symbol: str,
    strategy: SMCMultiTimeframe,
    min_score_filter: int = 50,
    signal_min_score_override: Optional[int] = None,
    include_blocked_preview: bool = False,
) -> Optional[dict]:
    htf = get_htf_cached(symbol)
    if htf is None or len(htf) < 10:
        return None

    ltf = fetch_data(symbol, LTF_TF, LTF_ANALYSIS_DAYS)
    if ltf is None or len(ltf) <= strategy.get_warmup_bars():
        return None

    strategy.set_htf_data(htf)

    regime = detect_regime(htf)
    strategy._regime = regime

    idx = len(ltf) - 1
    signal = strategy.generate_signal(
        ltf,
        idx,
        regime=regime,
        min_score_override=signal_min_score_override,
        include_blocked_preview=include_blocked_preview,
    )

    if signal is None or signal.direction == Direction.NEUTRAL:
        return None

    meta = signal.metadata or {}
    indicator_values = signal.indicator_values or {}
    score = signal.score
    preview_only = bool(meta.get("preview_only", False))
    raw_score = float(indicator_values.get("raw_score", score))
    effective_score = float(indicator_values.get("effective_score", score))
    blocked_by = str(indicator_values.get("blocked_by", meta.get("blocked_by", "")))
    below_threshold = preview_only or effective_score < min_score_filter

    sl_from_strat = meta.get("sl", 0.0)
    tp_from_strat = meta.get("tp", 0.0)

    if sl_from_strat > 0 and tp_from_strat > 0:
        sl = sl_from_strat
        tp = tp_from_strat
    else:
        htf_idx = strategy._find_htf_idx(ltf.candles[idx].timestamp)
        htf_atr = float(strategy._htf_atr_cache[htf_idx]) if strategy._htf_atr_cache is not None and htf_idx >= 0 else 0
        htf_close = htf.candles[htf_idx].close if htf_idx >= 0 else ltf.candles[idx].close
        if signal.direction == Direction.LONG:
            sl = htf_close - htf_atr * SL_ATR_MULT
            tp = htf_close + htf_atr * TP_ATR_MULT
        else:
            sl = htf_close + htf_atr * SL_ATR_MULT
            tp = htf_close - htf_atr * TP_ATR_MULT

    current_price = ltf.candles[idx].close
    stop_distance = abs(current_price - sl)
    risk_amount = state.paper_equity * RISK_PER_TRADE
    size_units = risk_amount / stop_distance if stop_distance > 0 else 0

    result = {
        "symbol": symbol,
        "strategy_name": signal.strategy_name or "SMC_MTF_V2",
        "timeframe": LTF_TF.value,
        "analysis_timeframe": f"{HTF_TF.value}/{LTF_TF.value}",
        "timestamp": ltf.candles[idx].timestamp,
        "signal_time": signal.timestamp,
        "decision_time": signal.timestamp,
        "signal_bar_time": ltf.candles[idx].timestamp,
        "direction": "LONG" if signal.direction == Direction.LONG else "SHORT",
        "current_price": current_price,
        "entry_price": current_price,
        "sl": float(sl),
        "tp": float(tp),
        "risk_reward": float(meta.get("risk_reward", 2.0)),
        "max_hold": int(meta.get("max_hold", 24)),
        "trail_activation_r": SMC_TRAIL_ACTIVATION_R,
        "trail_distance_r": SMC_TRAIL_DISTANCE_R,
        "size_units": size_units,
        "size_usd": size_units * current_price,
        "score": score,
        "required_score": float(min_score_filter),
        "raw_score": raw_score,
        "effective_score": effective_score,
        "preview_only": preview_only,
        "blocked_by": blocked_by,
        "trade_eligible": bool(
            indicator_values.get("trade_eligible", not below_threshold)
        ),
        "atr": float(indicator_values.get("htf_atr", 0.0)),
        "confidence": signal.confidence,
        "reasons": indicator_values.get("reasons", ""),
        "htf_trend": indicator_values.get("htf_trend", "?"),
        "regime": str(regime.value),
        "htf_bars": len(htf),
        "ltf_bars": len(ltf),
        "below_threshold": below_threshold,
    }
    return result

# REDACTED: removed private strategy material or identifying configuration.
def analyze_single_tf(symbol: str, strategy: Any, series: Optional[BarSeries]=None, timeframe: Timeframe=D1_TF, analysis_days: Optional[int]=None) -> Optional[dict]:
    """Generate a closed-bar single-timeframe signal using frozen settings."""
    if analysis_days is None:
        analysis_days = D1_ANALYSIS_DAYS if timeframe == D1_TF else 160
    series = series or fetch_data(symbol, timeframe, analysis_days)
    if series is None or len(series) <= strategy.get_warmup_bars():
        return None
    if hasattr(strategy, 'set_data'):
        strategy.set_data(series)
    if isinstance(strategy, SMCMultiTimeframe):
        strategy.set_htf_data(series)
    idx = len(series) - 1
    signal = strategy.generate_signal(series, idx, regime=MarketRegime.UNKNOWN)
    if signal is None or signal.direction == Direction.NEUTRAL:
        return None
    current = series.candles[idx]
    meta = signal.metadata or {}
    indicator_values = signal.indicator_values or {}
    strategy_name = signal.strategy_name or strategy.name
    direction = 'LONG' if signal.direction == Direction.LONG else 'SHORT'
    decision_time = current.timestamp + timedelta(minutes=timeframe.minutes())
    default_sl = current.close * (0.95 if direction == 'LONG' else 1.05)
    default_tp = current.close * (1.05 if direction == 'LONG' else 0.95)
    sl = float(meta.get('sl', default_sl))
    tp = float(meta.get('tp', default_tp))
    risk_reward = meta.get('risk_reward')
    entry_anchored_barriers = bool(getattr(strategy, 'live_entry_anchored', False) and meta.get('entry_anchored_barriers', False))
    stop_atr = float(meta.get('stop_atr', 0.0)) if entry_anchored_barriers else 0.0
    reasons = str(indicator_values.get('reasons', indicator_values.get('reason', '')))
    if not reasons and strategy_name == 'PURE_TREND_FOLLOW':
        reasons = f'DONCHIAN20_{direction};SMA300_FILTER'
    pass
    atr = indicator_values.get('atr', indicator_values.get('htf_atr', 0.0))
    try:
        atr = float(atr)
    except (TypeError, ValueError):
        atr = 0.0
    if not np.isfinite(atr) or atr <= 0:
        start = max(1, idx - 14 + 1)
        true_ranges = []
        for i in range(start, idx + 1):
            candle = series.candles[i]
            previous = series.candles[i - 1]
            true_ranges.append(max(candle.high - candle.low, abs(candle.high - previous.close), abs(candle.low - previous.close)))
        atr = float(np.mean(true_ranges)) if true_ranges else 0.0
    stop_distance = abs(current.close - sl)
    risk_amount = state.paper_equity * RISK_PER_TRADE
    size_units = risk_amount / stop_distance if stop_distance > 0 else 0.0
    return {'symbol': symbol, 'route_id': strategy_instance_route_id(strategy, symbol, timeframe), 'strategy_name': strategy_name, 'timeframe': timeframe.value, 'analysis_timeframe': timeframe.value, 'timestamp': current.timestamp, 'signal_time': decision_time, 'decision_time': decision_time, 'signal_bar_time': current.timestamp, 'direction': direction, 'current_price': current.close, 'entry_price': current.close, 'sl': sl, 'tp': tp, 'risk_reward': float(risk_reward) if risk_reward is not None else None, 'entry_anchored_barriers': entry_anchored_barriers, 'stop_atr': stop_atr, 'tp_pct': 0.05 if risk_reward is None and 'tp' not in meta else None, 'max_hold': entry_max_hold({'strategy_name': strategy_name, 'max_hold': meta.get('max_hold', 100)}, 100), 'size_units': size_units, 'size_usd': size_units * current.close, 'score': signal.score, 'required_score': required_score_for_route(strategy_name, symbol), 'raw_score': float(signal.score), 'effective_score': float(signal.score), 'preview_only': False, 'blocked_by': '', 'trade_eligible': True, 'atr': atr, 'confidence': signal.confidence, 'reasons': reasons, 'regime': MarketRegime.UNKNOWN.value, 'ltf_bars': len(series), 'below_threshold': False}

def signal_key(signal: dict) -> str:
    route = signal_route(signal)
    if route:
        return route
    return f"UNKNOWN:{signal['symbol']}:{signal.get('timeframe', LTF_TF.value)}"

# REDACTED: removed private strategy material or identifying configuration.
def required_score_for_route(strategy_name: str, symbol: str) -> float:
    if strategy_name == 'SMC_MTF_V2':
        return float(SMC_MTF_MIN_SCORES.get(symbol, 50))
    if strategy_name == 'PAYID_V2':
        return float(PAYID_D1_MIN_SCORES.get(symbol, 40))
    return {'PURE_TREND_FOLLOW': 60.0, 'PURE_MEAN_REVERSION': 60.0, 'PURE_BREAKOUT': 55.0, 'CR_LVB_30': 60.0, 'CR_LVB_30_LONG': 60.0, 'CR_DM_21_63': 60.0, 'RESIDUAL_BREAKOUT': 60.0, 'XAU_FIXED_BARRIER_DM': 60.0, 'XAU_LVB_60': 60.0}.get(strategy_name, 50.0)

def _candidate_strength(signal: dict) -> float:
    threshold = required_score_for_route(
        str(signal.get("strategy_name", "")),
        str(signal.get("symbol", "")),
    )
    return float(signal.get("effective_score", signal.get("score", 0))) / threshold

def _route_priority(signal: dict) -> int:
    route = signal_route(signal)
    if route in ROUTE_PRIORITY:
        return ROUTE_PRIORITY[route]
    return STRATEGY_PRIORITY.get(signal.get("strategy_name"), 0)

def select_entry_candidates(candidates: List[dict]) -> Tuple[List[dict], List[str]]:
    """Resolve same-symbol signals before they compete for shared slots."""
    if unlimited_route_mode():
        selectable: List[dict] = []
        single_path_groups: Dict[str, List[dict]] = {}
        for signal in candidates:
            path_id = single_entry_path(signal)
            if path_id is None:
                selectable.append(signal)
            else:
                single_path_groups.setdefault(path_id, []).append(signal)

        for path_id, signals in single_path_groups.items():
            preferred_route = SINGLE_ENTRY_PATH_PREFERRED_ROUTES[path_id]
            winner = next(
                (
                    signal
                    for signal in signals
                    if signal_route(signal) == preferred_route
                ),
                None,
            )
            if winner is None:
                winner = max(
                    signals,
                    key=lambda signal: (
                        _route_priority(signal),
                        _candidate_strength(signal),
                        float(signal.get("score", 0)),
                        str(signal_route(signal) or ""),
                    ),
                )
            selectable.append(winner)
            winner_route = str(signal_route(winner))
            for signal in signals:
                if signal is winner:
                    continue
                signal["preview_only"] = True
                signal["below_threshold"] = True
                signal["trade_eligible"] = False
                signal["effective_score"] = 0.0
                signal["blocked_by"] = (
                    f"SINGLE_ENTRY_PATH:{path_id}:winner={winner_route}"
                )

        return sorted(
            (dict(signal) for signal in selectable),
            key=lambda signal: (
                _route_priority(signal),
                _candidate_strength(signal),
                float(signal.get("score", 0)),
            ),
            reverse=True,
        ), []

    grouped: Dict[str, List[dict]] = {}
    for signal in candidates:
        grouped.setdefault(signal["symbol"], []).append(signal)

    selected: List[dict] = []
    conflicts: List[str] = []
    for symbol, signals in grouped.items():
        directions = {signal["direction"] for signal in signals}
        if len(directions) > 1:
            conflicts.append(symbol)
            continue

        ranked = sorted(
            signals,
            key=lambda signal: (
                _route_priority(signal),
                _candidate_strength(signal),
                float(signal.get("score", 0)),
            ),
            reverse=True,
        )
        winner = dict(ranked[0])
        if len(ranked) > 1:
            winner["confluence_strategies"] = [
                signal.get("strategy_name", "UNKNOWN") for signal in ranked
            ]
        selected.append(winner)

    selected.sort(
        key=lambda signal: (
            _route_priority(signal),
            _candidate_strength(signal),
            float(signal.get("score", 0)),
        ),
        reverse=True,
    )
    return selected, conflicts

def execute_paper(signal: dict) -> Optional[dict]:
    """Queue a signal for the first bar that opens after it was observed."""
    if not route_is_allowed(signal):
        print(f"  CONFIG3: blocked non-whitelisted route {signal_route(signal)}")
        return None
    if not route_is_entry_enabled(signal):
        print(f"  ROUTE ENTRY DISABLED: {signal_route(signal)}")
        return None
    path_block = single_entry_path_reservation_block(signal)
    if path_block:
        print(f"  PORTFOLIO: {path_block}, skip")
        return None
    activation_block = recovery_activation_block(signal)
    if activation_block:
        print(f"  RECOVERY ACTIVATION: {activation_block}")
        return None
    migration_block = recovery_migration_block(signal)
    if migration_block:
        print(f"  RECOVERY MIGRATION: {migration_block}")
        return None
    symbol = signal["symbol"]
    pending = dict(signal)
    pending["max_hold"] = entry_max_hold(pending, 24)
    pending["queued_at"] = now_utc()
    pending["route_id"] = signal_route(pending)
    state.pending_signals[state_key_for_signal(pending)] = pending
    return {"symbol": symbol, "status": "PENDING", **pending}

def _internal_symbol(exchange_symbol: str) -> Optional[str]:
    for internal, exchange in BINGX_MAP.items():
        if exchange == exchange_symbol:
            return internal
    return None

def _position_amount(position: dict) -> float:
    try:
        return abs(float(position.get("positionAmt", position.get("availableAmt", 0)) or 0))
    except (TypeError, ValueError):
        return 0.0

def _live_client_order_id(signal: dict) -> str:
    signal_bar = signal.get("signal_bar_time", signal.get("signal_time", ""))
    identity = "|".join((
        str(signal_route(signal) or signal.get("strategy_name", "UNKNOWN")),
        str(signal.get("symbol", "")),
        str(signal.get("timeframe", "")),
        str(signal.get("direction", "")),
        str(signal_bar),
    ))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"{LIVE_CLIENT_ORDER_PREFIX}-{digest}"

def _live_take_profit(
    signal: dict,
    entry_price: float,
    stop_loss: Optional[float] = None,
) -> float:
    direction = signal["direction"]
    rr = signal.get("risk_reward")
    if rr is None and signal.get("strategy_name", "SMC_MTF_V2") == "SMC_MTF_V2":
        rr = 2.0
    sl = float(signal["sl"] if stop_loss is None else stop_loss)
    if rr is not None:
        risk = abs(entry_price - sl)
        return (
            entry_price + risk * float(rr)
            if direction == "LONG"
            else entry_price - risk * float(rr)
        )
    if signal.get("tp_pct") is not None:
        tp_pct = float(signal["tp_pct"])
        return entry_price * (1 + tp_pct if direction == "LONG" else 1 - tp_pct)
    return float(signal["tp"])

def ensure_max_live_leverage(
    executor: BingXExecutor,
    symbol: str,
    position_side: str,
) -> dict:
    """Set the tracked side to BingX's maximum leverage and cache the profile."""
    side = position_side.upper()
    cache_key = (symbol, side)
    cached = _live_leverage_profiles.get(cache_key)
    if cached is not None:
        return dict(cached)

    leverage_info = executor.get_leverage(symbol)
    side_label = "Long" if side == "LONG" else "Short"
    max_key = f"max{side_label}Leverage"
    current_key = f"{side_label.lower()}Leverage"
    max_value_key = f"maxPosition{side_label}Val"
    try:
        max_leverage = int(float(leverage_info.get(max_key, 0) or 0))
        current_leverage = int(float(leverage_info.get(current_key, 0) or 0))
        max_position_value = float(
            leverage_info.get(max_value_key, math.inf) or math.inf
        )
    except (TypeError, ValueError) as exc:
        raise OrderRejectedError(
            f"Invalid BingX leverage profile for {symbol} {side}"
        ) from exc
    if max_leverage < 1:
        raise OrderRejectedError(f"BingX maximum leverage is unavailable for {symbol}")

    if current_leverage != max_leverage:
        executor.set_leverage(symbol, side, max_leverage)
        print(
            f"  LIVE LEVERAGE {symbol} {side}: "
            f"{current_leverage or '?'}x -> {max_leverage}x"
        )

    profile = {
        "leverage": max_leverage,
        "max_position_value": max_position_value,
    }
    _live_leverage_profiles[cache_key] = profile
    return dict(profile)

def apply_live_margin_guard(plan: dict, balance: dict, leverage_profile: dict) -> dict:
    """Require enough free cross margin after leverage is maximized."""
    try:
        leverage = int(leverage_profile["leverage"])
        available_margin = float(balance.get("available_margin", 0) or 0)
        max_position_value = float(
            leverage_profile.get("max_position_value", math.inf) or math.inf
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise OrderRejectedError("Live margin profile is invalid") from exc
    if leverage < 1:
        raise OrderRejectedError("Live leverage must be positive")
    if not math.isfinite(available_margin) or available_margin <= 0:
        raise OrderRejectedError("BingX available margin is unavailable")

    notional = float(plan["notional"])
    estimated_initial_margin = notional / leverage
    fee_reserve = notional * float(plan["fee_rate"])
    required_margin = estimated_initial_margin + fee_reserve
    margin_budget = available_margin * LIVE_MARGIN_UTILIZATION
    if math.isfinite(max_position_value) and notional > max_position_value:
        raise OrderRejectedError(
            f"Order notional ${notional:.4f} exceeds BingX {plan['position_side']} limit "
            f"${max_position_value:.4f}"
        )
    if required_margin > margin_budget:
        raise OrderRejectedError(
            f"Need ${required_margin:.4f} margin at {leverage}x, "
            f"only ${margin_budget:.4f} is usable"
        )

    guarded = dict(plan)
    guarded.update({
        "exchange_leverage": leverage,
        "available_margin": available_margin,
        "estimated_initial_margin": estimated_initial_margin,
        "fee_reserve": fee_reserve,
        "required_margin": required_margin,
        "margin_budget": margin_budget,
    })
    return guarded

def build_live_order_plan(
    signal: dict,
    executor: BingXExecutor,
    equity: float,
) -> dict:
    """Risk-size an order, allowing only BingX's minimum-size risk override."""
    symbol = signal["symbol"]
    direction = signal["direction"]
    if direction not in ("LONG", "SHORT"):
        raise OrderRejectedError(f"Unsupported live direction: {direction}")
    if not math.isfinite(equity) or equity <= 0:
        raise OrderRejectedError("Live account equity is unavailable")

    price = executor.get_ticker_price(symbol)
    route = signal_route(signal)
    atr = signal_atr(signal) if route is not None else 0.0
    if route is not None and atr <= 0:
        raise OrderRejectedError("ATR is unavailable for the live risk gate")

    buffer = price * LIVE_SLIPPAGE_BUFFER_BPS / 10_000.0
    risk_entry = price + buffer if direction == "LONG" else price - buffer
    sl = float(signal["sl"])
    if signal.get("entry_anchored_barriers"):
        stop_atr_multiple = float(signal.get("stop_atr", 0.0))
        if not math.isfinite(stop_atr_multiple) or stop_atr_multiple <= 0:
            raise OrderRejectedError("Entry-anchored stop ATR multiple is invalid")
        signed = 1.0 if direction == "LONG" else -1.0
        sl = risk_entry - signed * stop_atr_multiple * atr
    if not math.isfinite(sl) or sl <= 0:
        raise OrderRejectedError("Signal stop loss is invalid")
    if direction == "LONG" and not sl < price:
        raise OrderRejectedError("Live price is already at or below the LONG stop")
    if direction == "SHORT" and not sl > price:
        raise OrderRejectedError("Live price is already at or above the SHORT stop")

    if route is not None:
        stop_reference = risk_entry if signal.get("entry_anchored_barriers") else price
        stop_atr = abs(stop_reference - sl) / atr
        if stop_atr < MIN_STOP_ATR:
            raise OrderRejectedError(
                f"Live stop {stop_atr:.3f} ATR is below {MIN_STOP_ATR:.2f} ATR"
            )

    raw_tp = _live_take_profit(signal, risk_entry, sl)
    if not math.isfinite(raw_tp) or raw_tp <= 0:
        raise OrderRejectedError("Live take profit is invalid")
    if direction == "LONG" and not raw_tp > price:
        raise OrderRejectedError("Live LONG take profit is not above market")
    if direction == "SHORT" and not raw_tp < price:
        raise OrderRejectedError("Live SHORT take profit is not below market")

    contract = executor.get_contract(symbol)
    fee_rate = float(contract.get("takerFeeRate", 0.0005) or 0.0005)
    stop_rounding = "up" if direction == "LONG" else "down"
    tp_rounding = "down" if direction == "LONG" else "up"
    rounded_sl = float(executor.format_price(symbol, sl, stop_rounding))
    rounded_tp = float(executor.format_price(symbol, raw_tp, tp_rounding))
    if direction == "LONG" and not rounded_sl < price < rounded_tp:
        raise OrderRejectedError("Rounded LONG protection is invalid")
    if direction == "SHORT" and not rounded_tp < price < rounded_sl:
        raise OrderRejectedError("Rounded SHORT protection is invalid")

    risk_budget = live_risk_budget(equity)
    if risk_budget <= 0:
        raise OrderRejectedError("Live risk budget is unavailable")
    risk_per_unit = (
        abs(risk_entry - rounded_sl) + risk_entry * fee_rate * 2.0
    )
    if risk_per_unit <= 0:
        raise OrderRejectedError("Live per-unit risk is invalid")
    risk_quantity = risk_budget / risk_per_unit
    try:
        floor_quantity = float(executor.format_quantity(symbol, risk_quantity))
    except OrderRejectedError:
        floor_quantity = 0.0
    minimum_quantity = executor.minimum_order_quantity(symbol, risk_entry)
    minimum_adjustment = floor_quantity + 1e-15 < minimum_quantity
    quantity = minimum_quantity if minimum_adjustment else floor_quantity
    quantity = executor.validate_quantity(symbol, quantity, risk_entry)

    total_risk = quantity * (
        abs(risk_entry - rounded_sl) + risk_entry * fee_rate * 2.0
    )
    notional = quantity * risk_entry
    risk_exceeds_budget = total_risk > risk_budget * 1.000001
    minimum_override = (
        LIVE_MINIMUM_ORDER_RISK_OVERRIDE
        and minimum_adjustment
        and risk_exceeds_budget
    )
    if risk_exceeds_budget and not minimum_override:
        label = "BingX minimum order" if minimum_adjustment else "Rounded live order"
        raise OrderRejectedError(
            f"{label} risk ${total_risk:.4f} exceeds strict ${risk_budget:.2f} limit"
        )
    risk_over_budget = max(0.0, total_risk - risk_budget)

    return {
        "symbol": symbol,
        "exchange_symbol": executor.map_symbol(symbol),
        "direction": direction,
        "side": "BUY" if direction == "LONG" else "SELL",
        "position_side": direction,
        "price": price,
        "risk_entry": risk_entry,
        "quantity": quantity,
        "sl": rounded_sl,
        "tp": rounded_tp,
        "risk_budget": risk_budget,
        "planned_risk": total_risk,
        "minimum_quantity": minimum_quantity,
        "minimum_adjustment": minimum_adjustment,
        "minimum_override": minimum_override,
        "risk_over_budget": risk_over_budget,
        "risk_utilization": total_risk / risk_budget,
        "notional": notional,
        "fee_rate": fee_rate,
    }

def _matching_live_position(symbol: str, position_side: str) -> Optional[dict]:
    if live_executor is None:
        return None
    for position in live_executor.get_positions(symbol):
        if (
            str(position.get("positionSide", "")).upper() == position_side.upper()
            and _position_amount(position) > 0
        ):
            return position
    return None

def _live_fill_details(
    symbol: str,
    position_side: str,
    order_row: dict,
    planned_quantity: float,
    previous_position_amount: float = 0.0,
) -> Tuple[str, float, float]:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    order_id = str(order_row.get("orderId", order_row.get("orderID", "")))
    latest = dict(order_row)
    for _ in range(6):
        price = float(latest.get("avgPrice", latest.get("price", 0)) or 0)
        quantity = float(
            latest.get("executedQty", latest.get("cumQty", 0)) or 0
        )
        if price > 0 and quantity > 0:
            return order_id, price, quantity
        if order_id:
            try:
                latest = live_executor.get_order(symbol, order_id=order_id)
            except OrderRejectedError:
                pass
        position = _matching_live_position(symbol, position_side)
        if position is not None:
            price = float(position.get("avgPrice", 0) or 0)
            if previous_position_amount > 0:
                price = live_executor.get_ticker_price(symbol)
            quantity = max(
                0.0,
                _position_amount(position) - float(previous_position_amount),
            )
            if price > 0 and quantity > 0:
                return order_id, price, quantity
        time.sleep(0.5)
    position = _matching_live_position(symbol, position_side)
    if position is None:
        raise RuntimeError(f"BingX did not confirm the live position for {symbol}")
    price = float(position.get("avgPrice", 0) or 0)
    if previous_position_amount > 0:
        price = live_executor.get_ticker_price(symbol)
    quantity = max(
        0.0,
        _position_amount(position) - float(previous_position_amount),
    ) or planned_quantity
    if price <= 0:
        price = live_executor.get_ticker_price(symbol)
    return order_id, price, quantity

def _protection_from_orders(
    orders: List[dict],
    symbol: str,
    position_side: str,
) -> Dict[str, str]:
    protection: Dict[str, str] = {}
    for order in orders:
        if _internal_symbol(str(order.get("symbol", ""))) != symbol:
            continue
        if str(order.get("positionSide", "")).upper() != position_side.upper():
            continue
        order_type = str(order.get("type", order.get("orderType", ""))).upper()
        if order_type == "STOP_MARKET":
            protection["stop_order_id"] = str(order.get("orderId", ""))
        elif order_type == "TAKE_PROFIT_MARKET":
            protection["take_profit_order_id"] = str(order.get("orderId", ""))
    return protection

def _protection_for_intent(orders: List[dict], intent: dict) -> Dict[str, str]:
    symbol = str(intent.get("symbol", ""))
    position_side = str(intent.get("direction", "")).upper()
    quantity = float(
        intent.get("filled_quantity", intent.get("quantity", 0)) or 0
    )
    targets = {
        "STOP_MARKET": ("stop_order_id", float(intent.get("sl", 0) or 0)),
        "TAKE_PROFIT_MARKET": (
            "take_profit_order_id",
            float(intent.get("tp", 0) or 0),
        ),
    }
    matches: Dict[str, List[str]] = {field: [] for field, _ in targets.values()}
    for order in orders:
        if _internal_symbol(str(order.get("symbol", ""))) != symbol:
            continue
        if str(order.get("positionSide", "")).upper() != position_side:
            continue
        order_type = str(order.get("type", order.get("orderType", ""))).upper()
        target = targets.get(order_type)
        if target is None:
            continue
        field, target_price = target
        try:
            order_price = float(order.get("stopPrice", 0) or 0)
            order_quantity = float(
                order.get("origQty", order.get("quantity", 0)) or 0
            )
        except (TypeError, ValueError):
            continue
        price_tolerance = max(1e-12, abs(target_price) * 1e-8)
        quantity_tolerance = max(1e-12, abs(quantity) * 1e-6)
        if (
            abs(order_price - target_price) <= price_tolerance
            and abs(order_quantity - quantity) <= quantity_tolerance
        ):
            order_id = _order_id(order)
            if order_id:
                matches[field].append(order_id)
    if any(len(values) != 1 for values in matches.values()):
        return {}
    return {field: values[0] for field, values in matches.items()}

def _wait_for_live_protection(symbol: str, position_side: str) -> Dict[str, str]:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    for _ in range(10):
        protection = _protection_from_orders(
            live_executor.get_open_orders(symbol),
            symbol,
            position_side,
        )
        if protection.get("stop_order_id") and protection.get("take_profit_order_id"):
            return protection
        time.sleep(0.5)
    return {}

def _order_id(order: dict) -> str:
    return str(order.get("orderId", order.get("orderID", "")))

def _cancel_live_order_with_history(
    order_id: str,
    symbol: str,
    *,
    order_role: str,
    reason: str,
) -> bool:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    cancelled = live_executor.cancel_order(order_id, symbol=symbol)
    if cancelled:
        _append_live_order_history(
            "ORDER_CANCELLED",
            order_role=order_role,
            symbol=symbol,
            exchange_order_id=order_id,
            reason=reason,
        )
    return cancelled

def _place_live_protection(
    symbol: str,
    position_side: str,
    quantity: float,
    stop_loss: float,
    take_profit: float,
    *,
    parent_client_order_id: Optional[str] = None,
    route_id: Optional[str] = None,
) -> Dict[str, str]:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    close_side = "SELL" if position_side == "LONG" else "BUY"
    created: Dict[str, str] = {}
    try:
        stop_row = live_executor.submit_conditional_order(
            symbol=symbol,
            side=close_side,
            position_side=position_side,
            quantity=quantity,
            stop_price=stop_loss,
            order_type="STOP_MARKET",
        )
        created["stop_order_id"] = _order_id(stop_row)
        if not created["stop_order_id"]:
            raise RuntimeError("BingX did not return the stop order ID")
        _append_live_order_history(
            "ORDER_SUBMITTED",
            order_role="STOP_LOSS",
            symbol=symbol,
            route_id=route_id,
            parent_client_order_id=parent_client_order_id,
            exchange_order_id=created["stop_order_id"],
            order_type="STOP_MARKET",
            side=close_side,
            position_side=position_side,
            quantity=quantity,
            stop_price=stop_loss,
        )
        tp_row = live_executor.submit_conditional_order(
            symbol=symbol,
            side=close_side,
            position_side=position_side,
            quantity=quantity,
            stop_price=take_profit,
            order_type="TAKE_PROFIT_MARKET",
        )
        created["take_profit_order_id"] = _order_id(tp_row)
        if not created["take_profit_order_id"]:
            raise RuntimeError("BingX did not return the take-profit order ID")
        _append_live_order_history(
            "ORDER_SUBMITTED",
            order_role="TAKE_PROFIT",
            symbol=symbol,
            route_id=route_id,
            parent_client_order_id=parent_client_order_id,
            exchange_order_id=created["take_profit_order_id"],
            order_type="TAKE_PROFIT_MARKET",
            side=close_side,
            position_side=position_side,
            quantity=quantity,
            stop_price=take_profit,
        )
        return created
    except Exception:
        for order_id in created.values():
            if not order_id:
                continue
            try:
                _cancel_live_order_with_history(
                    order_id,
                    symbol,
                    order_role="PROTECTION",
                    reason="protection setup failed",
                )
            except Exception:
                pass
        raise

def _wait_for_protection_ids(
    symbol: str,
    protection: Dict[str, str],
) -> bool:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    expected = {value for value in protection.values() if value}
    for _ in range(10):
        visible = {_order_id(order) for order in live_executor.get_open_orders(symbol)}
        if expected and expected.issubset(visible):
            return True
        time.sleep(0.5)
    return False

def _emergency_close_live_position(
    symbol: str,
    position_side: str,
    quantity: float,
    reason: str,
) -> None:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    position = _matching_live_position(symbol, position_side)
    if position is None:
        return
    before_amount = _position_amount(position)
    close_quantity = min(quantity, before_amount)
    close_side = "SELL" if position_side == "LONG" else "BUY"
    close_id = f"{LIVE_CLIENT_ORDER_PREFIX}-safe-{int(time.time() * 1000)}"
    order_row = live_executor.submit_market_order(
        symbol=symbol,
        side=close_side,
        position_side=position_side,
        quantity=close_quantity,
        client_order_id=close_id,
    )
    _append_live_order_history(
        "ORDER_SUBMITTED",
        order_role="EMERGENCY_CLOSE",
        symbol=symbol,
        client_order_id=close_id,
        exchange_order_id=_order_id(order_row),
        order_type="MARKET",
        side=close_side,
        position_side=position_side,
        quantity=close_quantity,
        reason=reason,
    )
    expected_remaining = max(0.0, before_amount - close_quantity)
    tolerance = max(1e-12, close_quantity * 1e-6)
    for _ in range(10):
        current = _matching_live_position(symbol, position_side)
        current_amount = _position_amount(current) if current is not None else 0.0
        if current_amount <= expected_remaining + tolerance:
            return
        time.sleep(0.5)
    raise RuntimeError(f"Emergency close failed for {symbol}: {reason}")

def _live_intent(signal: dict, plan: dict, client_order_id: str) -> dict:
    return {
        "client_order_id": client_order_id,
        "status": "PREPARED",
        "symbol": plan["symbol"],
        "exchange_symbol": plan["exchange_symbol"],
        "strategy_name": signal.get("strategy_name", "SMC_MTF_V2"),
        "route_id": signal_route(signal),
        "timeframe": signal.get("timeframe", LTF_TF.value),
        "direction": plan["direction"],
        "signal_time": signal.get("signal_time"),
        "decision_time": signal.get("decision_time"),
        "signal_bar_time": signal.get("signal_bar_time"),
        "created_at": now_utc(),
        "sl": plan["sl"],
        "tp": plan["tp"],
        "quantity": plan["quantity"],
        "risk_budget": plan["risk_budget"],
        "planned_risk": plan["planned_risk"],
        "minimum_adjustment": plan.get("minimum_adjustment", False),
        "minimum_override": plan.get("minimum_override", False),
        "risk_over_budget": plan.get("risk_over_budget", 0.0),
        "fee_rate": plan["fee_rate"],
        "exchange_leverage": plan["exchange_leverage"],
        "estimated_initial_margin": plan["estimated_initial_margin"],
        "available_margin": plan["available_margin"],
        "max_hold": entry_max_hold(signal, 24),
        "score": signal.get("score", 0),
        "reasons": signal.get("reasons", ""),
        "confluence_strategies": signal.get("confluence_strategies", []),
    }

def _trade_from_live_intent(
    intent: dict,
    entry_price: float,
    quantity: float,
    order_id: str,
    protection: Optional[Dict[str, str]] = None,
) -> dict:
    entry_time = now_utc()
    trade = {
        "symbol": intent["symbol"],
        "strategy_name": intent.get("strategy_name", "SMC_MTF_V2"),
        "route_id": intent.get("route_id") or strategy_route_id(
            str(intent.get("strategy_name", "SMC_MTF_V2")),
            str(intent["symbol"]),
            intent.get("timeframe"),
        ),
        "timeframe": intent.get("timeframe", LTF_TF.value),
        "direction": intent["direction"],
        "signal_time": AutoTradeState._parse_datetime(intent.get("signal_time")),
        "decision_time": AutoTradeState._parse_datetime(intent.get("decision_time")),
        "signal_bar_time": AutoTradeState._parse_datetime(intent.get("signal_bar_time")),
        "execution_time": entry_time,
        "entry_time": entry_time,
        "entry_price": entry_price,
        "entry_commission": quantity * entry_price * float(intent.get("fee_rate", 0.0005)),
        "fee_rate": float(intent.get("fee_rate", 0.0005)),
        "sl": float(intent["sl"]),
        "exchange_sl": float(intent["sl"]),
        "tp": float(intent["tp"]),
        "size": quantity,
        "status": "OPEN",
        "score": intent.get("score", 0),
        "reasons": intent.get("reasons", ""),
        "confluence_strategies": intent.get("confluence_strategies", []),
        "bars_held": 0,
        "max_hold": entry_max_hold(intent, 24),
        "last_processed_bar": None,
        "risk_budget": float(intent.get("risk_budget", 0)),
        "planned_risk": float(intent.get("planned_risk", 0)),
        "minimum_adjustment": bool(intent.get("minimum_adjustment", False)),
        "minimum_override": bool(intent.get("minimum_override", False)),
        "risk_over_budget": float(intent.get("risk_over_budget", 0)),
        "initial_risk_amount": quantity * abs(entry_price - float(intent["sl"])),
        "entry_leverage": quantity * entry_price / max(state.paper_equity, 1e-12),
        "exchange_leverage": int(intent.get("exchange_leverage", 1)),
        "estimated_initial_margin": float(
            intent.get("estimated_initial_margin", 0)
        ),
        "min_stop_atr": MIN_STOP_ATR,
        "live": True,
        "client_order_id": intent["client_order_id"],
        "exchange_order_id": order_id,
        **(protection or {}),
    }
    _ensure_smc_trailing_state(trade)
    return trade

def execute_live(signal: dict) -> Optional[dict]:
    if not ENTRY_ENABLED:
        print(f"  ENTRY LOCK: skip live entry for {signal.get('symbol', 'UNKNOWN')}")
        return None
    if not route_is_entry_enabled(signal):
        print(f"  ROUTE ENTRY DISABLED: {signal_route(signal)}")
        return None
    activation_block = recovery_activation_block(signal)
    if activation_block:
        print(f"  RECOVERY ACTIVATION: {activation_block}")
        return None
    migration_block = recovery_migration_block(signal)
    if migration_block:
        print(f"  RECOVERY MIGRATION: {migration_block}")
        return None
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    if not route_is_live_approved(signal):
        print(f"  LIVE APPROVAL BLOCK: {signal_route(signal)}")
        return None
    symbol = signal["symbol"]
    position_key = state_key_for_signal(signal)
    path_block = single_entry_path_reservation_block(signal)
    if path_block:
        print(f"  LIVE: {path_block}, skip")
        return None
    if route_is_reserved(signal):
        print(f"  LIVE: {position_key} already exists on BingX/state, skip")
        return None
    external_block = _external_side_block(symbol, signal.get("direction"))
    if external_block:
        print(f"  LIVE: {external_block}, skip")
        return None

    client_order_id = _live_client_order_id(signal)
    existing_intent = state.order_intents.get(client_order_id)
    if existing_intent and existing_intent.get("status") not in ("REJECTED", "FAILED"):
        print(f"  LIVE: duplicate intent {client_order_id}, skip")
        return None

    try:
        balance = live_executor.get_balance()
        equity = float(balance.get("equity", 0))
        state.paper_equity = equity
        plan = build_live_order_plan(signal, live_executor, equity)
        leverage_profile = ensure_max_live_leverage(
            live_executor,
            symbol,
            plan["position_side"],
        )
        plan = apply_live_margin_guard(plan, balance, leverage_profile)
    except (MarginError, OrderRejectedError, RateLimitExchangeError) as exc:
        error_text = _safe_exception_text(exc)
        print(f"  LIVE: skip {symbol}: {error_text}")
        tg.report_error(symbol, f"LIVE SKIP: {error_text}")
        return None

    if plan.get("minimum_adjustment"):
        if plan.get("minimum_override"):
            override_message = (
                f"minimum quantity={plan['quantity']:g} requires "
                f"risk=${plan['planned_risk']:.4f} > target=${plan['risk_budget']:.2f} "
                f"by ${plan['risk_over_budget']:.4f}"
            )
            print(f"  LIVE MINIMUM RISK OVERRIDE {symbol}: {override_message}")
            tg.report_error(symbol, f"LIVE MINIMUM RISK OVERRIDE: {override_message}")
        else:
            print(
                f"  LIVE MINIMUM ADJUSTMENT {symbol}: quantity={plan['quantity']:g}, "
                f"risk=${plan['planned_risk']:.4f} <= limit=${plan['risk_budget']:.2f}"
            )
    print(
        f"  LIVE MARGIN {symbol}: {plan['exchange_leverage']}x | "
        f"required=${plan['required_margin']:.4f} | "
        f"available=${plan['available_margin']:.4f} | "
        f"risk=${plan['planned_risk']:.4f}"
    )

    intent = _live_intent(signal, plan, client_order_id)
    _append_live_order_history(
        "ORDER_INTENT_CREATED",
        required=True,
        order_role="ENTRY",
        symbol=symbol,
        exchange_symbol=plan["exchange_symbol"],
        strategy_name=intent["strategy_name"],
        route_id=intent["route_id"],
        timeframe=intent["timeframe"],
        client_order_id=client_order_id,
        order_type="MARKET",
        side=plan["side"],
        position_side=plan["position_side"],
        quantity=plan["quantity"],
        stop_loss=plan["sl"],
        take_profit=plan["tp"],
        risk_budget=plan["risk_budget"],
        planned_risk=plan["planned_risk"],
        minimum_adjustment=plan.get("minimum_adjustment", False),
        minimum_override=plan.get("minimum_override", False),
        risk_over_budget=plan.get("risk_over_budget", 0.0),
    )
    state.order_intents[client_order_id] = intent
    state.save()

    try:
        previous_position = _matching_live_position(symbol, plan["position_side"])
        previous_position_amount = (
            _position_amount(previous_position) if previous_position is not None else 0.0
        )
        live_executor.submit_market_order(
            symbol=symbol,
            side=plan["side"],
            position_side=plan["position_side"],
            quantity=plan["quantity"],
            client_order_id=f"{client_order_id}-t",
            test=True,
        )
        intent["status"] = "TESTED"
        state.save()

        # Recheck only untracked exposure. Existing route legs and their
        # quantity-scoped protection orders may share this symbol.
        external_block = _external_side_block(symbol, plan["position_side"])
        if external_block:
            intent["status"] = "REJECTED"
            intent["error"] = external_block
            state.save()
            print(f"  LIVE: {external_block}, skip")
            return None

        order_row = live_executor.submit_market_order(
            symbol=symbol,
            side=plan["side"],
            position_side=plan["position_side"],
            quantity=plan["quantity"],
            client_order_id=client_order_id,
        )
        intent["status"] = "SUBMITTED"
        intent["order_id"] = str(order_row.get("orderId", order_row.get("orderID", "")))
        state.save()
        _append_live_order_history(
            "ORDER_SUBMITTED",
            order_role="ENTRY",
            symbol=symbol,
            exchange_symbol=plan["exchange_symbol"],
            strategy_name=intent["strategy_name"],
            route_id=intent["route_id"],
            client_order_id=client_order_id,
            exchange_order_id=intent["order_id"],
            order_type="MARKET",
            side=plan["side"],
            position_side=plan["position_side"],
            quantity=plan["quantity"],
        )

        order_id, entry_price, filled_quantity = _live_fill_details(
            symbol,
            plan["position_side"],
            order_row,
            plan["quantity"],
            previous_position_amount,
        )
        try:
            protection = _place_live_protection(
                symbol,
                plan["position_side"],
                filled_quantity,
                plan["sl"],
                plan["tp"],
                parent_client_order_id=client_order_id,
                route_id=intent["route_id"],
            )
            intent.update(protection)
            state.save()
        except Exception as exc:
            error_text = _safe_exception_text(exc)
            _emergency_close_live_position(
                symbol,
                plan["position_side"],
                filled_quantity,
                f"route SL/TP placement failed: {error_text}",
            )
            intent["status"] = "FAILED"
            intent["error"] = (
                f"route SL/TP placement failed; entry closed: {error_text}"
            )
            state.save()
            _append_live_order_history(
                "ORDER_FAILED",
                order_role="ENTRY",
                symbol=symbol,
                route_id=intent.get("route_id"),
                client_order_id=client_order_id,
                exchange_order_id=intent.get("order_id"),
                reason=intent["error"],
            )
            raise RuntimeError(f"LIVE {position_key} closed because SL/TP failed") from exc
        if not _wait_for_protection_ids(symbol, protection):
            for child_order_id in protection.values():
                try:
                    _cancel_live_order_with_history(
                        child_order_id,
                        symbol,
                        order_role="PROTECTION",
                        reason="protection not visible",
                    )
                except Exception:
                    pass
            _emergency_close_live_position(
                symbol,
                plan["position_side"],
                filled_quantity,
                "route SL/TP not visible",
            )
            intent["status"] = "FAILED"
            intent["error"] = "route SL/TP not visible; entry closed"
            state.save()
            _append_live_order_history(
                "ORDER_FAILED",
                order_role="ENTRY",
                symbol=symbol,
                route_id=intent.get("route_id"),
                client_order_id=client_order_id,
                exchange_order_id=intent.get("order_id"),
                reason=intent["error"],
            )
            raise RuntimeError(f"LIVE {position_key} closed because SL/TP was not confirmed")

        actual_risk = filled_quantity * (
            abs(entry_price - plan["sl"]) + entry_price * plan["fee_rate"] * 2.0
        )
        allowed_fill_risk = live_fill_risk_limit(plan)
        if actual_risk > allowed_fill_risk:
            for child_order_id in protection.values():
                try:
                    _cancel_live_order_with_history(
                        child_order_id,
                        symbol,
                        order_role="PROTECTION",
                        reason="post-fill risk exceeded",
                    )
                except Exception:
                    pass
            _emergency_close_live_position(
                symbol,
                plan["position_side"],
                filled_quantity,
                "post-fill risk exceeded",
            )
            intent["status"] = "FAILED"
            intent["error"] = "post-fill risk exceeded; entry closed"
            state.save()
            _append_live_order_history(
                "ORDER_FAILED",
                order_role="ENTRY",
                symbol=symbol,
                route_id=intent.get("route_id"),
                client_order_id=client_order_id,
                exchange_order_id=intent.get("order_id"),
                reason=intent["error"],
            )
            raise RuntimeError(f"LIVE {symbol} closed after post-fill risk validation")

        trade = _trade_from_live_intent(
            intent,
            entry_price,
            filled_quantity,
            order_id,
            protection,
        )
        intent["status"] = "FILLED"
        intent["filled_at"] = now_utc()
        intent["fill_price"] = entry_price
        intent["filled_quantity"] = filled_quantity
        state.positions[position_key] = trade
        state.save()
        _append_live_order_history(
            "ORDER_FILLED",
            order_role="ENTRY",
            symbol=symbol,
            strategy_name=intent["strategy_name"],
            route_id=intent["route_id"],
            client_order_id=client_order_id,
            exchange_order_id=order_id,
            position_side=plan["position_side"],
            quantity=filled_quantity,
            fill_price=entry_price,
            stop_order_id=protection.get("stop_order_id"),
            take_profit_order_id=protection.get("take_profit_order_id"),
        )
        tg.report_trade_open(trade)
        return trade
    except (MarginError, OrderRejectedError, RateLimitExchangeError) as exc:
        error_text = _safe_exception_text(exc)
        intent["status"] = "REJECTED"
        intent["error"] = error_text
        state.save()
        _append_live_order_history(
            "ORDER_REJECTED",
            order_role="ENTRY",
            symbol=symbol,
            route_id=intent.get("route_id"),
            client_order_id=client_order_id,
            reason=error_text,
        )
        print(f"  LIVE: BingX rejected {symbol}: {error_text}")
        tg.report_error(symbol, f"LIVE REJECTED: {error_text}")
        return None
    except Exception as exc:
        if intent.get("status") not in ("FAILED", "FILLED"):
            error_text = _safe_exception_text(exc)
            intent["status"] = "UNKNOWN"
            intent["error"] = error_text
            state.save()
            _append_live_order_history(
                "ORDER_STATUS_UNKNOWN",
                order_role="ENTRY",
                symbol=symbol,
                route_id=intent.get("route_id"),
                client_order_id=client_order_id,
                exchange_order_id=intent.get("order_id"),
                reason=error_text,
            )
        raise

def _execution_for(symbol: str) -> ExecutionSimulator:
    ac = SYMBOLS.get(symbol, AssetClass.CRYPTO)
    if ac == AssetClass.FOREX:
        return ExecutionSimulator(slippage_bps=0.2, commission_bps=0.2, spread_bps=0.3, latency_ms=200, random_seed=42)
    if ac == AssetClass.COMMODITY:
        return ExecutionSimulator(slippage_bps=0.5, commission_bps=0.4, spread_bps=2.0, latency_ms=200, random_seed=42)
    return ExecutionSimulator(slippage_bps=0.5, commission_bps=0.4, spread_bps=1.0, latency_ms=200, random_seed=42)

def _prior_liquidity(series: BarSeries, idx: int, default: float = 1_000_000.0) -> float:
    values = [c.volume for c in series.candles[max(0, idx - 20):idx] if c.volume > 0]
    return float(np.median(values)) if values else default

def _active_exchange_positions(rows: List[dict]) -> List[dict]:
    return [row for row in rows if _position_amount(row) > 0]

def _record_live_close(
    position: dict,
    exit_price: float,
    reason: str,
    position_key: Optional[str] = None,
    *,
    close_order_id: Optional[str] = None,
    close_client_order_id: Optional[str] = None,
) -> None:
    symbol = position["symbol"]
    position_key = position_key or state_key_for_position(position, symbol)
    direction = position["direction"]
    quantity = float(position["size"])
    fee_rate = float(position.get("fee_rate", 0.0005))
    exit_commission = quantity * exit_price * fee_rate
    gross = (
        (exit_price - float(position["entry_price"])) * quantity
        if direction == "LONG"
        else (float(position["entry_price"]) - exit_price) * quantity
    )
    pnl = gross - float(position.get("entry_commission", 0)) - exit_commission
    position["status"] = "CLOSED"
    position["exit_time"] = now_utc()
    position["exit_price"] = exit_price
    position["exit_commission"] = exit_commission
    position["pnl"] = pnl
    position["exit_reason"] = reason
    state.total_pnl += pnl
    state.trade_log.append(position)
    state.positions.pop(position_key, None)
    client_order_id = position.get("client_order_id")
    if client_order_id in state.order_intents:
        state.order_intents[client_order_id]["status"] = "CLOSED"
        state.order_intents[client_order_id]["closed_at"] = now_utc()
        state.order_intents[client_order_id]["exit_reason"] = reason
    if live_executor is not None:
        try:
            state.paper_equity = live_executor.get_balance()["equity"]
        except Exception:
            pass
    state.save()
    if close_order_id is None:
        if "SL" in reason:
            close_order_id = position.get("stop_order_id")
        elif "TP" in reason:
            close_order_id = position.get("take_profit_order_id")
    _append_live_order_history(
        "POSITION_CLOSED",
        order_role="EXIT",
        symbol=symbol,
        strategy_name=position.get("strategy_name"),
        route_id=position.get("route_id"),
        client_order_id=close_client_order_id,
        parent_client_order_id=position.get("client_order_id"),
        exchange_order_id=close_order_id,
        position_side=direction,
        quantity=quantity,
        exit_price=exit_price,
        pnl=pnl,
        reason=reason,
    )
    tg.report_trade_close(position, state.paper_equity, reason)
    print(
        f"\n  === LIVE CLOSE {symbol} | {reason} | "
        f"PnL~${pnl:+,.4f} | Equity=${state.paper_equity:,.4f} ==="
    )

def close_live_position(position_key: str, reason: str) -> bool:
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")
    position = state.positions.get(position_key)
    if position is None or position.get("status") != "OPEN":
        return False
    symbol = str(position["symbol"])
    position_side = position["direction"]
    exchange_position = _matching_live_position(symbol, position_side)
    if exchange_position is None:
        exit_price = live_executor.get_ticker_price(symbol)
        _record_live_close(
            position,
            exit_price,
            f"EXCHANGE_CLOSED:{reason}",
            position_key,
        )
        return True

    before_amount = _position_amount(exchange_position)
    quantity = min(float(position["size"]), before_amount)
    close_side = "SELL" if position_side == "LONG" else "BUY"
    identity = f"{position.get('client_order_id', symbol)}|{reason}|{position.get('bars_held', 0)}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:18]
    close_client_id = f"{LIVE_CLIENT_ORDER_PREFIX}-x-{digest}"
    order_row = live_executor.submit_market_order(
        symbol=symbol,
        side=close_side,
        position_side=position_side,
        quantity=quantity,
        client_order_id=close_client_id,
    )
    order_id = str(order_row.get("orderId", order_row.get("orderID", "")))
    _append_live_order_history(
        "ORDER_SUBMITTED",
        order_role="EXIT",
        symbol=symbol,
        strategy_name=position.get("strategy_name"),
        route_id=position.get("route_id"),
        client_order_id=close_client_id,
        parent_client_order_id=position.get("client_order_id"),
        exchange_order_id=order_id,
        order_type="MARKET",
        side=close_side,
        position_side=position_side,
        quantity=quantity,
        reason=reason,
    )
    exit_price = float(order_row.get("avgPrice", order_row.get("price", 0)) or 0)
    expected_remaining = max(0.0, before_amount - quantity)
    tolerance = max(1e-12, quantity * 1e-6)
    for _ in range(10):
        if order_id and exit_price <= 0:
            try:
                latest = live_executor.get_order(symbol, order_id=order_id)
                exit_price = float(latest.get("avgPrice", latest.get("price", 0)) or 0)
            except OrderRejectedError:
                pass
        remaining = _matching_live_position(symbol, position_side)
        remaining_amount = _position_amount(remaining) if remaining is not None else 0.0
        if remaining_amount <= expected_remaining + tolerance:
            break
        time.sleep(0.5)
    else:
        raise RuntimeError(f"BingX did not close {symbol} for {reason}")
    if exit_price <= 0:
        exit_price = live_executor.get_ticker_price(symbol)

    # Attached child orders normally cancel with the position. Cancel only the
    # two order IDs captured for this bot-owned trade if they remain open.
    for key in ("stop_order_id", "take_profit_order_id"):
        child_order_id = position.get(key)
        if not child_order_id:
            continue
        try:
            _cancel_live_order_with_history(
                str(child_order_id),
                symbol,
                order_role=(
                    "STOP_LOSS" if key == "stop_order_id" else "TAKE_PROFIT"
                ),
                reason=f"position closed: {reason}",
            )
        except Exception:
            pass

    _record_live_close(
        position,
        exit_price,
        reason,
        position_key,
        close_order_id=order_id,
        close_client_order_id=close_client_id,
    )
    return True

def _live_order_status(symbol: str, order_id: Optional[str]) -> str:
    if live_executor is None or not order_id:
        return "UNKNOWN"
    try:
        row = live_executor.get_order(symbol, order_id=str(order_id))
    except Exception:
        return "UNKNOWN"
    return str(row.get("status", row.get("state", "UNKNOWN"))).upper()

def reconcile_live_account() -> None:
    """Reconcile route legs against BingX's aggregated symbol-side positions."""
    global external_reservations
    if live_executor is None:
        raise RuntimeError("Live executor is not initialized")

    balance = live_executor.get_balance()
    equity = float(balance.get("equity", 0))
    if not math.isfinite(equity) or equity <= 0:
        raise RuntimeError("BingX live equity is unavailable")
    state.paper_equity = equity
    exchange_positions = _active_exchange_positions(live_executor.get_positions())
    exchange_orders = live_executor.get_open_orders()
    open_orders_by_id = {
        _order_id(order): order for order in exchange_orders if _order_id(order)
    }

    by_symbol_side: Dict[Tuple[str, str], dict] = {}
    for exchange_position in exchange_positions:
        internal = _internal_symbol(str(exchange_position.get("symbol", "")))
        if internal:
            key = (
                internal,
                str(exchange_position.get("positionSide", "")).upper(),
            )
            by_symbol_side[key] = exchange_position

    changed = False
    tracked_groups: Dict[Tuple[str, str], List[Tuple[str, dict]]] = {}
    for position_key, position in state.positions.items():
        group = (
            str(position.get("symbol", "")),
            str(position.get("direction", "")).upper(),
        )
        tracked_groups.setdefault(group, []).append((position_key, position))

    # Recover an order submitted immediately before a process restart. Exact
    # route quantity and child IDs are persisted in the intent when available.
    for client_order_id, intent in list(state.order_intents.items()):
        if intent.get("status") not in ("SUBMITTED", "UNKNOWN"):
            continue
        position_key = state_key_for_signal(intent)
        if position_key in state.positions:
            continue
        symbol = str(intent.get("symbol", ""))
        direction = str(intent.get("direction", "")).upper()
        exchange_position = by_symbol_side.get((symbol, direction))
        if not symbol or exchange_position is None:
            continue
        protection = {
            key: str(intent.get(key, ""))
            for key in ("stop_order_id", "take_profit_order_id")
            if intent.get(key)
        }
        if len(protection) < 2:
            protection = _protection_for_intent(exchange_orders, intent)
        if len(protection) < 2:
            existing_group = tracked_groups.get((symbol, direction), [])
            if not existing_group:
                protection = _protection_from_orders(
                    exchange_orders,
                    symbol,
                    direction,
                )
        if len(protection) < 2 or not set(protection.values()).issubset(open_orders_by_id):
            quantity = float(intent.get("filled_quantity", intent.get("quantity", 0)) or 0)
            if quantity > 0:
                _emergency_close_live_position(
                    symbol,
                    direction,
                    quantity,
                    "restart recovery found no route SL/TP",
                )
            intent["status"] = "FAILED"
            intent["error"] = "restart recovery found no route SL/TP; leg closed"
            changed = True
            continue
        try:
            order = live_executor.get_order(
                symbol,
                order_id=str(intent.get("order_id", "")),
            )
        except Exception:
            order = {}
        entry_price = float(
            order.get("avgPrice", intent.get("fill_price", 0)) or 0
        )
        quantity = float(
            order.get(
                "executedQty",
                intent.get("filled_quantity", intent.get("quantity", 0)),
            )
            or 0
        )
        if entry_price <= 0:
            entry_price = live_executor.get_ticker_price(symbol)
        if quantity <= 0:
            continue
        trade = _trade_from_live_intent(
            intent,
            entry_price,
            quantity,
            str(intent.get("order_id", "")),
            protection,
        )
        state.positions[position_key] = trade
        tracked_groups.setdefault((symbol, direction), []).append(
            (position_key, trade)
        )
        intent["status"] = "FILLED"
        intent["recovered_at"] = now_utc()
        changed = True

    # Detect route-level exchange protection fills before comparing aggregate
    # quantities. The sibling child is cancelled after either SL or TP fills.
    for position_key, position in list(state.positions.items()):
        symbol = str(position.get("symbol", ""))
        stop_id = str(position.get("stop_order_id", ""))
        tp_id = str(position.get("take_profit_order_id", ""))
        stop_open = bool(stop_id and stop_id in open_orders_by_id)
        tp_open = bool(tp_id and tp_id in open_orders_by_id)
        reason = ""
        exit_price = 0.0
        if stop_id and not stop_open and _live_order_status(symbol, stop_id) == "FILLED":
            reason = "SL"
            exit_price = float(position.get("exchange_sl", position.get("sl", 0)) or 0)
        elif tp_id and not tp_open and _live_order_status(symbol, tp_id) == "FILLED":
            reason = "TP"
            exit_price = float(position.get("tp", 0) or 0)
        if not reason:
            continue
        sibling = tp_id if reason == "SL" else stop_id
        if sibling and sibling in open_orders_by_id:
            try:
                _cancel_live_order_with_history(
                    sibling,
                    symbol,
                    order_role="TAKE_PROFIT" if reason == "SL" else "STOP_LOSS",
                    reason=f"sibling cancelled after {reason} fill",
                )
            except Exception:
                pass
        if exit_price <= 0:
            exit_price = live_executor.get_ticker_price(symbol)
        _record_live_close(position, exit_price, f"EXCHANGE_{reason}", position_key)
        changed = True

    tracked_groups = {}
    for position_key, position in state.positions.items():
        group = (
            str(position.get("symbol", "")),
            str(position.get("direction", "")).upper(),
        )
        tracked_groups.setdefault(group, []).append((position_key, position))

    reservations: Dict[str, dict] = {}
    tracked_order_ids: set[str] = set()
    for group, legs in tracked_groups.items():
        symbol, direction = group
        exchange_position = by_symbol_side.get(group)
        if exchange_position is None:
            for position_key, position in list(legs):
                exit_price = live_executor.get_ticker_price(symbol)
                _record_live_close(
                    position,
                    exit_price,
                    "EXCHANGE_PROTECTION_OR_MANUAL",
                    position_key,
                )
                changed = True
            continue

        try:
            leverage_profile = ensure_max_live_leverage(
                live_executor,
                symbol,
                direction,
            )
            exchange_leverage = int(leverage_profile["leverage"])
            for _, position in legs:
                if position.get("exchange_leverage") != exchange_leverage:
                    position["exchange_leverage"] = exchange_leverage
                    changed = True
        except (MarginError, OrderRejectedError) as exc:
            print(f"  LIVE LEVERAGE RETRY {symbol} {direction}: {exc}")

        if len(legs) == 1:
            _, only_position = legs[0]
            if not only_position.get("stop_order_id") or not only_position.get("take_profit_order_id"):
                legacy = _protection_from_orders(exchange_orders, symbol, direction)
                if len(legacy) == 2:
                    only_position.update(legacy)
                    changed = True

        for position_key, position in list(legs):
            stop_id = str(position.get("stop_order_id", ""))
            tp_id = str(position.get("take_profit_order_id", ""))
            if stop_id:
                tracked_order_ids.add(stop_id)
            if tp_id:
                tracked_order_ids.add(tp_id)
            if (
                not stop_id
                or not tp_id
                or stop_id not in open_orders_by_id
                or tp_id not in open_orders_by_id
            ):
                _emergency_close_live_position(
                    symbol,
                    direction,
                    float(position.get("size", 0)),
                    "tracked route leg lost SL/TP",
                )
                _record_live_close(
                    position,
                    live_executor.get_ticker_price(symbol),
                    "SAFETY_CLOSE_NO_PROTECTION",
                    position_key,
                )
                changed = True

        remaining_legs = [
            (key, position)
            for key, position in state.positions.items()
            if (
                str(position.get("symbol", "")),
                str(position.get("direction", "")).upper(),
            ) == group
        ]
        tracked_quantity = sum(
            float(position.get("size", 0)) for _, position in remaining_legs
        )
        exchange_quantity = _position_amount(exchange_position)
        tolerance = max(1e-12, tracked_quantity * 1e-6)
        if exchange_quantity + tolerance < tracked_quantity:
            raise RuntimeError(
                f"BingX {symbol} {direction} quantity {exchange_quantity:g} is below "
                f"tracked route total {tracked_quantity:g}"
            )
        excess = max(0.0, exchange_quantity - tracked_quantity)
        if excess > tolerance:
            reservations[external_reservation_key(symbol, direction)] = {
                "status": "EXTERNAL_POSITION",
                "symbol": symbol,
                "direction": direction,
                "size": excess,
            }

    for exchange_position in exchange_positions:
        internal = _internal_symbol(str(exchange_position.get("symbol", "")))
        direction = str(exchange_position.get("positionSide", "")).upper()
        if internal and (internal, direction) not in tracked_groups:
            reservations[external_reservation_key(internal, direction)] = {
                "status": "EXTERNAL_POSITION",
                "symbol": internal,
                "direction": direction,
                "size": _position_amount(exchange_position),
            }
    for order in exchange_orders:
        order_id = _order_id(order)
        if order_id in tracked_order_ids:
            continue
        internal = _internal_symbol(str(order.get("symbol", "")))
        direction = str(order.get("positionSide", "")).upper()
        if internal:
            reservations.setdefault(external_reservation_key(internal, direction), {
                "status": "EXTERNAL_ORDER",
                "symbol": internal,
                "direction": direction,
            })
    external_reservations = reservations
    if changed:
        state.save()

def live_positions_report_snapshot() -> Dict[str, dict]:
    """Read mark PnL and exchange protection immediately before Telegram."""
    fallback = {symbol: dict(position) for symbol, position in state.positions.items()}
    for position in fallback.values():
        position["pnl"] = None
    if live_executor is None or not fallback:
        return fallback

    try:
        balance = live_executor.get_balance()
        exchange_positions = _active_exchange_positions(live_executor.get_positions())
        exchange_orders = live_executor.get_open_orders()
    except Exception as exc:
        print(f"  LIVE REPORT SNAPSHOT ERROR: {_safe_exception_text(exc)}")
        return fallback

    equity = float(balance.get("equity", 0) or 0)
    if math.isfinite(equity) and equity > 0:
        state.paper_equity = equity

    positions_by_key: Dict[Tuple[str, str], dict] = {}
    for row in exchange_positions:
        internal = _internal_symbol(str(row.get("symbol", "")))
        side = str(row.get("positionSide", "")).upper()
        if internal and side:
            positions_by_key[(internal, side)] = row

    orders_by_id: Dict[str, dict] = {}
    legacy_protection_by_group: Dict[Tuple[str, str], dict] = {}
    for order in exchange_orders:
        order_id = _order_id(order)
        if order_id:
            orders_by_id[order_id] = order
        internal = _internal_symbol(str(order.get("symbol", "")))
        side = str(order.get("positionSide", "")).upper()
        order_type = str(order.get("type", order.get("orderType", ""))).upper()
        if not internal or not side:
            continue
        try:
            stop_price = float(order.get("stopPrice", 0) or 0)
        except (TypeError, ValueError):
            continue
        if stop_price <= 0:
            continue
        protection = legacy_protection_by_group.setdefault((internal, side), {})
        if order_type == "STOP_MARKET":
            protection["sl"] = stop_price
        elif order_type == "TAKE_PROFIT_MARKET":
            protection["tp"] = stop_price

    state_group_counts: Dict[Tuple[str, str], int] = {}
    for position in state.positions.values():
        group = (
            str(position.get("symbol", "")),
            str(position.get("direction", "")).upper(),
        )
        state_group_counts[group] = state_group_counts.get(group, 0) + 1

    snapshot: Dict[str, dict] = {}
    for position_key, position in state.positions.items():
        symbol = str(position.get("symbol", position_key))
        side = str(position.get("direction", "")).upper()
        row = positions_by_key.get((symbol, side))
        current = dict(position)
        if row is not None:
            try:
                mark_price = float(row.get("markPrice", 0) or 0)
                current["mark_price"] = mark_price
                if state_group_counts.get((symbol, side), 0) == 1:
                    current["pnl"] = float(row.get("unrealizedProfit", 0) or 0)
                else:
                    entry_price = float(position.get("entry_price", 0) or 0)
                    quantity = float(position.get("size", 0) or 0)
                    current["pnl"] = (
                        (mark_price - entry_price) * quantity
                        if side == "LONG"
                        else (entry_price - mark_price) * quantity
                    )
            except (TypeError, ValueError):
                current["pnl"] = None
        else:
            current["pnl"] = None
        for field, order_field in (
            ("stop_order_id", "sl"),
            ("take_profit_order_id", "tp"),
        ):
            order = orders_by_id.get(str(position.get(field, "")))
            if order is None:
                continue
            try:
                stop_price = float(order.get("stopPrice", 0) or 0)
            except (TypeError, ValueError):
                continue
            if stop_price > 0:
                current[order_field] = stop_price
        if state_group_counts.get((symbol, side), 0) == 1:
            current.update(legacy_protection_by_group.get((symbol, side), {}))
        snapshot[position_key] = current
    return snapshot

def check_live_positions(position_key: str, series: BarSeries) -> bool:
    position = state.positions.get(position_key)
    if position is None or position.get("status") != "OPEN":
        return False
    symbol = str(position["symbol"])
    changed = _ensure_smc_trailing_state(position)
    last = position.get("last_processed_bar")
    last_dt = datetime.fromisoformat(last) if isinstance(last, str) else last
    candidates = [
        candle for candle in series.candles
        if candle.timestamp >= position["execution_time"]
        and (last_dt is None or candle.timestamp > last_dt)
    ]
    for candle in candidates:
        direction = position["direction"]
        sl = float(position["sl"])
        tp = float(position["tp"])
        position["bars_held"] = int(position.get("bars_held", 0)) + 1
        if direction == "LONG":
            stop_hit = candle.low <= sl
            tp_hit = candle.high >= tp
        else:
            stop_hit = candle.high >= sl
            tp_hit = candle.low <= tp
        stop_reason = "TRAIL" if position.get("trailing_stop_active") else "SL"
        reason = stop_reason if stop_hit else ("TP" if tp_hit else "")
        if not reason and position["bars_held"] >= int(position.get("max_hold", 24)):
            reason = "TIME_EXIT"
        position["last_processed_bar"] = candle.timestamp
        state.last_processed_bar[position_key] = candle.timestamp.isoformat()
        changed = True
        if reason:
            close_live_position(position_key, reason)
            return True
        if _update_smc_trailing_after_bar(position, candle):
            changed = True
    return changed

def _contract_entry_unavailable_reason(contract: Optional[dict]) -> Optional[str]:
    if contract is None:
        return "missing"
    try:
        status = int(contract.get("status", 0))
    except (TypeError, ValueError):
        status = 0
    if status != 1:
        return f"status={contract.get('status')}"
    api_state_open = str(contract.get("apiStateOpen", "false")).lower()
    if api_state_open != "true":
        return f"apiStateOpen={api_state_open}"
    return None

def live_preflight(*, test_orders: bool = False) -> BingXExecutor:
    if not telegram_configured():
        raise RuntimeError(
            "Telegram credentials are required for live mode; set "
            "AITRADE_TG_TOKEN and AITRADE_TG_CHAT_ID"
        )
    refresh_runtime_symbols(force=True)
    executor = BingXExecutor(symbol_map=BINGX_MAP)
    balance = executor.get_balance()
    positions_before = _active_exchange_positions(executor.get_positions())
    orders_before = executor.get_open_orders()
    if not executor.get_position_mode():
        raise RuntimeError("BingX account must remain in Hedge Mode")
    if float(balance.get("equity", 0)) <= 0:
        raise RuntimeError("BingX account equity must be positive")
    contracts = executor.get_contracts()
    required_missing: List[str] = []
    inactive_missing: List[str] = []
    for internal_symbol, exchange_symbol in FIXED_BINGX_MAP.items():
        contract = contracts.get(exchange_symbol)
        unavailable_reason = _contract_entry_unavailable_reason(
            contract
        )
        if unavailable_reason is None:
            continue
        entry_routes = _route_ids_for_symbol(LIVE_ENTRY_ROUTES, internal_symbol)
        exposure_reasons = _missing_contract_exposure_reasons(
            internal_symbol,
            exchange_symbol,
            positions_before,
            orders_before,
        )
        if contract is not None:
            if not entry_routes:
                reasons = [unavailable_reason, *exposure_reasons]
                inactive_missing.append(
                    f"{internal_symbol}={exchange_symbol} "
                    f"({', '.join(reasons)})"
                )
                continue
            reasons = [unavailable_reason]
            if entry_routes:
                reasons.append(f"entry_routes={len(entry_routes)}")
            required_missing.append(
                f"{exchange_symbol} ({', '.join(reasons)})"
            )
        elif internal_symbol not in OPTIONAL_INACTIVE_BINGX_SYMBOLS:
            required_missing.append(
                f"{exchange_symbol} ({unavailable_reason})"
            )
        elif entry_routes or exposure_reasons:
            reasons = [unavailable_reason, *exposure_reasons]
            if entry_routes:
                reasons.append(f"entry_routes={len(entry_routes)}")
            required_missing.append(
                f"{exchange_symbol} ({', '.join(reasons)})"
            )
        else:
            inactive_missing.append(
                f"{internal_symbol}={exchange_symbol} ({unavailable_reason})"
            )
    if required_missing:
        raise RuntimeError(
            f"Missing required BingX contracts: {', '.join(required_missing)}"
        )
    if inactive_missing:
        print(
            "LIVE preflight unavailable-entry contract skip: "
            f"{', '.join(inactive_missing)}; no executable entry route required"
        )

    tested: List[str] = []
    if test_orders:
        for symbol in ("BTCUSDT", "HBARUSDT", "EURUSD", "XAUUSD"):
            if _active_exchange_positions(executor.get_positions(symbol)):
                raise RuntimeError(f"Cannot test occupied symbol: {symbol}")
            if executor.get_open_orders(symbol):
                raise RuntimeError(f"Cannot test symbol with open orders: {symbol}")
            price = executor.get_ticker_price(symbol)
            contract = executor.get_contract(symbol)
            precision = int(contract.get("quantityPrecision", 0))
            scale = 10 ** precision
            minimum = max(
                float(contract.get("tradeMinQuantity", 0) or 0),
                float(contract.get("tradeMinUSDT", 0) or 0) / price,
            )
            quantity = math.ceil(minimum * scale - 1e-12) / scale
            quantity = executor.validate_quantity(symbol, quantity, price)
            executor.submit_market_order(
                symbol=symbol,
                side="BUY",
                position_side="LONG",
                quantity=quantity,
                client_order_id=f"{LIVE_CLIENT_ORDER_PREFIX}-pre-{symbol.lower()}",
                stop_loss=price * 0.99,
                take_profit=price * 1.02,
                test=True,
            )
            tested.append(symbol)
        positions_after = _active_exchange_positions(executor.get_positions())
        orders_after = executor.get_open_orders()
        before_position_keys = {
            (row.get("symbol"), row.get("positionSide"), row.get("positionAmt"))
            for row in positions_before
        }
        after_position_keys = {
            (row.get("symbol"), row.get("positionSide"), row.get("positionAmt"))
            for row in positions_after
        }
        before_order_ids = {str(row.get("orderId")) for row in orders_before}
        after_order_ids = {str(row.get("orderId")) for row in orders_after}
        if before_position_keys != after_position_keys or before_order_ids != after_order_ids:
            raise RuntimeError("BingX test-order unexpectedly changed positions or orders")

    print(
        "LIVE preflight OK: "
        f"equity=${float(balance['equity']):.4f} "
        f"available=${float(balance.get('available_margin', 0)):.4f} "
        f"positions={len(positions_before)} open_orders={len(orders_before)} "
        f"hedge_mode=true contracts={len(contracts)}"
        + (f" tested={','.join(tested)}" if tested else "")
    )
    return executor

def _is_transient_exchange_error(exc: Exception) -> bool:
    if isinstance(exc, (RateLimitExchangeError, requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError):
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", 0)
        return status_code in {408, 425, 429} or status_code >= 500
    if isinstance(exc, requests.RequestException):
        return False
    message = str(exc).lower()
    return any(token in message for token in (
        "rate limit", "rate limited", "100410", "connection reset",
        "connection aborted", "temporarily unavailable", "timed out", "timeout",
        "bad gateway", "service unavailable", "gateway timeout",
        "timestamp is invalid", "invalid timestamp", "timestamp mismatch",
        "null timestamp",
    ))

def live_preflight_with_retry(
    *,
    test_orders: bool = False,
    attempts: int = 5,
) -> BingXExecutor:
    """Retry only transient exchange failures; auth/config errors stay fatal."""
    delays = (5, 15, 30, 60)
    for attempt in range(max(1, attempts)):
        try:
            return live_preflight(test_orders=test_orders)
        except AuthError:
            raise
        except Exception as exc:
            if not _is_transient_exchange_error(exc) or attempt >= attempts - 1:
                raise
            delay = delays[min(attempt, len(delays) - 1)]
            print(
                f"LIVE preflight transient error: {_safe_exception_text(exc)}; "
                f"retrying in {delay}s ({attempt + 1}/{attempts})"
            )
            time.sleep(delay)
    raise RuntimeError("LIVE preflight retry loop ended unexpectedly")

def reconcile_live_account_with_retry(*, attempts: int = 5) -> None:
    """Keep startup alive through transient exchange failures."""
    delays = (5, 15, 30, 60)
    for attempt in range(max(1, attempts)):
        try:
            reconcile_live_account()
            return
        except AuthError:
            raise
        except Exception as exc:
            if not _is_transient_exchange_error(exc) or attempt >= attempts - 1:
                raise
            delay = delays[min(attempt, len(delays) - 1)]
            print(
                f"LIVE reconcile transient error: {_safe_exception_text(exc)}; "
                f"retrying in {delay}s ({attempt + 1}/{attempts})"
            )
            time.sleep(delay)
    raise RuntimeError("LIVE reconcile retry loop ended unexpectedly")

def reconcile_live_cycle() -> bool:
    """Return whether exchange reconciliation succeeded for this cycle."""
    try:
        reconcile_live_account()
    except AuthError:
        raise
    except Exception as exc:
        if not _is_transient_exchange_error(exc):
            raise
        error_text = _safe_exception_text(exc)
        print(
            f"  LIVE RECONCILE transient error: {error_text}; "
            "entries blocked this cycle"
        )
        tg.report_error("PORTFOLIO", f"RECONCILE RETRY NEXT CYCLE: {error_text}")
        return False
    return True

def mark_entry_locked_results(scan_results: Dict[str, Any], reason: str) -> None:
    """Keep scores visible while making every reported setup non-actionable."""
    for result in scan_results.values():
        if not isinstance(result, dict) or result.get("already_processed"):
            continue
        result["preview_only"] = True
        result["trade_eligible"] = False
        result["effective_score"] = 0.0
        result["blocked_by"] = reason

def process_pending_signals() -> bool:
    """Fill each strategy on the first valid open for its own timeframe."""
    changed = False
    for pending_key, signal in list(state.pending_signals.items()):
        symbol = str(signal.get("symbol", pending_key))
        position_key = state_key_for_signal(signal)
        route = signal_route(signal)
        if route is not None and not route_is_allowed(signal):
            del state.pending_signals[pending_key]
            changed = True
            print(f"  CONFIG3: dropped pending {route}; route not whitelisted")
            continue
        if not route_is_entry_enabled(signal):
            del state.pending_signals[pending_key]
            changed = True
            print(f"  ROUTE ENTRY DISABLED: dropped pending {route}")
            continue
        if position_key in state.positions:
            del state.pending_signals[pending_key]
            changed = True
            continue
        open_positions = {
            s: p for s, p in state.positions.items() if p.get("status") == "OPEN"
        }
        block = _capacity_block(symbol, open_positions)
        if block:
            del state.pending_signals[pending_key]
            changed = True
            print(f"  PORTFOLIO: dropped pending {symbol}; {block}")
            continue
        queued_at = signal.get("queued_at")
        if not isinstance(queued_at, datetime):
            # Legacy pending signals have no trustworthy submission time. Start
            # their clock now instead of fabricating a historical fill.
            signal["queued_at"] = now_utc()
            changed = True
            continue

        # A forming bar is used only for its open price. The queued timestamp
        # prevents selecting a bar that had already opened before observation.
        try:
            signal_tf = Timeframe(signal.get("timeframe", LTF_TF.value))
        except ValueError:
            signal_tf = LTF_TF
        replay_days = D1_REPLAY_DAYS if signal_tf == D1_TF else PAPER_REPLAY_DAYS
        series = fetch_data(symbol, signal_tf, replay_days, include_forming=True)
        if series is None:
            continue
        next_items = [(i, c) for i, c in enumerate(series.candles) if c.timestamp >= queued_at]
        if not next_items:
            continue
        idx, entry_bar = next_items[0]
        sim = _execution_for(symbol)
        side = OrderSide.BUY if signal["direction"] == "LONG" else OrderSide.SELL
        pside = PositionSide.LONG if signal["direction"] == "LONG" else PositionSide.SHORT
        liquidity = _prior_liquidity(series, idx)
        probe = sim.simulate_at_price(
            symbol, side, pside, 1.0, entry_bar.open,
            entry_bar.timestamp, liquidity,
        )
        if probe is None:
            del state.pending_signals[pending_key]
            changed = True
            continue
        stop_distance = abs(probe.price - signal["sl"])
        if stop_distance <= 0:
            del state.pending_signals[pending_key]
            changed = True
            continue

        # Config 3 applies the ATR guard to every whitelisted route. Signals
        # without a strategy name are legacy/test payloads and retain their old behavior.
        if route is not None:
            atr = signal_atr(signal)
            if atr <= 0:
                del state.pending_signals[pending_key]
                changed = True
                print(f"  CONFIG3: dropped pending {route}; ATR unavailable")
                continue
            stop_atr = stop_distance / atr
            if stop_atr < MIN_STOP_ATR:
                del state.pending_signals[pending_key]
                changed = True
                print(
                    f"  CONFIG3: dropped pending {route}; "
                    f"stop={stop_atr:.3f} ATR < {MIN_STOP_ATR:.2f}"
                )
                continue

        risk_budget = state.paper_equity * RISK_PER_TRADE
        leverage_capped = False

        def cap_size(quantity: float, price: float) -> float:
            nonlocal leverage_capped
            capped = min(quantity, liquidity) if RECALCULATE_FILL_RISK else quantity
            if SYMBOLS.get(symbol) == AssetClass.CRYPTO:
                leverage_limit = state.paper_equity * MAX_CRYPTO_LEVERAGE / price
                if capped > leverage_limit:
                    capped = leverage_limit
                    leverage_capped = True
            return capped

        size_units = cap_size(risk_budget / stop_distance, probe.price)
        fill = None
        if RECALCULATE_FILL_RISK:
            for _ in range(8):
                fill = sim.simulate_at_price(
                    symbol, side, pside, size_units, entry_bar.open,
                    entry_bar.timestamp, liquidity,
                )
                if fill is None:
                    break
                actual_distance = abs(fill.price - signal["sl"])
                if actual_distance <= 0:
                    break
                target_size = cap_size(risk_budget / actual_distance, fill.price)
                if abs(target_size - size_units) <= max(1e-9, size_units * 1e-7):
                    break
                size_units = target_size
        else:
            fill = sim.simulate_at_price(
                symbol, side, pside, size_units, entry_bar.open,
                entry_bar.timestamp, liquidity,
            )
        del state.pending_signals[pending_key]
        changed = True
        if fill is None:
            continue
        sl = signal["sl"]
        if ((signal["direction"] == "LONG" and fill.price <= sl) or
                (signal["direction"] == "SHORT" and fill.price >= sl)):
            continue
        rr = signal.get("risk_reward")
        if rr is None and signal.get("strategy_name", "SMC_MTF_V2") == "SMC_MTF_V2":
            rr = 2.0
        if rr is not None:
            tp = (fill.price + (fill.price - sl) * float(rr)
                  if signal["direction"] == "LONG"
                  else fill.price - (sl - fill.price) * float(rr))
        elif signal.get("tp_pct") is not None:
            tp_pct = float(signal["tp_pct"])
            tp = fill.price * (1 + tp_pct if signal["direction"] == "LONG" else 1 - tp_pct)
        else:
            tp = float(signal["tp"])
        trade = {
            "symbol": symbol,
            "route_id": route,
            "strategy_name": signal.get("strategy_name", "SMC_MTF_V2"),
            "timeframe": signal_tf.value,
            "direction": signal["direction"],
            "signal_time": signal["signal_time"],
            "decision_time": signal["decision_time"],
            "signal_bar_time": signal.get("signal_bar_time"),
            "execution_time": entry_bar.timestamp,
            "entry_time": entry_bar.timestamp,
            "entry_price": fill.price,
            "entry_commission": fill.commission,
            "sl": sl, "tp": tp,
            "size": fill.quantity, "status": "OPEN",
            "score": signal.get("score", 0),
            "reasons": signal.get("reasons", ""),
            "confluence_strategies": signal.get("confluence_strategies", []),
            "bars_held": 0,
            "max_hold": entry_max_hold(signal, 24),
            "last_processed_bar": None,
            "latency_status": fill.latency_status,
            "risk_budget": risk_budget,
            "initial_risk_amount": fill.quantity * abs(fill.price - sl),
            "entry_leverage": fill.quantity * fill.price / state.paper_equity,
            "min_stop_atr": MIN_STOP_ATR,
        }
        if leverage_capped:
            print(
                f"  CONFIG3: capped {route or symbol} at "
                f"{trade['entry_leverage']:.2f}x leverage"
            )
        _ensure_smc_trailing_state(trade)
        state.positions[position_key] = trade
        tg.report_trade_open(trade)
    return changed

# REDACTED: removed private strategy material or identifying configuration.
def runtime_check() -> None:
    """REDACTED: private strategy configuration and dependent implementation."""
    raise RuntimeError('Frozen private route assertions removed; this copy is not operational')

def check_positions(position_key: str, series: BarSeries) -> bool:
    pos = state.positions.get(position_key)
    if pos is None or pos.get("status") != "OPEN":
        return False
    symbol = str(pos["symbol"])
    changed = _ensure_smc_trailing_state(pos)
    last = pos.get("last_processed_bar")
    last_dt = datetime.fromisoformat(last) if isinstance(last, str) else last
    candidates = [
        (i, c) for i, c in enumerate(series.candles)
        if c.timestamp >= pos["execution_time"] and (last_dt is None or c.timestamp > last_dt)
    ]
    for idx, candle in candidates:
        direction, sl, tp = pos["direction"], pos["sl"], pos["tp"]
        pos["bars_held"] = int(pos.get("bars_held", 0)) + 1
        if direction == "LONG":
            stop_hit, tp_hit = candle.low <= sl, candle.high >= tp
            stop_reason = "TRAIL" if pos.get("trailing_stop_active") else "SL"
            reason = stop_reason if stop_hit else ("TP" if tp_hit else "")
            base = (candle.open if candle.open <= sl else sl) if stop_hit else tp
            side, pside = OrderSide.SELL, PositionSide.LONG
        else:
            stop_hit, tp_hit = candle.high >= sl, candle.low <= tp
            stop_reason = "TRAIL" if pos.get("trailing_stop_active") else "SL"
            reason = stop_reason if stop_hit else ("TP" if tp_hit else "")
            base = (candle.open if candle.open >= sl else sl) if stop_hit else tp
            side, pside = OrderSide.BUY, PositionSide.SHORT
        if not reason and pos["bars_held"] >= int(pos.get("max_hold", 24)):
            reason = "TIME_EXIT"
            base = candle.close
        pos["last_processed_bar"] = candle.timestamp
        state.last_processed_bar[position_key] = candle.timestamp.isoformat()
        changed = True
        if not reason:
            _update_smc_trailing_after_bar(pos, candle)
            continue
        sim = _execution_for(symbol)
        fill = sim.simulate_at_price(
            symbol, side, pside, pos["size"], base, candle.timestamp,
            _prior_liquidity(series, idx),
        )
        if fill is None:
            continue
        exit_price = fill.price
        gross = ((exit_price - pos["entry_price"]) if direction == "LONG" else (pos["entry_price"] - exit_price)) * pos["size"]
        pnl = gross - pos.get("entry_commission", 0.0) - fill.commission
        pos["status"] = "CLOSED"
        pos["exit_time"] = candle.timestamp + timedelta(minutes=series.timeframe.minutes())
        pos["exit_price"] = exit_price
        pos["exit_commission"] = fill.commission
        pos["pnl"] = pnl
        pos["exit_reason"] = reason
        pos["ambiguous_bar"] = bool(stop_hit and tp_hit)

        state.paper_equity += pnl
        state.total_pnl += pnl
        state.trade_log.append(pos)
        del state.positions[position_key]

        tg.report_trade_close(pos, state.paper_equity, reason)

        print(f"\n  === DONG LENH {symbol} | {reason} | PnL=${pnl:+,.2f} | Equity=${state.paper_equity:,.2f} ===")
        break
    return changed

# REDACTED: removed private strategy material or identifying configuration.
def build_single_tf_route_specs() -> List[Tuple[Any, str, Timeframe]]:
    """REDACTED: private strategy configuration and dependent implementation."""
    return []

def build_entry_scan_route_specs() -> List[Tuple[Any, str, Timeframe]]:
    """Exclude all 14 management-only routes before signal data is fetched."""
    return [
        (strategy, symbol, timeframe)
        for strategy, symbol, timeframe in build_single_tf_route_specs()
        if route_is_entry_enabled({
            "route_id": strategy_instance_route_id(strategy, symbol, timeframe),
            "strategy_name": strategy.name,
            "symbol": symbol,
            "timeframe": timeframe.value,
        })
    ]

# REDACTED: removed private strategy material or identifying configuration.
def current_smc_scan_symbols() -> Tuple[str, ...]:
    """REDACTED: private strategy reference removed."""
    return ()

def main_loop(live_mode: bool = False, *, once: bool = False):
    global state, live_executor, external_reservations, _live_leverage_profiles
    state = AutoTradeState("live_state.json" if live_mode else "state.json")
    restored = state.load()
    _live_leverage_profiles = {}
    if live_mode:
        live_executor = live_preflight_with_retry()
        ensure_state_symbol_mappings()
        live_executor.update_symbol_map(BINGX_MAP)
        if state.pending_signals:
            state.pending_signals.clear()
            state.save()
        reconcile_live_account_with_retry()
    else:
        live_executor = None
        external_reservations = {}
        refresh_runtime_symbols(force=True)
    startup_smc_symbols = current_smc_scan_symbols()
    single_tf_routes = build_entry_scan_route_specs()
    startup_symbols = tuple(sorted(WHITELIST_SYMBOLS))
    print(f"\n{'='*70}")
    print("  WHITELIST ASSET-ADAPTIVE STRATEGY SCANNER")
    print(f"  Mode: {'LIVE' if live_mode else 'PAPER'}")
    print(
        "  Entry contract: 59 legs from the frozen 62-leg operator selection "
        "on H1/H4/H6/H8/H12/D1"
    )
    print("  Operator exclusions: VANRYUSDT, USDTRY (management/reconcile only)")
    print(
        f"  SMC gate: {SMC_CONFIRMATION_MODE.upper()} | "
        f"Time exit: {SMC_MAX_HOLD_BARS} bars ({SMC_MAX_HOLD_BARS}h) | "
        f"Trail: A{SMC_TRAIL_ACTIVATION_R:g}R/D{SMC_TRAIL_DISTANCE_R:g}R"
    )
    print(
        f"  Config 3: stop >= {MIN_STOP_ATR:.2f} ATR | "
        "fill-risk recalc | live leverage = BingX maximum"
    )
    print(f"  SMC MTF entry scan: {', '.join(startup_smc_symbols) or 'none'}")
    print(f"  Whitelist: {len(startup_symbols)} symbols / {len(current_allowed_routes())} routes")
    print(f"  Unsupported: {', '.join(UNSUPPORTED_WHITELIST)}")
    print("  Market data: BingX | residual factor: Binance/BingX | legacy D1: Yahoo")
    capital_label = "BingX equity" if live_mode else "Shared capital"
    risk_label = (
        f"{LIVE_RISK_FRACTION:.1%} equity/route target; BingX minimum may exceed"
        if live_mode
        else f"{RISK_PER_TRADE:.1%}"
    )
    print(f"  {capital_label}: ${state.paper_equity:,.4f} | Risk: {risk_label}")
    if unlimited_route_mode():
        print(
            "  Position mode: unlimited-route | one active leg per route | "
            f"{len(SINGLE_ENTRY_PATH_PREFERRED_ROUTES)} shared paths cap=1 | "
            "no global caps"
        )
    else:
        print(
            f"  Position caps: Crypto={MAX_CRYPTO_POSITIONS} | "
            f"Forex/Gold={MAX_FOREX_GOLD_POSITIONS} | Total={MAX_POSITIONS} | "
            f"SMC={MAX_SMC_POSITIONS}"
        )
    print(f"  Scan interval: 300s (5 phut)")
    print(f"  Detailed terminal steps: {'ENABLED' if VERBOSE_SCAN else 'DISABLED'}")
    print(f"  New entries: {'ENABLED' if ENTRY_ENABLED else 'LOCKED'}")
    print(f"  Live-approved routes: {len(LIVE_APPROVED_ROUTES)}")
    print(f"  Entry-enabled routes: {len(LIVE_ENTRY_ROUTES)}")
    print(
        f"  Single-entry paths: {len(SINGLE_ENTRY_PATH_PREFERRED_ROUTES)} "
        "duplicate paths cap=1"
    )
    for path_id, preferred_route in sorted(
        SINGLE_ENTRY_PATH_PREFERRED_ROUTES.items()
    ):
        print(f"    {path_id}: preferred={preferred_route}")
    print(
        f"  Entry-disabled routes: {len(LIVE_ENTRY_DISABLED_ROUTES)} | "
        f"MR/Breakout time exit: {MR_MAX_HOLD_BARS}/{BREAKOUT_MAX_HOLD_BARS} D1 bars"
    )
    print(f"  Log dir: {LOG_DIR}")
    if live_mode:
        print(f"  Order history: {LIVE_ORDER_HISTORY_PATH}")
    if restored:
        print(f"  State: restored ({len(state.positions)} positions, {len(state.pending_signals)} pending)")
    else:
        print("  State: fresh")
    if live_mode:
        print(f"  External reservations: {len(external_reservations)} (never managed by bot)")
    print(f"{'='*70}")

    smc_strategy = SMCMultiTimeframe()
    smc_strategy._init_indicators()
    smc_strategy.set_parameters(smc_runtime_parameters())

    tg.report_startup(
        mode="LIVE" if live_mode else "PAPER",
        symbols=list(startup_symbols),
        htf=HTF_TF.value,
        ltf=LTF_TF.value,
        strategies=[
            f"SMC {HTF_TF.value}/{LTF_TF.value} "
            f"{SMC_CONFIRMATION_MODE.upper()} exit={SMC_MAX_HOLD_BARS}h "
            f"trail=A{SMC_TRAIL_ACTIVATION_R:g}R/D{SMC_TRAIL_DISTANCE_R:g}R "
            f"guard={MIN_STOP_ATR:.2f}ATR",
            "59 entry routes mapped from the frozen 62-leg operator selection",
            "All 9 duplicate compute paths capped at one active bot leg",
            "ZEC LONG-only and WLD SHORT-only direction restrictions preserved",
            "H6/H12 derived from complete BingX H1 UTC blocks",
            "37 OOS_CANDIDATE and 22 WATCH legs entry-enabled",
            "VANRYUSDT and USDTRY retained for management but excluded from entry",
            "73-route management whitelist retained for existing positions",
        ],
        max_positions=(len(LIVE_APPROVED_ROUTES) if unlimited_route_mode() else MAX_POSITIONS),
        max_crypto_positions=(
            len(LIVE_APPROVED_ROUTES) if unlimited_route_mode() else MAX_CRYPTO_POSITIONS
        ),
        max_forex_positions=(
            len(LIVE_APPROVED_ROUTES)
            if unlimited_route_mode()
            else MAX_FOREX_GOLD_POSITIONS
        ),
        equity=state.paper_equity,
        risk_label=(
            f"{LIVE_RISK_FRACTION:.1%} equity/route target; minimum override enabled"
            if live_mode
            else f"{RISK_PER_TRADE:.1%}/trade"
        ),
        unlimited_routes=unlimited_route_mode(),
        leverage_label="BingX maximum (margin optimized)" if live_mode else None,
    )

    cycle = 0

    while True:
        cycle += 1
        now = now_utc()

        configured_entries_enabled = ENTRY_ENABLED or not live_mode
        reconciliation_ok = reconcile_live_cycle() if live_mode else True
        cycle_scans_enabled = reconciliation_ok
        cycle_entries_enabled = configured_entries_enabled and reconciliation_ok
        if cycle_scans_enabled:
            refresh_runtime_symbols(executor=live_executor)
        else:
            ensure_state_symbol_mappings()
            if live_executor is not None:
                live_executor.update_symbol_map(BINGX_MAP)
        smc_cycle_symbols = current_smc_scan_symbols() if cycle_scans_enabled else ()

        print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] Cycle #{cycle}")
        print(f"  Equity: ${state.paper_equity:,.2f} | Positions: {len(state.positions)}")
        scan_trace(
            f"1/7 account reconciliation: {'OK' if reconciliation_ok else 'FAILED'}; "
            f"entries={'ON' if cycle_entries_enabled else 'OFF'}"
        )
        scan_trace(
            f"2/7 runtime universe: {len(WHITELIST_SYMBOLS)} symbols, "
            f"{len(current_allowed_routes())} routes, SMC={len(smc_cycle_symbols)}"
        )
        if not cycle_entries_enabled:
            if cycle_scans_enabled:
                print("  ENTRY LOCK: scan/report active; no new entries")
            else:
                print("  ENTRY GUARD: scan paused; managing existing positions only")

        # Paper fills on the next observed bar open. Live enters immediately
        # after the closed signal bar is observed.
        if not live_mode and process_pending_signals():
            state.save()

        # Only entry-enabled routes are evaluated for new signals. Open legs,
        # including management-only routes, remain handled in phase 3 above.
        scan_results: Dict[str, Optional[Dict]] = {}
        entry_candidates: List[dict] = []
        smc_scan_order = [symbol for symbol in smc_cycle_symbols if symbol in SYMBOLS]

        # Manage every open position on the timeframe that created it.
        position_keys = list(state.positions.keys())
        scan_trace(f"3/7 manage open positions: {len(position_keys)} route legs")
        for position_number, position_key in enumerate(position_keys, start=1):
            pos = state.positions[position_key]
            sym = str(pos.get("symbol", position_key))
            try:
                position_tf = Timeframe(pos.get("timeframe", LTF_TF.value))
            except ValueError:
                position_tf = LTF_TF
            replay_days = D1_REPLAY_DAYS if position_tf == D1_TF else PAPER_REPLAY_DAYS
            scan_trace(
                f"3/7 position {position_number}/{len(position_keys)}: "
                f"{position_route(pos)} {sym} {position_tf.value} -> fetch {replay_days}d"
            )
            position_series = fetch_data(sym, position_tf, replay_days)
            if position_series and len(position_series) > 0:
                position_changed = (
                    check_live_positions(position_key, position_series)
                    if live_mode
                    else check_positions(position_key, position_series)
                )
                if position_changed:
                    state.save()
                    scan_trace("3/7 position state changed and saved")
                else:
                    scan_trace("3/7 position unchanged; no exit/stop update")
            else:
                scan_trace("3/7 position data unavailable; left unchanged")

        series_cache: Dict[Tuple[str, Timeframe, str], Optional[BarSeries]] = {}
        route_specs = single_tf_routes if cycle_scans_enabled else ()
        scan_trace(f"4/7 scan single-TF routes: {len(route_specs)}")
        for route_number, (single_strategy, symbol, timeframe) in enumerate(
            route_specs, start=1
        ):
            route_label = strategy_instance_route_id(
                single_strategy,
                symbol,
                timeframe,
            )
            key = route_label
            scan_trace(
                f"4/7 route {route_number}/{len(route_specs)}: "
                f"{route_label} [{timeframe.value}]"
            )
            route_probe = {
                "route_id": route_label,
                "symbol": symbol,
                "strategy_name": single_strategy.name,
                "timeframe": timeframe.value,
            }
            if route_is_reserved(route_probe):
                scan_trace("4/7 -> SKIP reserved by an open/pending route leg")
                continue
            if symbol not in SYMBOLS:
                scan_trace("4/7 -> SKIP symbol mapping unavailable")
                continue
            if not is_market_open(symbol):
                scan_trace("4/7 -> SKIP market closed")
                continue
            try:
                provider = signal_data_provider(
                    single_strategy.name,
                    symbol,
                    timeframe,
                )
                cache_key = (symbol, timeframe, provider)
                if cache_key not in series_cache:
                    analysis_days = D1_ANALYSIS_DAYS if timeframe == D1_TF else 160
                    scan_trace(
                        f"4/7 -> DATA {provider} fetch {analysis_days}d "
                        f"for {symbol} {timeframe.value}"
                    )
                    series_cache[cache_key] = fetch_signal_data(
                        single_strategy.name,
                        symbol,
                        timeframe,
                        analysis_days,
                    )
                series = series_cache[cache_key]
                if series is not None and len(series) > 0:
                    scan_trace(
                        f"4/7 -> DATA ready bars={len(series)} "
                        f"last={series.candles[-1].timestamp.isoformat()}"
                    )
                else:
                    scan_trace("4/7 -> DATA unavailable; analyzer will fail closed")
                if isinstance(single_strategy, ResidualBreakoutRecovery):
                    factor_returns = get_binance_residual_factor()
                    if factor_returns is None:
                        raise RuntimeError("Binance residual factor unavailable")
                    single_strategy.set_factor_returns(factor_returns)
                signal = analyze_single_tf(
                    symbol,
                    single_strategy,
                    series,
                    timeframe=timeframe,
                )
                scan_results[key] = signal
                if signal is None:
                    scan_trace("4/7 -> NO_SIGNAL on latest closed bar")
                    continue
                scan_trace(
                    f"4/7 -> SIGNAL {signal['direction']} "
                    f"score={signal.get('effective_score', signal.get('score', 0)):g}/"
                    f"{signal.get('required_score', 0):g} "
                    f"bar={signal.get('signal_bar_time')}"
                )
                previous = state.last_signal.get(key)
                if previous and previous.get("signal_bar_time") == signal.get("signal_bar_time"):
                    scan_results[key] = mark_signal_already_processed(signal)
                    scan_trace("4/7 -> SKIP same closed signal bar already processed")
                    continue
                # Mark the closed bar as processed even if portfolio gates
                # later reject it; stale signals must never enter late.
                state.last_signal[key] = signal
                if not route_is_entry_enabled(signal):
                    scan_results[key] = mark_signal_entry_disabled(signal)
                    scan_trace("4/7 -> SKIP route entry disabled")
                    continue
                activation_block = recovery_activation_block(signal)
                if activation_block:
                    scan_results[key] = mark_signal_migration_blocked(
                        signal,
                        activation_block,
                    )
                    scan_trace(f"4/7 -> SKIP {activation_block}")
                    continue
                migration_block = recovery_migration_block(signal)
                if migration_block:
                    scan_results[key] = mark_signal_migration_blocked(
                        signal,
                        migration_block,
                    )
                    scan_trace(f"4/7 -> SKIP {migration_block}")
                    continue
                entry_candidates.append(signal)
                scan_trace("4/7 -> CANDIDATE queued for portfolio selection")
            except Exception as exc:
                error_text = _safe_exception_text(exc)
                scan_results[key] = f"ERROR: {error_text}"
                scan_trace(f"4/7 -> ERROR {error_text}")
                tg.report_error(symbol, f"{single_strategy.name}: {error_text}")

        scan_trace(f"5/7 scan SMC MTF routes: {len(smc_scan_order)}")
        for symbol in smc_scan_order:
            if symbol not in SYMBOLS:
                scan_trace(f"5/7 {symbol} -> SKIP symbol mapping unavailable")
                continue
            smc_route_probe = {
                "symbol": symbol,
                "strategy_name": "SMC_MTF_V2",
                "timeframe": LTF_TF.value,
            }
            if route_is_reserved(smc_route_probe):
                scan_trace(f"5/7 {symbol} -> SKIP reserved by open/pending SMC leg")
                continue

            # Weekend filter
            if not is_market_open(symbol):
                print(f"  {symbol}: market closed (weekend), skip")
                scan_trace(f"5/7 {symbol} -> SKIP market closed")
                continue

            scan_trace(
                f"5/7 {symbol} -> fetch H4/H1, evaluate score and confirmation gate"
            )
            print(f"  Scanning {symbol}...", end=" ")
            sys.stdout.flush()
            key = f"SMC_MTF_V2:{symbol}:{LTF_TF.value}"
            try:
                min_score = SMC_MTF_MIN_SCORES[symbol]
                smc_strategy.set_parameters(smc_mtf_parameters(symbol))
                signal = analyze_symbol(
                    symbol,
                    smc_strategy,
                    min_score_filter=min_score,
                    signal_min_score_override=1,
                    include_blocked_preview=True,
                )
                if signal:
                    scan_results[key] = signal

                    if (
                        signal.get("preview_only")
                        or signal.get("below_threshold")
                        or not signal.get("trade_eligible", True)
                    ):
                        print(
                            f"near gate {signal.get('effective_score', 0):g}/"
                            f"{signal.get('required_score', min_score):g}, skip"
                        )
                        scan_trace(
                            f"5/7 {symbol} -> BLOCKED "
                            f"effective={signal.get('effective_score', 0):g}/"
                            f"{signal.get('required_score', min_score):g} "
                            f"reason={signal.get('blocked_by') or 'BELOW_GATE'} "
                            f"setup={signal.get('reasons') or 'NONE'}"
                        )
                        continue

                    previous = state.last_signal.get(key)
                    if previous and previous.get("signal_bar_time") == signal.get("signal_bar_time"):
                        scan_results[key] = mark_signal_already_processed(signal)
                        print("same closed signal bar (already processed), skip")
                        scan_trace(f"5/7 {symbol} -> SKIP signal bar already processed")
                        continue

                    print(f"TIN HIEU {signal['direction']} | score={signal['score']} | "
                          f"price={signal['current_price']:.2f} | SL={signal['sl']:.2f} | TP={signal['tp']:.2f}")
                    print(f"    Regime: {signal['regime']} | Reasons: {signal['reasons']}")
                    state.last_signal[key] = signal
                    entry_candidates.append(signal)
                    scan_trace(f"5/7 {symbol} -> CANDIDATE queued for portfolio selection")
                else:
                    print("no signal")
                    scan_trace(f"5/7 {symbol} -> NO_SIGNAL")
            except Exception as e:
                error_text = _safe_exception_text(e)
                scan_results[key] = f"ERROR: {error_text}"
                print(f"ERROR: {error_text}")
                scan_trace(f"5/7 {symbol} -> ERROR {error_text}")
                tg.report_error(symbol, error_text)

        selected, conflicts = select_entry_candidates(entry_candidates)
        scan_trace(
            f"6/7 portfolio selection: candidates={len(entry_candidates)}, "
            f"selected={len(selected)}, conflicts={len(conflicts)}"
        )
        for candidate in selected:
            scan_trace(
                f"6/7 selected {signal_route(candidate)} "
                f"{candidate.get('direction')} score="
                f"{candidate.get('effective_score', candidate.get('score', 0)):g}"
            )
        for symbol in conflicts:
            print(f"  PORTFOLIO: strategy direction conflict on {symbol}, skip")
            for result in scan_results.values():
                if isinstance(result, dict) and result.get("symbol") == symbol:
                    result["preview_only"] = True
                    result["below_threshold"] = True
                    result["effective_score"] = 0
                    result["trade_eligible"] = False
                    result["blocked_by"] = "STRATEGY_CONFLICT"

        if not cycle_entries_enabled:
            reason = "ENTRY_LOCK" if not configured_entries_enabled else "RECONCILE_TRANSIENT"
            mark_entry_locked_results(scan_results, reason)
            selected = []

        for signal in selected:
            symbol = signal["symbol"]
            if not route_is_allowed(signal):
                print(f"  CONFIG3: blocked non-whitelisted route {signal_route(signal)}")
                continue
            if not route_is_entry_enabled(signal):
                print(f"  ROUTE ENTRY DISABLED: {signal_route(signal)}")
                continue
            activation_block = recovery_activation_block(signal)
            if activation_block:
                print(f"  RECOVERY ACTIVATION: {activation_block}")
                mark_portfolio_blocked(
                    scan_results,
                    symbol,
                    activation_block,
                    signal_route(signal) if unlimited_route_mode() else None,
                )
                continue
            migration_block = recovery_migration_block(signal)
            if migration_block:
                print(f"  RECOVERY MIGRATION: {migration_block}")
                mark_portfolio_blocked(
                    scan_results,
                    symbol,
                    migration_block,
                    signal_route(signal) if unlimited_route_mode() else None,
                )
                continue
            portfolio_block = portfolio_heat_block_signal(signal)
            if portfolio_block:
                print(f"  PORTFOLIO: {portfolio_block}, skip")
                mark_portfolio_blocked(
                    scan_results,
                    symbol,
                    portfolio_block,
                    signal_route(signal) if unlimited_route_mode() else None,
                )
                print(
                    f"  {signal['strategy_name']} {symbol}: "
                    "signal blocked by shared portfolio"
                )
                continue
            trade = execute_live(signal) if live_mode else execute_paper(signal)
            if trade:
                action = "OPENED" if live_mode else "QUEUED"
                print(
                    f"    ==> {action} {signal['strategy_name']} "
                    f"{signal['direction']} {symbol} on {signal['timeframe']}"
                )

        state.save()
        scan_trace("7/7 state saved; building Telegram/report snapshot")
        report_positions = (
            live_positions_report_snapshot() if live_mode else state.positions
        )
        tg.report_scan(
            scan_results,
            report_positions,
            state.paper_equity,
            state.total_pnl,
            cycle,
        )
        scan_trace(
            f"7/7 cycle complete: scanned={len(scan_results)}, "
            f"positions={len(state.positions)}, next scan in 5m"
        )

        if once or "--once" in sys.argv:
            print("\n  --once mode: stopping after 1 cycle.")
            break
        for remaining in range(300, 0, -60):
            time.sleep(60)
            print(f"  Next scan in {remaining//60}m...")

        print()

CLI_USAGE = """usage: auto_trade_smc_mtf.py [--live] [--once]
       auto_trade_smc_mtf.py --check
       auto_trade_smc_mtf.py --live-preflight [--live-test-orders]

Live entries default to locked. Set AITRADE_ENTRY_ENABLED=1 explicitly to allow them.
"""

def cli_main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--help" in args or "-h" in args:
        print(CLI_USAGE)
        return 0
    if "--check" in args:
        runtime_check()
        return 0
    if "--live-preflight" in args or "--live-test-orders" in args:
        live_preflight_with_retry(test_orders="--live-test-orders" in args)
        return 0
    main_loop(live_mode="--live" in args, once="--once" in args)
    return 0

if __name__ == "__main__":
    try:
        cli_main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
        tg.report_shutdown()
        state.save()
    except Exception as e:
        error_text = _safe_exception_text(e)
        print(f"\nFatal error: {error_text}")
        try:
            send_tg(
                f"<b>💥 FATAL ERROR</b>\n<code>{error_text[:300]}</code>",
                silent=False,
            )
        except Exception as notify_exc:
            print(f"Fatal notification error: {_safe_exception_text(notify_exc)}")
        state.save()
        if _request_exception_in_chain(e) is not None:
            raise SystemExit(1) from None
        raise
