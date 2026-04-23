"""
BIFS VSA SCANNER v4 — VSA + Volume Profile Multi-TF
═══════════════════════════════════════════════════════
MEJORAS vs v3:
  1. VSA EXPANDIDO: 8 señales (+ UPTHRUST, TEST, STOPPING VOL, CLIMAX)
  2. MULTI-BAR CONTEXT: Lee secuencias de 3 barras, no barras aisladas
  3. TENDENCIA SMA: Contexto SMA20/50 para filtrar señales
  4. CONFLUENCIA: Score penaliza contradicciones VSA vs VP
  5. COMPRESIÓN DIRECCIONAL: Ya no es siempre bull — depende de contexto
  6. 52W RÁPIDO: Calculado desde data descargada (elimina 50+ API calls lentas)
  7. UNIVERSO INTEGRADO: Flag para activar 100+ activos con ADRs arg y CEDEARs
  8. SECTOR HEATMAP: Resumen sectorial en el HTML
  9. SCORE v2: Breakdown transparente con componentes visibles
 10. SEÑAL COMPUESTA: Ícono de confluencia VSA+VP en la tabla

pip install yfinance requests --quiet
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import requests
import os
import glob
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════
EXTENDED_UNIVERSE = True   # True = 143 activos (USA + ARG ADRs + CEDEARs)
                           # False = 50 activos (solo USA core)

# ══════════════════════════════════════════════════════════════
# UNIVERSO
# ══════════════════════════════════════════════════════════════
UNIVERSE_CORE = [
    # ETFs
    ("SPY",  "S&P 500 ETF",          "ETF",   "Index"),
    ("QQQ",  "Nasdaq 100 ETF",        "ETF",   "Index"),
    ("IWM",  "Russell 2000 ETF",      "ETF",   "Index"),
    ("DIA",  "Dow Jones ETF",         "ETF",   "Index"),
    ("GLD",  "Gold ETF",              "ETF",   "Commodity"),
    ("SLV",  "Silver ETF",            "ETF",   "Commodity"),
    ("XLE",  "Energy Select ETF",     "ETF",   "Energy"),
    ("XLK",  "Tech Select ETF",       "ETF",   "Tech"),
    ("XLF",  "Finance Select ETF",    "ETF",   "Finance"),
    ("XLV",  "Health Select ETF",     "ETF",   "Health"),
    ("SOXX", "Semis ETF",             "ETF",   "Semis"),
    ("ARKK", "ARK Innovation ETF",    "ETF",   "Growth"),
    ("TLT",  "20Y Treasury ETF",      "ETF",   "Bonds"),
    ("VXX",  "VIX Short-Term ETF",    "ETF",   "Volatility"),
    # Mega cap
    ("NVDA", "NVIDIA Corp",           "Stock", "Semis"),
    ("AAPL", "Apple Inc",             "Stock", "Tech"),
    ("MSFT", "Microsoft Corp",        "Stock", "Tech"),
    ("AMZN", "Amazon.com",            "Stock", "Tech"),
    ("GOOGL","Alphabet Inc",          "Stock", "Tech"),
    ("META", "Meta Platforms",        "Stock", "Tech"),
    ("TSLA", "Tesla Inc",             "Stock", "Auto"),
    ("AVGO", "Broadcom Inc",          "Stock", "Semis"),
    # AI / Software
    ("PLTR", "Palantir",              "Stock", "AI"),
    ("APP",  "AppLovin Corp",         "Stock", "AdTech"),
    ("NOW",  "ServiceNow",            "Stock", "SaaS"),
    ("CRM",  "Salesforce",            "Stock", "SaaS"),
    ("CRWD", "CrowdStrike",           "Stock", "Cyber"),
    ("SNOW", "Snowflake",             "Stock", "Data"),
    # Finance
    ("JPM",  "JPMorgan Chase",        "Stock", "Finance"),
    ("GS",   "Goldman Sachs",         "Stock", "Finance"),
    ("V",    "Visa Inc",              "Stock", "Payments"),
    ("MA",   "Mastercard",            "Stock", "Payments"),
    # Defense / Space
    ("LMT",  "Lockheed Martin",       "Stock", "Defense"),
    ("RTX",  "Raytheon Technologies", "Stock", "Defense"),
    ("RKLB", "Rocket Lab Corp",       "Stock", "Space"),
    # Healthcare
    ("LLY",  "Eli Lilly",             "Stock", "Pharma"),
    ("ISRG", "Intuitive Surgical",    "Stock", "MedTech"),
    # Energy
    ("XOM",  "Exxon Mobil",           "Stock", "Energy"),
    ("CVX",  "Chevron Corp",          "Stock", "Energy"),
    # Consumer
    ("COST", "Costco Wholesale",      "Stock", "Consumer"),
    ("WMT",  "Walmart Inc",           "Stock", "Consumer"),
    # Semis
    ("AMD",  "Advanced Micro Devices","Stock", "Semis"),
    ("INTC", "Intel Corp",            "Stock", "Semis"),
    ("MU",   "Micron Technology",     "Stock", "Semis"),
    ("TSM",  "Taiwan Semiconductor",  "Stock", "Semis"),
    # Growth / LatAm
    ("MELI", "MercadoLibre",          "Stock", "LatAm"),
    ("SHOP", "Shopify Inc",           "Stock", "eComm"),
    ("NET",  "Cloudflare",            "Stock", "Cloud"),
    ("UBER", "Uber Technologies",     "Stock", "Tech"),
    ("BABA", "Alibaba Group",         "Stock", "China"),
]

UNIVERSE_EXTENDED = [
    # ═══════════════════════════════════════════════════════════
    # ADRs ARGENTINOS (operan en NYSE, volumen propio)
    # ═══════════════════════════════════════════════════════════
    ("GGAL",  "Grupo Fin. Galicia",      "Stock", "Arg-Finance"),
    ("BMA",   "Banco Macro",             "Stock", "Arg-Finance"),
    ("SUPV",  "Grupo Supervielle",       "Stock", "Arg-Finance"),
    ("YPF",   "YPF S.A.",                "Stock", "Arg-Energy"),
    ("PAM",   "Pampa Energía",           "Stock", "Arg-Energy"),
    ("CEPU",  "Central Puerto",          "Stock", "Arg-Energy"),
    ("TGS",   "Transp. Gas del Sur",     "Stock", "Arg-Energy"),
    ("VIST",  "Vista Energy",            "Stock", "Arg-Energy"),
    ("LOMA",  "Loma Negra",              "Stock", "Arg-Materials"),
    ("IRS",   "IRSA",                    "Stock", "Arg-RealEstate"),
    ("CRESY", "Cresud",                  "Stock", "Arg-Agri"),
    ("EDN",   "Edenor",                  "Stock", "Arg-Utilities"),
    ("TEO",   "Telecom Argentina",       "Stock", "Arg-Telecom"),
    ("BIOX",  "Bioceres",                "Stock", "Arg-Agri"),
    ("AGRO",  "Adecoagro",               "Stock", "Arg-Agri"),
    ("SATL",  "Satellogic",              "Stock", "Arg-Space"),

    # ═══════════════════════════════════════════════════════════
    # CEDEARs CON VOLUMEN REAL EN BYMA (no en UNIVERSE_CORE)
    # Fuente: ranking volumen operado BYMA
    # ═══════════════════════════════════════════════════════════

    # ─── Crypto / Digital Assets ──────────────────────────────
    ("IBIT",  "iShares Bitcoin Trust",   "ETF",   "Crypto"),
    ("ETHA",  "iShares Ethereum Trust",  "ETF",   "Crypto"),
    ("MSTR",  "MicroStrategy",           "Stock", "Crypto"),
    ("HUT",   "Hut 8 Corp",             "Stock", "Crypto"),
    ("COIN",  "Coinbase Global",         "Stock", "Crypto"),

    # ─── Tech / AI / Quantum ──────────────────────────────────
    ("ORCL",  "Oracle Corp",             "Stock", "Cloud"),
    ("NFLX",  "Netflix",                 "Stock", "Entertainment"),
    ("RGTI",  "Rigetti Computing",       "Stock", "Quantum"),
    ("ASTS",  "AST SpaceMobile",         "Stock", "Space"),

    # ─── Mega Cap / Value ─────────────────────────────────────
    ("BRK-B", "Berkshire Hathaway",      "Stock", "Finance"),
    ("GE",    "General Electric",        "Stock", "Industrial"),
    ("UNH",   "UnitedHealth",            "Stock", "Health"),

    # ─── LatAm ────────────────────────────────────────────────
    ("NU",    "Nu Holdings",             "Stock", "LatAm"),
    ("STNE",  "StoneCo",                 "Stock", "LatAm"),
    ("PBR",   "Petrobras",               "Stock", "Energy"),
    ("JMIA",  "Jumia Technologies",      "Stock", "Africa"),
    ("EWZ",   "Brazil ETF",              "ETF",   "LatAm"),
]


# ══════════════════════════════════════════════════════════════
# VOLUME PROFILE ENGINE (sin cambios del v3)
# ══════════════════════════════════════════════════════════════
def _get_vol(y11, y12, y21, y22, height, vol):
    if height <= 0 or vol <= 0:
        return 0.0
    overlap = max(0, min(max(y11,y12), max(y21,y22)) - max(min(y11,y12), min(y21,y22)))
    return overlap * vol / height

def calc_volume_profile(df, lookback, rows=24, va_pct=70.0):
    if df is None or len(df) < lookback:
        return None
    subset = df.iloc[-lookback:].copy()
    h_arr = subset['High'].values.astype(float)
    l_arr = subset['Low'].values.astype(float)
    o_arr = subset['Open'].values.astype(float)
    c_arr = subset['Close'].values.astype(float)
    v_arr = subset['Volume'].values.astype(float)

    top = float(np.nanmax(h_arr))
    bot = float(np.nanmin(l_arr))
    if top <= bot:
        return None
    step = (top - bot) / rows
    levels = [bot + step * i for i in range(rows + 1)]
    totalvols = np.zeros(rows)

    for bar in range(len(subset)):
        h, l, o, c, v = h_arr[bar], l_arr[bar], o_arr[bar], c_arr[bar], v_arr[bar]
        if np.isnan(h) or np.isnan(v) or v <= 0:
            continue
        body_top = max(o, c)
        body_bot = min(o, c)
        topwick = h - body_top
        bottomwick = body_bot - l
        body = body_top - body_bot
        denom = 2 * topwick + 2 * bottomwick + body
        if denom <= 0:
            for x in range(rows):
                overlap = max(0, min(h, levels[x+1]) - max(l, levels[x]))
                if overlap > 0 and h > l:
                    totalvols[x] += v * overlap / (h - l)
            continue
        bodyvol = body * v / denom
        topwickvol = 2 * topwick * v / denom
        bottomwickvol = 2 * bottomwick * v / denom
        for x in range(rows):
            lv_bot, lv_top = levels[x], levels[x+1]
            totalvols[x] += (_get_vol(lv_bot, lv_top, body_bot, body_top, body, bodyvol) +
                             _get_vol(lv_bot, lv_top, body_top, h, topwick, topwickvol) / 2 +
                             _get_vol(lv_bot, lv_top, l, body_bot, bottomwick, bottomwickvol) / 2)
    if totalvols.max() <= 0:
        return None
    poc_idx = int(np.argmax(totalvols))
    poc_level = (levels[poc_idx] + levels[poc_idx + 1]) / 2
    total_target = totalvols.sum() * va_pct / 100.0
    va_accum = totalvols[poc_idx]
    up_idx, dn_idx = poc_idx, poc_idx
    for _ in range(rows):
        if va_accum >= total_target:
            break
        upper = totalvols[up_idx + 1] if up_idx < rows - 1 else 0
        lower = totalvols[dn_idx - 1] if dn_idx > 0 else 0
        if upper == 0 and lower == 0:
            break
        if upper >= lower:
            va_accum += upper
            up_idx += 1
        else:
            va_accum += lower
            dn_idx -= 1
    vah = levels[min(up_idx + 1, rows)]
    val_level = levels[max(dn_idx, 0)]
    return {"poc": round(poc_level, 4), "vah": round(vah, 4), "val": round(val_level, 4)}

def calc_poc_migration(df, short_bars=20, mid_bars=50, long_bars=150, rows=24, va_pct=70.0):
    available = len(df) if df is not None else 0
    s_bars = min(short_bars, available)
    m_bars = min(mid_bars, available)
    l_bars = min(long_bars, available)
    if s_bars < 10:
        return None
    vp_s = calc_volume_profile(df, s_bars, rows, va_pct) if s_bars >= 10 else None
    vp_m = calc_volume_profile(df, m_bars, rows, va_pct) if m_bars >= 20 else None
    vp_l = calc_volume_profile(df, l_bars, rows, va_pct) if l_bars >= 30 else None
    if vp_s is None:
        return None
    poc_s = vp_s['poc']
    poc_m = vp_m['poc'] if vp_m else poc_s
    poc_l = vp_l['poc'] if vp_l else poc_m
    close = float(df.iloc[-1]['Close'])
    high_l = float(df['High'].iloc[-l_bars:].max()) if l_bars > 0 else close
    low_l  = float(df['Low'].iloc[-l_bars:].min()) if l_bars > 0 else close
    price_range = high_l - low_l if high_l > low_l else 1.0

    if poc_s > poc_m and poc_m > poc_l:
        bias, bias_full, bias_color = "ACUM", "ACUMULACIÓN", "#00e676"
        bias_score, bias_bull = 1.5, True
    elif poc_s < poc_m and poc_m < poc_l:
        bias, bias_full, bias_color = "DIST", "DISTRIBUCIÓN", "#ff1744"
        bias_score, bias_bull = -1.0, False
    elif poc_s > poc_l and poc_m <= poc_l:
        bias, bias_full, bias_color = "T.ALC", "TRANSICIÓN ALCISTA", "#1de9b6"
        bias_score, bias_bull = 1.0, True
    elif poc_s < poc_l and poc_m >= poc_l:
        bias, bias_full, bias_color = "T.BAJ", "TRANSICIÓN BAJISTA", "#ff6d00"
        bias_score, bias_bull = -0.5, False
    else:
        poc_spread = max(poc_s, poc_m, poc_l) - min(poc_s, poc_m, poc_l)
        if poc_spread / price_range < 0.05:
            bias, bias_full, bias_color = "CONV", "CONVERGENCIA", "#ffab00"
            bias_score, bias_bull = 0.5, None
        else:
            bias, bias_full, bias_color = "ROT", "ROTACIÓN", "#4a6480"
            bias_score, bias_bull = 0.0, None

    above_count = sum([1 for p in [poc_s, poc_m, poc_l] if close > p])
    pos = "SOBRE" if above_count == 3 else "BAJO" if above_count == 0 else "ENTRE"
    pos_color = "#00e676" if above_count == 3 else "#ff1744" if above_count == 0 else "#ffab00"
    pos_score = 0.5 if above_count == 3 else -0.5 if above_count == 0 else 0.0

    dists = [(abs(close - poc_s), "S", poc_s), (abs(close - poc_m), "M", poc_m), (abs(close - poc_l), "L", poc_l)]
    magnet = min(dists, key=lambda x: x[0])

    return {
        "pocS": round(poc_s, 2), "pocM": round(poc_m, 2), "pocL": round(poc_l, 2),
        "vahS": round(vp_s['vah'], 2), "valS": round(vp_s['val'], 2),
        "vahM": round(vp_m['vah'], 2) if vp_m else None, "valM": round(vp_m['val'], 2) if vp_m else None,
        "vahL": round(vp_l['vah'], 2) if vp_l else None, "valL": round(vp_l['val'], 2) if vp_l else None,
        "bias": bias, "biasF": bias_full, "biasC": bias_color,
        "biasScore": bias_score, "biasBull": bias_bull,
        "pos": pos, "posC": pos_color, "posScore": pos_score,
        "magnet": magnet[1], "magnetPoc": round(magnet[2], 2),
        "magnetDist": round(magnet[0] / close * 100, 2) if close > 0 else 0,
        "barsS": s_bars, "barsM": m_bars, "barsL": l_bars,
    }


# ══════════════════════════════════════════════════════════════
# VSA ENGINE v2 — 8 SEÑALES + MULTI-BAR + TENDENCIA
# ══════════════════════════════════════════════════════════════
def calc_clv(high, low, close):
    spread = high - low
    if spread <= 0: return 0.0
    return ((close - low) - (high - close)) / spread


def calc_trend_context(df, idx=-1):
    """Calcula contexto de tendencia: SMA20, SMA50, posición del precio."""
    n = len(df)
    if n < 20:
        return {"sma20": None, "sma50": None, "trend": "N/A", "above20": None, "above50": None}

    closes = df['Close'].values.astype(float)
    c = closes[idx] if idx == -1 else closes[idx]

    sma20 = float(np.nanmean(closes[-20:])) if n >= 20 else None
    sma50 = float(np.nanmean(closes[-50:])) if n >= 50 else None

    above20 = c > sma20 if sma20 else None
    above50 = c > sma50 if sma50 else None

    if sma20 and sma50:
        if c > sma20 > sma50:
            trend = "UP"
        elif c < sma20 < sma50:
            trend = "DOWN"
        elif c > sma20 and sma20 < sma50:
            trend = "RECOVERING"
        elif c < sma20 and sma20 > sma50:
            trend = "WEAKENING"
        else:
            trend = "LATERAL"
    elif sma20:
        trend = "UP" if c > sma20 else "DOWN"
    else:
        trend = "N/A"

    return {
        "sma20": round(sma20, 2) if sma20 else None,
        "sma50": round(sma50, 2) if sma50 else None,
        "trend": trend,
        "above20": above20,
        "above50": above50,
    }


def classify_signal_v2(clv_val, vol_ratio, spread_pct, is_up, prev_bars, trend):
    """
    VSA expandido: 8 señales con contexto multi-bar y tendencia.
    prev_bars = lista de dicts [{clv, vol_r, spread_pct, is_up, close}, ...]
    """
    wide   = spread_pct > 2.0
    narrow = spread_pct < 1.0
    hi_vol = vol_ratio > 1.4
    lo_vol = vol_ratio < 0.6
    mid_vol = 0.8 <= vol_ratio <= 1.2

    # Contexto previo (2 barras anteriores)
    prev_down = sum(1 for b in prev_bars if not b.get('is_up', True))
    prev_up   = sum(1 for b in prev_bars if b.get('is_up', False))
    prev_hi_vol = sum(1 for b in prev_bars if b.get('vol_r', 1) > 1.4)
    trend_up = trend.get('trend') in ('UP', 'RECOVERING')
    trend_dn = trend.get('trend') in ('DOWN', 'WEAKENING')

    # ── 1. ABSORCIÓN INSTITUCIONAL ────────────────────────────
    # Vol alto + CLV fuerte (cierre near high) + spread amplio
    # Confirmación: viene después de caída (prev_down > 0)
    if hi_vol and clv_val >= 0.65 and wide:
        strength = "FUERTE" if prev_down >= 1 else "NORMAL"
        return dict(k="ABSORCION", c="#00e676", base_score=3.0, bull=True,
                    detail=f"Vol {vol_ratio:.1f}x + CLV {clv_val:.2f} + spread {spread_pct:.1f}%",
                    strength=strength, emoji="⬛")

    # ── 2. UPTHRUST (distribución disfrazada) ─────────────────
    # Barra sube (is_up o high alto) pero cierra abajo (CLV bajo) con vol alto
    # Es lo opuesto a absorción: parece fuerza pero es trampa alcista
    if hi_vol and clv_val <= -0.4 and wide and is_up:
        return dict(k="UPTHRUST", c="#e040fb", base_score=0.5, bull=False,
                    detail=f"Falsa ruptura alcista. CLV {clv_val:.2f} desmiente el high",
                    strength="FUERTE" if prev_up >= 1 else "NORMAL", emoji="⚡")

    # ── 3. TRAMPA / DISTRIBUCIÓN ──────────────────────────────
    # Vol alto + cierre débil + spread amplio (bearish)
    if hi_vol and clv_val <= -0.5 and wide:
        return dict(k="TRAMPA", c="#ff1744", base_score=1.0, bull=False,
                    detail=f"Distribución agresiva. Vol {vol_ratio:.1f}x descargando",
                    strength="FUERTE" if trend_up else "NORMAL", emoji="⚠")

    # ── 4. STOPPING VOLUME (freno de caída) ───────────────────
    # Vol alto + spread amplio + cierre medio-alto + después de caída
    if hi_vol and clv_val >= 0.3 and clv_val < 0.65 and wide and prev_down >= 2:
        return dict(k="STOPPING", c="#7c4dff", base_score=2.5, bull=True,
                    detail=f"Vol alto absorbe venta tras {prev_down} barras down. Posible piso",
                    strength="FUERTE" if clv_val >= 0.5 else "NORMAL", emoji="🛑")

    # ── 5. CLIMAX (agotamiento de movimiento) ─────────────────
    # Vol muy alto + spread amplio + CLV extremo + viene de tendencia prolongada
    if vol_ratio >= 2.0 and wide:
        if clv_val >= 0.7 and prev_up >= 2:
            return dict(k="CLIMAX", c="#ff6d00", base_score=1.5, bull=False,
                        detail=f"Posible buying climax. Vol {vol_ratio:.1f}x tras subas = agotamiento",
                        strength="FUERTE", emoji="🔥")
        if clv_val <= -0.3 and prev_down >= 2:
            return dict(k="CLIMAX", c="#ff6d00", base_score=2.0, bull=True,
                        detail=f"Posible selling climax. Vol {vol_ratio:.1f}x tras caídas = capitulación",
                        strength="FUERTE", emoji="🔥")

    # ── 6. TEST (prueba de oferta/demanda) ────────────────────
    # Vol bajo + spread estrecho/medio + CLV alto + viene de zona de soporte
    # El mercado "testea" si hay vendedores — si no hay (vol bajo), es bull
    if lo_vol and clv_val >= 0.5 and not wide and prev_down >= 1:
        return dict(k="TEST", c="#1de9b6", base_score=2.7, bull=True,
                    detail=f"Test exitoso: baja sin vol ({vol_ratio:.2f}x). Sin vendedores",
                    strength="FUERTE" if trend_up else "NORMAL", emoji="◇")

    # ── 7. COMPRESIÓN (pre-breakout) ──────────────────────────
    # Spread estrecho + vol bajo — DIRECCIÓN depende del contexto
    if narrow and lo_vol:
        if trend_up or clv_val >= 0.3:
            bull = True
            detail = "Compresión en tendencia UP — probablemente continúa"
        elif trend_dn or clv_val <= -0.3:
            bull = False
            detail = "Compresión en tendencia DOWN — probablemente continúa"
        else:
            bull = None
            detail = "Compresión neutral — dirección indefinida hasta breakout"
        return dict(k="COMPRESION", c="#00bcd4", base_score=2.3, bull=bull,
                    detail=detail, strength="NORMAL", emoji="◈")

    # ── 8. NO SUPPLY / NO DEMAND ──────────────────────────────
    # Sube con vol bajo = no supply (bull)
    # Baja con vol bajo = no demand (bear)
    if lo_vol and is_up and clv_val >= 0.4:
        return dict(k="NO SUPPLY", c="#ffab00", base_score=2.3, bull=True,
                    detail=f"Sube sin resistencia de vendedores. Vol {vol_ratio:.2f}x",
                    strength="FUERTE" if trend_up else "NORMAL", emoji="△")

    if lo_vol and not is_up and clv_val <= -0.4:
        return dict(k="NO DEMAND", c="#ff8a65", base_score=1.5, bull=False,
                    detail=f"Baja sin interés comprador. Vol {vol_ratio:.2f}x",
                    strength="FUERTE" if trend_dn else "NORMAL", emoji="▽")

    # ── 9. BATALLA (indecisión con volumen) ───────────────────
    if hi_vol and -0.35 <= clv_val <= 0.35:
        return dict(k="BATALLA", c="#ff6d00", base_score=1.8, bull=None,
                    detail=f"Vol alto ({vol_ratio:.1f}x) + CLV neutro. Esperar resolución",
                    strength="NORMAL", emoji="⚡")

    # ── 10. NEUTRAL ───────────────────────────────────────────
    return dict(k="NEUTRAL", c="#4a6480", base_score=1.5, bull=None,
                detail=f"Sin patrón VSA dominante. CLV {clv_val:.2f}, vol {vol_ratio:.1f}x",
                strength="—", emoji="◦")


def compute_vsa_v2(ticker, df):
    """Calcula VSA v2 + VP Multi-TF. Ya no necesita .info (52w from data)."""
    if df is None or len(df) < 3:
        return None

    df = df.copy().dropna(subset=['Close','High','Low','Volume'])
    if len(df) < 3:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    o = float(last['Open'])
    h = float(last['High'])
    l = float(last['Low'])
    c = float(last['Close'])
    v = float(last['Volume'])

    spread     = h - l
    spread_pct = (spread / l * 100) if l > 0 else 0
    clv_val    = calc_clv(h, l, c)
    chg1d      = ((c - float(prev['Close'])) / float(prev['Close']) * 100) if float(prev['Close']) > 0 else 0
    is_up      = c >= float(prev['Close'])

    # Avg vol (10 barras)
    vols = df['Volume'].iloc[-11:-1].dropna()
    avg_vol = float(vols.mean()) if len(vols) > 0 else v
    vol_ratio = v / avg_vol if avg_vol > 0 else 1.0

    # ── MEJORA: 52w desde data descargada (elimina .info call lenta) ──
    w52h = float(df['High'].iloc[-252:].max()) if len(df) >= 20 else float(df['High'].max())
    w52l = float(df['Low'].iloc[-252:].min()) if len(df) >= 20 else float(df['Low'].min())
    w52pos = ((c - w52l) / (w52h - w52l) * 100) if (w52h > w52l) else 50.0

    # ── MEJORA: Tendencia SMA ──
    trend = calc_trend_context(df)

    # ── MEJORA: Multi-bar context (3 barras previas) ──
    prev_bars = []
    for i in range(max(0, len(df)-4), len(df)-1):
        row = df.iloc[i]
        prev_row = df.iloc[i-1] if i > 0 else row
        p_h, p_l, p_c = float(row['High']), float(row['Low']), float(row['Close'])
        p_v = float(row['Volume'])
        p_clv = calc_clv(p_h, p_l, p_c)
        va = df['Volume'].iloc[max(0,i-10):i].dropna()
        p_avg = float(va.mean()) if len(va) > 0 else p_v
        p_vol_r = p_v / p_avg if p_avg > 0 else 1.0
        p_spread = (p_h - p_l) / p_l * 100 if p_l > 0 else 0
        prev_bars.append({
            "clv": p_clv, "vol_r": p_vol_r, "spread_pct": p_spread,
            "is_up": p_c >= float(prev_row['Close']), "close": p_c
        })

    # ── Señal VSA v2 (expandida) ──
    sig = classify_signal_v2(clv_val, vol_ratio, spread_pct, is_up, prev_bars, trend)

    # ── Volume Profile Multi-TF ──
    vp = calc_poc_migration(df, short_bars=20, mid_bars=50, long_bars=150)

    # ══════════════════════════════════════════════════════════
    # SCORE v2 — Transparente con breakdown
    # ══════════════════════════════════════════════════════════

    # 1. Base VSA (0-3)
    s_vsa = sig['base_score']

    # 2. CLV strength (0-2)
    abs_clv = abs(clv_val)
    s_clv = 2.0 if abs_clv >= 0.7 else 1.4 if abs_clv >= 0.5 else 0.8 if abs_clv >= 0.3 else 0.2

    # 3. Volume conviction (0-2)
    s_vol = 2.0 if vol_ratio >= 2 else 1.7 if vol_ratio >= 1.5 else 1.3 if vol_ratio >= 1.2 else 1.0 if vol_ratio >= 0.8 else 0.5

    # 4. Spread energy (0-1.5)
    s_sp = 1.5 if spread_pct >= 5 else 1.2 if spread_pct >= 3 else 0.8 if spread_pct >= 1.5 else 0.4

    # 5. 52w position (0-1.5) — favorece fuerza relativa
    s_w52 = 1.5 if w52pos >= 80 else 1.1 if w52pos >= 60 else 0.8 if w52pos >= 40 else 0.4

    # 6. VP migration modifier (-1.5 a +2.0)
    vp_mod = 0.0
    if vp:
        vp_mod = vp['biasScore'] + vp['posScore']

    # 7. CONFLUENCIA — VSA y VP dicen lo mismo? (+0.5 a -1.0)
    confluence = 0.0
    confluence_label = "—"
    if vp and sig['bull'] is not None:
        vp_bull = vp.get('biasBull')
        if sig['bull'] == True and vp_bull == True:
            confluence = 0.5
            confluence_label = "✓ ALINEADO BULL"
        elif sig['bull'] == False and vp_bull == False:
            confluence = 0.5
            confluence_label = "✓ ALINEADO BEAR"
        elif sig['bull'] == True and vp_bull == False:
            confluence = -1.0
            confluence_label = "✗ CONFLICTO (VSA↑ VP↓)"
        elif sig['bull'] == False and vp_bull == True:
            confluence = -1.0
            confluence_label = "✗ CONFLICTO (VSA↓ VP↑)"
    elif vp and sig['bull'] is None:
        confluence_label = "◦ VSA NEUTRO"

    # 8. Trend alignment (bonus)
    trend_mod = 0.0
    if sig['bull'] == True and trend.get('trend') == 'UP':
        trend_mod = 0.3
    elif sig['bull'] == False and trend.get('trend') == 'DOWN':
        trend_mod = 0.3
    elif sig['bull'] == True and trend.get('trend') == 'DOWN':
        trend_mod = -0.3
    elif sig['bull'] == False and trend.get('trend') == 'UP':
        trend_mod = -0.3

    raw_score = s_vsa + s_clv + s_vol + s_sp + s_w52 + vp_mod + confluence + trend_mod
    score = min(10.0, max(0.0, round(raw_score, 1)))

    score_breakdown = {
        "vsa": round(s_vsa, 1),
        "clv": round(s_clv, 1),
        "vol": round(s_vol, 1),
        "spread": round(s_sp, 1),
        "w52": round(s_w52, 1),
        "vp": round(vp_mod, 1),
        "confluence": round(confluence, 1),
        "trend": round(trend_mod, 1),
    }

    # ── Historial 10 barras ──
    hist = []
    for i in range(max(0, len(df)-10), len(df)):
        row = df.iloc[i]
        cl = calc_clv(float(row['High']), float(row['Low']), float(row['Close']))
        vA = df['Volume'].iloc[max(0,i-10):i].dropna()
        vAvg = float(vA.mean()) if len(vA) > 0 else float(row['Volume'])
        vR = float(row['Volume']) / vAvg if vAvg > 0 else 1.0
        hist.append({
            "date": str(row.name)[:10], "clv": round(cl, 3), "volR": round(vR, 2),
            "close": round(float(row['Close']), 2),
            "high": round(float(row['High']), 2), "low": round(float(row['Low']), 2),
        })

    # ── Spark 5 barras ──
    spark = []
    for i in range(max(0, len(df)-5), len(df)):
        row = df.iloc[i]
        if i > 0:
            prev_c = float(df.iloc[i-1]['Close'])
            chg = (float(row['Close']) - prev_c) / prev_c * 100 if prev_c > 0 else 0
        else:
            chg = 0
        spark.append({"close": round(float(row['Close']), 2), "chg": round(chg, 2)})

    return {
        "ticker": ticker,
        "o": round(o, 2), "h": round(h, 2), "l": round(l, 2),
        "c": round(c, 2), "v": int(v),
        "spread": round(spread, 2), "spPct": round(spread_pct, 2),
        "clvV": round(clv_val, 3), "chg1d": round(chg1d, 2),
        "avgVol": int(avg_vol), "volR": round(vol_ratio, 2),
        "w52h": round(w52h, 2), "w52l": round(w52l, 2), "w52pos": round(w52pos, 1),
        "sig": sig, "score": score, "scoreBD": score_breakdown,
        "trend": trend, "confluence": confluence_label,
        "hist": hist, "spark": spark, "vp": vp,
    }


# ══════════════════════════════════════════════════════════════
# DATA FETCH — OPTIMIZADO (sin .info calls individuales)
# ══════════════════════════════════════════════════════════════
def fetch_all(universe, period="1y"):
    results = []
    errors  = []
    total   = len(universe)

    print(f"Descargando {total} tickers via yfinance (period={period})...")
    print("─" * 60)

    tickers_list = [t[0] for t in universe]
    meta_map = {t[0]: t for t in universe}

    BATCH = 10
    all_dfs = {}

    for i in range(0, total, BATCH):
        batch = tickers_list[i:i+BATCH]
        batch_n = i // BATCH + 1
        total_batches = (total + BATCH - 1) // BATCH
        print(f"  Batch {batch_n}/{total_batches}: {', '.join(batch)}")
        try:
            data = yf.download(
                batch, period=period, interval="1d",
                group_by='ticker', auto_adjust=True,
                progress=False, threads=True
            )
            for tk in batch:
                try:
                    if len(batch) == 1:
                        all_dfs[tk] = data
                    else:
                        all_dfs[tk] = data[tk] if tk in data.columns.get_level_values(0) else None
                except:
                    all_dfs[tk] = None
        except Exception as e:
            print(f"  ✗ Batch error: {e}")
            for tk in batch:
                all_dfs[tk] = None

    # ── MEJORA: NO más .info calls individuales ──
    # 52w se calcula directamente del dataframe descargado
    print(f"\n  ✓ Download completo. Calculando VSA + VP Multi-TF...")
    print("─" * 60)

    for tk in tickers_list:
        m = meta_map.get(tk, (tk, tk, "Stock", "—"))
        df = all_dfs.get(tk)

        result = compute_vsa_v2(tk, df)
        if result:
            result['name']   = m[1]
            result['cat']    = m[2]
            result['sector'] = m[3]
            results.append(result)
            bull_str = "▲" if result['sig']['bull'] == True else "▼" if result['sig']['bull'] == False else "◦"
            vp_str = result['vp']['bias'] if result.get('vp') else "—"
            trend_str = result['trend']['trend'][:3] if result.get('trend') else "—"
            conf_str = "✓" if "ALINEADO" in result.get('confluence', '') else "✗" if "CONFLICTO" in result.get('confluence', '') else "◦"
            print(f"  {tk:<6} {result['sig']['k']:<12} CLV:{result['clvV']:>6.3f}  Vol:{result['volR']:>5.2f}x  Score:{result['score']:>4.1f}  VP:{vp_str:<6} T:{trend_str:<4} {conf_str} {bull_str}")
        else:
            errors.append(tk)
            print(f"  {tk:<6} ✗ Sin datos")

    print(f"\n{'='*60}")
    print(f"✓ {len(results)} activos procesados · {len(errors)} errores")
    if errors:
        print(f"  Errores: {', '.join(errors)}")

    return results


# ══════════════════════════════════════════════════════════════
# SECTOR SUMMARY
# ══════════════════════════════════════════════════════════════
def calc_sector_summary(data):
    """Agrupa por sector y calcula métricas agregadas."""
    sectors = {}
    for d in data:
        s = d['sector']
        if s not in sectors:
            sectors[s] = {"tickers": [], "scores": [], "bulls": 0, "bears": 0, "acum": 0, "dist": 0}
        sectors[s]['tickers'].append(d['ticker'])
        sectors[s]['scores'].append(d['score'])
        if d['sig']['bull'] == True:
            sectors[s]['bulls'] += 1
        elif d['sig']['bull'] == False:
            sectors[s]['bears'] += 1
        if d.get('vp'):
            if d['vp']['bias'] in ('ACUM', 'T.ALC'):
                sectors[s]['acum'] += 1
            elif d['vp']['bias'] in ('DIST', 'T.BAJ'):
                sectors[s]['dist'] += 1

    summary = []
    for name, info in sectors.items():
        n = len(info['tickers'])
        avg_score = np.mean(info['scores'])
        bias = "BULL" if info['acum'] > info['dist'] else "BEAR" if info['dist'] > info['acum'] else "NEUTRO"
        summary.append({
            "sector": name, "count": n,
            "avgScore": round(avg_score, 1),
            "bulls": info['bulls'], "bears": info['bears'],
            "acum": info['acum'], "dist": info['dist'],
            "bias": bias,
        })

    summary.sort(key=lambda x: x['avgScore'], reverse=True)
    return summary


# ══════════════════════════════════════════════════════════════
# HTML GENERATOR (v4 — con sector heatmap + score breakdown + confluence)
# ══════════════════════════════════════════════════════════════
# El template HTML es largo — se genera con f-string por partes

def generate_html(data, sector_summary, output_file):
    """Genera HTML v4 con todas las mejoras visuales."""

    # Stats
    counts = {}
    vp_counts = {"ACUM":0,"DIST":0,"T.ALC":0,"T.BAJ":0,"CONV":0,"ROT":0}
    bull_count = 0
    top_score, top_ticker = 0, "—"
    confluences = {"aligned_bull":0, "aligned_bear":0, "conflict":0, "neutral":0}

    for d in data:
        k = d['sig']['k']
        counts[k] = counts.get(k, 0) + 1
        if d['sig']['bull'] is True: bull_count += 1
        if d['score'] > top_score:
            top_score  = d['score']
            top_ticker = d['ticker']
        if d.get('vp'):
            b = d['vp']['bias']
            vp_counts[b] = vp_counts.get(b, 0) + 1
        cf = d.get('confluence', '')
        if 'ALINEADO BULL' in cf: confluences['aligned_bull'] += 1
        elif 'ALINEADO BEAR' in cf: confluences['aligned_bear'] += 1
        elif 'CONFLICTO' in cf: confluences['conflict'] += 1
        else: confluences['neutral'] += 1

    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    # numpy types no son JSON serializable — convertir
    class NpEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return super().default(obj)

    json_data = json.dumps(data, ensure_ascii=False, cls=NpEncoder)
    sector_json = json.dumps(sector_summary, ensure_ascii=False, cls=NpEncoder)

    # Sector heatmap HTML
    sector_html = ""
    for s in sector_summary:
        bc = '#00e676' if s['bias'] == 'BULL' else '#ff1744' if s['bias'] == 'BEAR' else '#4a6480'
        sector_html += f'''<div style="background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:8px 10px;min-width:120px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em">{s['sector']}</div>
          <div style="display:flex;justify-content:space-between;margin-top:4px">
            <span style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;color:{bc}">{s['avgScore']}</span>
            <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{bc}">{s['bias']}</span>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--muted);margin-top:2px">▲{s['acum']} ▼{s['dist']} · {s['count']} activos</div>
        </div>'''

    # VSA signal type explanations for JS
    vsa_ex_js = """{
      ABSORCION:{t:'⬛ ABSORCIÓN INSTITUCIONAL',bg:'rgba(0,230,118,.06)',bd:'rgba(0,230,118,.2)',
        txt:d=>`${d.sig.detail}`},
      UPTHRUST:{t:'⚡ UPTHRUST — FALSA RUPTURA',bg:'rgba(224,64,251,.06)',bd:'rgba(224,64,251,.2)',
        txt:d=>`${d.sig.detail}`},
      TRAMPA:{t:'⚠ TRAMPA — DISTRIBUCIÓN',bg:'rgba(255,23,68,.06)',bd:'rgba(255,23,68,.2)',
        txt:d=>`${d.sig.detail}`},
      STOPPING:{t:'🛑 STOPPING VOLUME',bg:'rgba(124,77,255,.06)',bd:'rgba(124,77,255,.2)',
        txt:d=>`${d.sig.detail}`},
      CLIMAX:{t:'🔥 CLIMAX — AGOTAMIENTO',bg:'rgba(255,109,0,.06)',bd:'rgba(255,109,0,.2)',
        txt:d=>`${d.sig.detail}`},
      TEST:{t:'◇ TEST EXITOSO',bg:'rgba(29,233,182,.06)',bd:'rgba(29,233,182,.2)',
        txt:d=>`${d.sig.detail}`},
      COMPRESION:{t:'◈ COMPRESIÓN — PRE-BREAKOUT',bg:'rgba(0,188,212,.06)',bd:'rgba(0,188,212,.2)',
        txt:d=>`${d.sig.detail}`},
      'NO SUPPLY':{t:'△ NO SUPPLY',bg:'rgba(255,171,0,.06)',bd:'rgba(255,171,0,.2)',
        txt:d=>`${d.sig.detail}`},
      'NO DEMAND':{t:'▽ NO DEMAND',bg:'rgba(255,138,101,.06)',bd:'rgba(255,138,101,.2)',
        txt:d=>`${d.sig.detail}`},
      BATALLA:{t:'⚡ BATALLA — INDECISIÓN',bg:'rgba(255,109,0,.06)',bd:'rgba(255,109,0,.2)',
        txt:d=>`${d.sig.detail}`},
      NEUTRAL:{t:'◦ NEUTRAL',bg:'rgba(74,100,128,.06)',bd:'rgba(74,100,128,.2)',
        txt:d=>`${d.sig.detail}`},
    }"""

    vp_ex_js = """{
      ACUM:{t:'▲ ACUMULACIÓN',txt:d=>`POCs: S:$${fmt(d.vp.pocS)} > M:$${fmt(d.vp.pocM)} > L:$${fmt(d.vp.pocL)}`},
      DIST:{t:'▼ DISTRIBUCIÓN',txt:d=>`POCs: S:$${fmt(d.vp.pocS)} < M:$${fmt(d.vp.pocM)} < L:$${fmt(d.vp.pocL)}`},
      'T.ALC':{t:'◆ TRANS. ALCISTA',txt:d=>`POC Short ($${fmt(d.vp.pocS)}) cruzó arriba del Long ($${fmt(d.vp.pocL)})`},
      'T.BAJ':{t:'◆ TRANS. BAJISTA',txt:d=>`POC Short ($${fmt(d.vp.pocS)}) cruzó abajo del Long ($${fmt(d.vp.pocL)})`},
      CONV:{t:'◈ CONVERGENCIA',txt:d=>`POCs comprimidos: S:$${fmt(d.vp.pocS)} · M:$${fmt(d.vp.pocM)} · L:$${fmt(d.vp.pocL)}`},
      ROT:{t:'◈ ROTACIÓN',txt:d=>`POCs sin tendencia: S:$${fmt(d.vp.pocS)} · M:$${fmt(d.vp.pocM)} · L:$${fmt(d.vp.pocL)}`},
    }"""

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BIFS VSA Scanner v4 — {date_str}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600;700&family=Bebas+Neue&family=DM+Sans:wght@300;400;500;600&display=swap');
:root{{--bg:#04060c;--bg2:#080d18;--bg3:#0c1220;--border:#162030;--dim:#1e3050;--green:#00e676;--cyan:#00bcd4;--gold:#ffab00;--red:#ff1744;--orange:#ff6d00;--teal:#1de9b6;--purple:#7c4dff;--pink:#e040fb;--text:#e0ecff;--muted:#4a6480;--white:#f0f8ff;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;font-size:13px;min-height:100vh;overflow-x:hidden;}}
body::after{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,180,255,.01) 3px,rgba(0,180,255,.01) 4px);pointer-events:none;z-index:9999;}}
header{{background:linear-gradient(180deg,#060a18,var(--bg));border-bottom:1px solid var(--border);padding:16px 24px;position:sticky;top:0;z-index:100;backdrop-filter:blur(12px);}}
.hdr{{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;}}
.logo-t{{font-family:'Bebas Neue',sans-serif;font-size:24px;letter-spacing:.12em;color:var(--white);}}
.logo-s{{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--muted);letter-spacing:.15em;text-transform:uppercase;margin-top:1px;}}
.hdr-kpis{{display:flex;gap:18px;flex-wrap:wrap;}}
.hk{{display:flex;flex-direction:column;align-items:flex-end;gap:1px;}}
.hk-l{{font-family:'JetBrains Mono',monospace;font-size:7px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);}}
.hk-v{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;}}
.pill{{display:inline-flex;align-items:center;gap:6px;background:rgba(0,230,118,.08);border:1px solid rgba(0,230,118,.2);padding:4px 12px;border-radius:20px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--green);letter-spacing:.1em;text-transform:uppercase;}}
.ctrl{{display:flex;gap:8px;padding:10px 24px;background:var(--bg2);border-bottom:1px solid var(--border);flex-wrap:wrap;align-items:center;}}
.btn{{padding:6px 14px;border-radius:5px;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;cursor:pointer;border:1px solid transparent;transition:all .15s;background:transparent;color:var(--muted);}}
.btn-o{{border-color:var(--border);}}
.btn-o:hover,.btn-o.act{{border-color:var(--cyan);color:var(--cyan);background:rgba(0,188,212,.08);}}
.inp{{max-width:220px;background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:6px 11px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text);outline:none;}}
.inp:focus{{border-color:var(--cyan);}}
.inp::placeholder{{color:var(--muted);}}
.sel{{background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:6px 10px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text);cursor:pointer;outline:none;}}
.sector-bar{{display:flex;gap:6px;padding:10px 24px;overflow-x:auto;border-bottom:1px solid var(--border);background:var(--bg);}}
.stats{{display:flex;gap:1px;background:var(--border);border-bottom:1px solid var(--border);}}
.sc{{flex:1;background:var(--bg2);padding:8px 14px;}}
.sc-l{{font-family:'JetBrains Mono',monospace;font-size:7px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);}}
.sc-v{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;margin-top:1px;}}
.tw{{overflow-x:auto;}}
table{{width:100%;border-collapse:collapse;min-width:1450px;}}
thead tr{{background:var(--bg3);position:sticky;top:84px;z-index:50;}}
thead th{{padding:8px 10px;font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);text-align:left;border-bottom:1px solid var(--dim);cursor:pointer;white-space:nowrap;user-select:none;}}
thead th:hover{{color:var(--cyan);}}
tbody tr{{border-bottom:1px solid rgba(22,32,48,.6);transition:background .1s;cursor:pointer;}}
tbody tr:hover{{background:rgba(0,188,212,.04);}}
tbody tr.hi{{background:rgba(0,188,212,.07)!important;}}
td{{padding:9px 10px;vertical-align:middle;white-space:nowrap;}}
.tk-m{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;}}
.tk-n{{font-size:9px;color:var(--muted);margin-top:1px;}}
.tk-s{{font-size:8px;color:var(--dim);}}
.clv-b{{display:inline-flex;align-items:center;justify-content:center;padding:4px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:12px;min-width:62px;text-align:center;}}
.vc{{display:flex;flex-direction:column;gap:3px;}}
.vb{{width:76px;height:6px;background:var(--border);border-radius:3px;overflow:hidden;position:relative;}}
.vbf{{height:100%;border-radius:3px;}}
.val{{position:absolute;top:0;bottom:0;width:2px;background:rgba(255,255,255,.25);border-radius:1px;}}
.vn{{font-family:'JetBrains Mono',monospace;font-size:10px;}}
.vd{{font-family:'JetBrains Mono',monospace;font-size:9px;}}
.w52b{{width:76px;height:5px;background:var(--border);border-radius:3px;position:relative;overflow:hidden;}}
.w52g{{position:absolute;inset:0;background:linear-gradient(90deg,var(--red),var(--gold) 50%,var(--green));}}
.w52p{{position:absolute;top:-3px;width:3px;height:11px;background:white;border-radius:2px;transform:translateX(-50%);}}
.w52t{{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);}}
.sig{{padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:.06em;display:inline-block;white-space:nowrap;}}
.scc{{display:flex;align-items:center;gap:6px;}}
.scn{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:16px;}}
.scb{{width:46px;height:5px;background:var(--border);border-radius:3px;overflow:hidden;}}
.scbf{{height:100%;border-radius:3px;}}
.spk{{display:flex;align-items:flex-end;gap:2px;}}
.spkb{{width:5px;border-radius:2px 2px 0 0;min-height:3px;}}
.vp-badge{{padding:3px 8px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:.06em;display:inline-block;white-space:nowrap;}}
.vp-pos{{font-family:'JetBrains Mono',monospace;font-size:8px;margin-top:2px;}}
.poc-vis{{position:relative;width:60px;height:24px;background:var(--border);border-radius:3px;overflow:hidden;margin-top:3px;}}
.poc-mk{{position:absolute;width:2px;height:100%;border-radius:1px;top:0;}}
.poc-pr{{position:absolute;top:0;left:0;bottom:0;width:1px;background:rgba(255,255,255,.4);}}
.trend-badge{{padding:2px 6px;border-radius:3px;font-family:'JetBrains Mono',monospace;font-weight:700;font-size:8px;text-transform:uppercase;letter-spacing:.06em;display:inline-block;}}
.conf-icon{{font-size:11px;}}
.dp{{display:none;position:fixed;right:0;top:0;bottom:0;width:400px;background:var(--bg2);border-left:1px solid var(--border);z-index:200;overflow-y:auto;padding:18px;box-shadow:-20px 0 60px rgba(0,0,0,.6);}}
.dp.open{{display:block;animation:si .2s ease;}}
@keyframes si{{from{{transform:translateX(100%)}}to{{transform:translateX(0)}}}}
.dp-x{{position:absolute;top:12px;right:14px;background:none;border:none;color:var(--muted);font-size:16px;cursor:pointer;}}
.dp-x:hover{{color:var(--text);}}
.dp-tk{{font-family:'Bebas Neue',sans-serif;font-size:32px;color:var(--white);letter-spacing:.06em;margin-top:4px;}}
.dp-nm{{font-size:10px;color:var(--muted);margin-bottom:12px;}}
.dp-pr{{display:flex;gap:14px;margin-bottom:14px;}}
.dp-price{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:26px;}}
.dp-chg{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;margin-top:8px;}}
.dp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-bottom:14px;}}
.dp-c{{background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:9px 11px;}}
.dp-cl{{font-family:'JetBrains Mono',monospace;font-size:7px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin-bottom:2px;}}
.dp-cv{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:14px;}}
.dp-vb{{padding:11px 13px;border-radius:6px;border:1px solid;margin-bottom:12px;}}
.dp-vt{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:9px;text-transform:uppercase;letter-spacing:.1em;margin-bottom:5px;}}
.dp-vx{{font-size:11px;line-height:1.65;color:#7e9ab8;}}
.dp-vx strong{{color:var(--text);}}
.dp-ht{{font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:8px;}}
.dp-bars{{display:flex;flex-direction:column;gap:3px;}}
.dp-br{{display:grid;grid-template-columns:55px 1fr 46px 52px;gap:6px;align-items:center;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);}}
.dp-cbg{{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden;}}
.dp-cf{{height:100%;border-radius:3px;}}
.dp-vp-section{{background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:12px;margin-bottom:14px;}}
.dp-vp-title{{font-family:'JetBrains Mono',monospace;font-size:8px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin-bottom:10px;}}
.dp-vp-row{{display:grid;grid-template-columns:60px 1fr 70px;gap:8px;align-items:center;margin-bottom:6px;font-family:'JetBrains Mono',monospace;font-size:10px;}}
.dp-vp-label{{font-size:8px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);}}
.dp-vp-bar{{height:8px;background:var(--border);border-radius:4px;position:relative;overflow:visible;}}
.dp-vp-mk{{position:absolute;top:-2px;width:4px;height:12px;border-radius:2px;transform:translateX(-50%);}}
.dp-vp-val{{font-weight:700;text-align:right;}}
.dp-vp-bias{{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:5px;margin-top:8px;}}
.dp-vp-bias-txt{{font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.06em;}}
.dp-vp-bias-sub{{font-size:9px;color:var(--muted);margin-top:2px;}}
.score-bd{{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin-bottom:14px;}}
.score-bd-item{{background:var(--bg3);border:1px solid var(--border);border-radius:4px;padding:6px 8px;text-align:center;}}
.score-bd-l{{font-family:'JetBrains Mono',monospace;font-size:6px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);}}
.score-bd-v{{font-family:'JetBrains Mono',monospace;font-weight:700;font-size:12px;margin-top:2px;}}
.g{{color:var(--green);}} .c{{color:var(--cyan);}} .gd{{color:var(--gold);}}
.r{{color:var(--red);}} .m{{color:var(--muted);}} .w{{color:var(--white);font-weight:700;}}
</style>
</head>
<body>
<header>
  <div class="hdr">
    <div>
      <div class="logo-t">BIFS VSA SCANNER v4</div>
      <div class="logo-s">VSA v2 (8 señales) + Volume Profile Multi-TF + Confluencia · {date_str}</div>
    </div>
    <div class="hdr-kpis">
      <div class="hk"><span class="hk-l">Activos</span><span class="hk-v c" id="cnt">{len(data)}</span></div>
      <div class="hk"><span class="hk-l">Bull</span><span class="hk-v g">{bull_count}</span></div>
      <div class="hk"><span class="hk-l">Confluencia ✓</span><span class="hk-v g">{confluences['aligned_bull']}</span></div>
      <div class="hk"><span class="hk-l">Conflicto ✗</span><span class="hk-v r">{confluences['conflict']}</span></div>
      <div class="hk"><span class="hk-l">Top</span><span class="hk-v gd">{top_score} {top_ticker}</span></div>
      <div class="pill">v4 · 8 SEÑALES · CONFLUENCIA</div>
    </div>
  </div>
</header>
<div class="ctrl">
  <input class="inp" id="search" placeholder="Ticker / nombre / sector..." oninput="applyFilter()"/>
  <select class="sel" id="sfield" onchange="applyFilter()">
    <option value="score">Score ↓</option>
    <option value="clvV">CLV ↓</option>
    <option value="volR">Vol vs Avg ↓</option>
    <option value="chg1d">Cambio 1D ↓</option>
    <option value="w52pos">Pos 52w ↓</option>
  </select>
  <button class="btn btn-o act" onclick="setF('all',this)">TODO</button>
  <button class="btn btn-o" onclick="setF('bull',this)">BULL</button>
  <button class="btn btn-o" onclick="setF('bear',this)">BEAR</button>
  <button class="btn btn-o" onclick="setF('acum',this)">▲ ACUM</button>
  <button class="btn btn-o" onclick="setF('dist',this)">▼ DIST</button>
  <button class="btn btn-o" onclick="setF('conf_bull',this)">✓ CONFLUENCIA</button>
  <button class="btn btn-o" onclick="setF('conflict',this)">✗ CONFLICTO</button>
  <button class="btn btn-o" onclick="setF('etf',this)">ETF</button>
  <button class="btn btn-o" onclick="setF('arg',this)">ARG</button>
  <span style="margin-left:4px;border-left:1px solid var(--border);padding-left:8px"></span>
  <button class="btn btn-o" onclick="setF('t_liquidar',this)" style="color:#ff1744;border-color:#ff174444">LIQUIDAR</button>
  <button class="btn btn-o" onclick="setF('t_reducir',this)" style="color:#ff6d00;border-color:#ff6d0044">REDUCIR</button>
  <button class="btn btn-o" onclick="setF('t_aumentar',this)" style="color:#00e676;border-color:#00e67644">AUMENTAR</button>
</div>
<div class="sector-bar">{sector_html}</div>
<div class="stats">
  <div class="sc"><div class="sc-l">Absorción</div><div class="sc-v g">{counts.get("ABSORCION",0)}</div></div>
  <div class="sc"><div class="sc-l">Test/Stopping</div><div class="sc-v" style="color:var(--purple)">{counts.get("TEST",0)+counts.get("STOPPING",0)}</div></div>
  <div class="sc"><div class="sc-l">Compresión</div><div class="sc-v c">{counts.get("COMPRESION",0)}</div></div>
  <div class="sc"><div class="sc-l">No Supply</div><div class="sc-v gd">{counts.get("NO SUPPLY",0)}</div></div>
  <div class="sc"><div class="sc-l">Trampa/Upthrust</div><div class="sc-v r">{counts.get("TRAMPA",0)+counts.get("UPTHRUST",0)}</div></div>
  <div class="sc"><div class="sc-l">Climax</div><div class="sc-v" style="color:var(--orange)">{counts.get("CLIMAX",0)}</div></div>
  <div class="sc"><div class="sc-l">VP ▲</div><div class="sc-v g">{vp_counts.get("ACUM",0)+vp_counts.get("T.ALC",0)}</div></div>
  <div class="sc"><div class="sc-l">VP ▼</div><div class="sc-v r">{vp_counts.get("DIST",0)+vp_counts.get("T.BAJ",0)}</div></div>
</div>
<div class="tw">
<table>
<thead><tr>
  <th>#</th><th onclick="sortBy('ticker')">TICKER</th><th onclick="sortBy('c')">PRECIO</th>
  <th onclick="sortBy('chg1d')">1D%</th><th onclick="sortBy('clvV')">CLV</th>
  <th onclick="sortBy('volR')">VOL</th><th onclick="sortBy('w52pos')">52W</th>
  <th>TREND</th><th>5D</th><th onclick="sortBy('sigK')">VSA</th>
  <th>VP</th><th>CONF</th><th>TRANSICIÓN</th><th onclick="sortBy('score')">SCORE</th>
</tr></thead>
<tbody id="tbody"></tbody>
</table>
</div>
<div class="dp" id="dp">
  <button class="dp-x" onclick="closeDP()">✕</button>
  <div class="dp-tk" id="dptk">—</div>
  <div class="dp-nm" id="dpnm">—</div>
  <div class="dp-pr">
    <div class="dp-price" id="dppr">—</div>
    <div class="dp-chg" id="dpch">—</div>
  </div>
  <div class="dp-grid" id="dpgrid"></div>
  <div class="dp-ht">SCORE BREAKDOWN</div>
  <div class="score-bd" id="dpscorebd"></div>
  <div class="dp-vb" id="dpvb">
    <div class="dp-vt" id="dpvt">—</div>
    <div class="dp-vx" id="dpvx">—</div>
  </div>
  <div class="dp-vp-section" id="dpvps">
    <div class="dp-vp-title">VOLUME PROFILE · MIGRACIÓN INSTITUCIONAL</div>
    <div id="dpvp-content"></div>
  </div>
  <div class="dp-ht">HISTORIAL 10 DÍAS</div>
  <div class="dp-bars" id="dpbars"></div>
</div>
<script>
const RAW={json_data};
let allData=RAW,filtData=[...RAW],curF='all',selTk=null;
const fmt=(n,d=2)=>n==null?'—':n.toFixed(d);
const fmtV=n=>!n?'—':n>=1e9?(n/1e9).toFixed(1)+'B':n>=1e6?(n/1e6).toFixed(1)+'M':n>=1e3?(n/1e3).toFixed(0)+'K':String(n);
const clvStyle=v=>v>=0.7?{{bg:'rgba(0,230,118,.12)',c:'#00e676',bd:'rgba(0,230,118,.3)'}}:v>=0.5?{{bg:'rgba(0,188,212,.1)',c:'#00bcd4',bd:'rgba(0,188,212,.25)'}}:v>=0.3?{{bg:'rgba(255,171,0,.1)',c:'#ffab00',bd:'rgba(255,171,0,.25)'}}:v>=-0.3?{{bg:'rgba(74,100,128,.08)',c:'#4a6480',bd:'rgba(74,100,128,.2)'}}:{{bg:'rgba(255,23,68,.12)',c:'#ff1744',bd:'rgba(255,23,68,.3)'}};
const volC=r=>r>=2?'#00e676':r>=1.5?'#1de9b6':r>=1.2?'#00bcd4':r>=0.8?'#ffab00':'#4a6480';
const scoreC=s=>s>=8?'#00e676':s>=6?'#00bcd4':s>=4?'#ffab00':'#ff1744';
const trendC=t=>t==='UP'?'#00e676':t==='DOWN'?'#ff1744':t==='RECOVERING'?'#1de9b6':t==='WEAKENING'?'#ff6d00':'#4a6480';
const confIcon=c=>c.includes('ALINEADO BULL')?'✓':c.includes('ALINEADO BEAR')?'✓':c.includes('CONFLICTO')?'✗':'◦';
const confColor=c=>c.includes('ALINEADO BULL')?'#00e676':c.includes('ALINEADO BEAR')?'#ff1744':c.includes('CONFLICTO')?'#e040fb':'#4a6480';

const VSA_EX={vsa_ex_js};
const VP_EX={vp_ex_js};

function setF(f,btn){{curF=f;document.querySelectorAll('.ctrl .btn').forEach(b=>b.classList.remove('act'));btn.classList.add('act');applyFilter();}}
function applyFilter(){{
  const q=document.getElementById('search').value.toLowerCase();
  const sf=document.getElementById('sfield').value;
  let d=[...allData];
  if(curF==='bull') d=d.filter(x=>x.sig.bull===true);
  if(curF==='bear') d=d.filter(x=>x.sig.bull===false);
  if(curF==='etf')  d=d.filter(x=>x.cat==='ETF');
  if(curF==='arg')  d=d.filter(x=>(x.sector||'').startsWith('Arg'));
  if(curF==='acum') d=d.filter(x=>x.vp&&(x.vp.bias==='ACUM'||x.vp.bias==='T.ALC'));
  if(curF==='dist') d=d.filter(x=>x.vp&&(x.vp.bias==='DIST'||x.vp.bias==='T.BAJ'));
  if(curF==='conf_bull') d=d.filter(x=>(x.confluence||'').includes('ALINEADO'));
  if(curF==='conflict') d=d.filter(x=>(x.confluence||'').includes('CONFLICTO'));
  if(curF==='t_liquidar') d=d.filter(x=>x.transition&&x.transition.action==='LIQUIDAR');
  if(curF==='t_reducir') d=d.filter(x=>x.transition&&(x.transition.action==='REDUCIR'||x.transition.action==='AJUSTAR STOP'));
  if(curF==='t_aumentar') d=d.filter(x=>x.transition&&(x.transition.action==='AUMENTAR'||x.transition.action==='ENTRAR'));
  if(q) d=d.filter(x=>x.ticker.toLowerCase().includes(q)||(x.name||'').toLowerCase().includes(q)||(x.sector||'').toLowerCase().includes(q));
  filtData=d;
  filtData.sort((a,b)=>{{let av=a[sf]??0,bv=b[sf]??0;if(sf==='ticker')return String(av)<String(bv)?-1:1;return bv-av;}});
  render();
}}
function sortBy(f){{const m={{score:'score',clvV:'clvV',volR:'volR',chg1d:'chg1d',w52pos:'w52pos',ticker:'ticker'}};if(m[f])document.getElementById('sfield').value=m[f];applyFilter();}}

function render(){{
  const tbody=document.getElementById('tbody');
  document.getElementById('cnt').textContent=filtData.length;
  if(!filtData.length){{tbody.innerHTML='<tr><td colspan="14" style="text-align:center;padding:30px;color:var(--muted)">Sin resultados</td></tr>';return;}}
  tbody.innerHTML=filtData.map((d,i)=>{{
    const cc=d.chg1d>=0?'#00e676':'#ff1744',cs=d.chg1d>=0?'+':'';
    const cv=clvStyle(d.clvV),vc=volC(d.volR),sc=scoreC(d.score);
    const vPct=Math.min(98,(d.volR/3)*100);
    const maxC=Math.max(...d.spark.map(b=>b.close)),minC=Math.min(...d.spark.map(b=>b.close));
    const spk=d.spark.map(b=>{{const h2=maxC===minC?10:Math.max(3,((b.close-minC)/(maxC-minC))*18);return `<div class="spkb" style="height:${{h2}}px;background:${{b.chg>=0?'#00e676':'#ff1744'}}"></div>`;}}).join('');
    const tr=d.trend||{{}};const tc=trendC(tr.trend||'');
    let vpHtml='<span class="m">—</span>';
    if(d.vp){{const vp=d.vp;const allPocs=[vp.pocS,vp.pocM,vp.pocL,d.c];const pMin=Math.min(...allPocs)*0.998,pMax=Math.max(...allPocs)*1.002,pRng=pMax-pMin||1;
      vpHtml=`<div><span class="vp-badge" style="background:${{vp.biasC}}22;color:${{vp.biasC}};border:1px solid ${{vp.biasC}}44">${{vp.bias}}</span>
      <div class="vp-pos" style="color:${{vp.posC}}">${{vp.pos}}</div>
      <div class="poc-vis"><div class="poc-pr" style="left:${{((d.c-pMin)/pRng*100).toFixed(1)}}%"></div>
        <div class="poc-mk" style="left:${{((vp.pocL-pMin)/pRng*100).toFixed(1)}}%;background:#ff1744;opacity:.7"></div>
        <div class="poc-mk" style="left:${{((vp.pocM-pMin)/pRng*100).toFixed(1)}}%;background:#ff9800;opacity:.8"></div>
        <div class="poc-mk" style="left:${{((vp.pocS-pMin)/pRng*100).toFixed(1)}}%;background:#00e5ff"></div></div></div>`;}}
    const ci=confIcon(d.confluence||''),cclr=confColor(d.confluence||'');
    return `<tr data-tk="${{d.ticker}}" onclick="openDP('${{d.ticker}}')" class="${{d.ticker===selTk?'hi':''}}">
      <td style="font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted)">${{i+1}}</td>
      <td><div class="tk-m" style="color:${{d.sig.c}}">${{d.ticker}}</div><div class="tk-n">${{d.name}}</div><div class="tk-s">${{d.cat}} · ${{d.sector}}</div></td>
      <td style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:12px">$${{fmt(d.c)}}</td>
      <td style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:13px;color:${{cc}}">${{cs}}${{fmt(d.chg1d)}}%</td>
      <td><div class="clv-b" style="background:${{cv.bg}};color:${{cv.c}};border:1px solid ${{cv.bd}}">${{fmt(d.clvV,3)}}</div></td>
      <td><div class="vc"><div class="vn" style="color:${{vc}}">${{fmt(d.volR,2)}}x</div>
        <div class="vb"><div class="vbf" style="width:${{Math.min(100,vPct)}}%;background:${{vc}}"></div></div>
        <div class="vd" style="color:${{vc}}">${{fmtV(d.v)}}</div></div></td>
      <td><div class="w52b"><div class="w52g"></div><div class="w52p" style="left:${{Math.min(96,Math.max(4,d.w52pos))}}%"></div></div>
        <div class="w52t">${{fmt(d.w52pos,0)}}%</div></td>
      <td><span class="trend-badge" style="background:${{tc}}18;color:${{tc}};border:1px solid ${{tc}}44">${{(tr.trend||'—').slice(0,3)}}</span></td>
      <td><div class="spk">${{spk}}</div></td>
      <td><span class="sig" style="background:${{d.sig.c}}22;color:${{d.sig.c}};border:1px solid ${{d.sig.c}}44">${{d.sig.emoji||''}} ${{d.sig.k}}</span></td>
      <td>${{vpHtml}}</td>
      <td><span class="conf-icon" style="color:${{cclr}};font-size:14px;font-weight:700">${{ci}}</span></td>
      <td>${{(()=>{{const t=d.transition||{{}};return t.action?`<div style="font-family:'JetBrains Mono',monospace"><div style="font-size:9px;font-weight:700;color:${{t.actionC||'#4a6480'}}">${{t.action}}</div><div style="font-size:7px;color:var(--muted);margin-top:1px">${{t.delta||''}}</div></div>`:'<span class="m">—</span>';}})()}}</td>
      <td><div class="scc"><div class="scn" style="color:${{sc}}">${{d.score}}</div><div class="scb"><div class="scbf" style="width:${{d.score*10}}%;background:${{sc}}"></div></div></div></td>
    </tr>`;
  }}).join('');
}}

function openDP(ticker){{
  const d=allData.find(x=>x.ticker===ticker);if(!d)return;
  selTk=ticker;
  const cc=d.chg1d>=0?'#00e676':'#ff1744',cs=d.chg1d>=0?'+':'';
  const cv=clvStyle(d.clvV),sc=scoreC(d.score);
  document.getElementById('dptk').textContent=ticker;
  document.getElementById('dpnm').textContent=`${{d.name}} · ${{d.sector}} · Trend: ${{(d.trend||{{}}).trend||'—'}}`;
  document.getElementById('dppr').textContent=`$${{fmt(d.c)}}`;
  document.getElementById('dpch').style.color=cc;document.getElementById('dpch').textContent=`${{cs}}${{fmt(d.chg1d)}}%`;
  document.getElementById('dpgrid').innerHTML=`
    <div class="dp-c"><div class="dp-cl">CLV</div><div class="dp-cv" style="color:${{cv.c}}">${{fmt(d.clvV,3)}}</div></div>
    <div class="dp-c"><div class="dp-cl">Spread%</div><div class="dp-cv">${{fmt(d.spPct,1)}}%</div></div>
    <div class="dp-c"><div class="dp-cl">Vol / Avg</div><div class="dp-cv" style="color:${{volC(d.volR)}}">${{fmt(d.volR,2)}}x</div></div>
    <div class="dp-c"><div class="dp-cl">Score</div><div class="dp-cv" style="color:${{sc}}">${{d.score}}</div></div>
    <div class="dp-c"><div class="dp-cl">52w Range</div><div class="dp-cv">${{fmt(d.w52pos,0)}}%</div></div>
    <div class="dp-c"><div class="dp-cl">Confluencia</div><div class="dp-cv" style="color:${{confColor(d.confluence||'')}}">${{d.confluence||'—'}}</div></div>
    <div class="dp-c"><div class="dp-cl">SMA20</div><div class="dp-cv">${{d.trend&&d.trend.sma20?'$'+fmt(d.trend.sma20):'—'}}</div></div>
    <div class="dp-c"><div class="dp-cl">SMA50</div><div class="dp-cv">${{d.trend&&d.trend.sma50?'$'+fmt(d.trend.sma50):'—'}}</div></div>`;
  // Score breakdown
  if(d.scoreBD){{const bd=d.scoreBD;document.getElementById('dpscorebd').innerHTML=
    Object.entries(bd).map(([k,v])=>{{const c2=v>0?'#00e676':v<0?'#ff1744':'#4a6480';
      return `<div class="score-bd-item"><div class="score-bd-l">${{k}}</div><div class="score-bd-v" style="color:${{c2}}">${{v>0?'+':''}}${{v}}</div></div>`;
    }}).join('');}}
  // Transition info
  const t=d.transition||{{}};
  if(t.action && t.action!=='—'){{
    const prevInfo=t.prev_score!=null?`<div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);margin-top:6px">Scan anterior: Score ${{t.prev_score}} · VP ${{t.prev_vp||'—'}} · ${{t.prev_sig||'—'}}${{t.price_change!=null?' · Precio '+( t.price_change>=0?'+':'')+t.price_change+'%':''}}</div>`:'';
    document.getElementById('dpscorebd').innerHTML+=`<div style="grid-column:1/-1;background:${{t.actionC}}11;border:1px solid ${{t.actionC}}33;border-radius:5px;padding:8px 10px;margin-top:4px">
      <div style="font-family:'JetBrains Mono',monospace;font-weight:700;font-size:11px;color:${{t.actionC}}">${{t.delta}} → ${{t.action}}</div>
      <div style="font-size:10px;color:var(--muted);margin-top:3px;line-height:1.5">${{t.detail}}</div>${{prevInfo}}</div>`;
  }}
  const ex=VSA_EX[d.sig.k]||VSA_EX.NEUTRAL;const vb=document.getElementById('dpvb');
  vb.style.background=ex.bg;vb.style.borderColor=ex.bd;
  document.getElementById('dpvt').style.color=d.sig.c;document.getElementById('dpvt').textContent=ex.t;
  document.getElementById('dpvx').innerHTML=ex.txt(d);
  const vpDiv=document.getElementById('dpvp-content');
  if(d.vp){{const vp=d.vp;const vpEx=VP_EX[vp.bias]||VP_EX.ROT;
    const allP=[vp.pocS,vp.pocM,vp.pocL,d.c];const pMin=Math.min(...allP)*0.998,pMax=Math.max(...allP)*1.002,pRng=pMax-pMin||1;
    const pctOf=v=>((v-pMin)/pRng*100).toFixed(1);
    vpDiv.innerHTML=`
      <div class="dp-vp-row"><div class="dp-vp-label" style="color:#00e5ff">POC Short</div><div class="dp-vp-bar"><div class="dp-vp-mk" style="left:${{pctOf(vp.pocS)}}%;background:#00e5ff"></div></div><div class="dp-vp-val" style="color:#00e5ff">$${{fmt(vp.pocS)}}</div></div>
      <div class="dp-vp-row"><div class="dp-vp-label" style="color:#ff9800">POC Mid</div><div class="dp-vp-bar"><div class="dp-vp-mk" style="left:${{pctOf(vp.pocM)}}%;background:#ff9800"></div></div><div class="dp-vp-val" style="color:#ff9800">$${{fmt(vp.pocM)}}</div></div>
      <div class="dp-vp-row"><div class="dp-vp-label" style="color:#ff1744">POC Long</div><div class="dp-vp-bar"><div class="dp-vp-mk" style="left:${{pctOf(vp.pocL)}}%;background:#ff1744"></div></div><div class="dp-vp-val" style="color:#ff1744">$${{fmt(vp.pocL)}}</div></div>
      <div class="dp-vp-row"><div class="dp-vp-label" style="color:rgba(255,255,255,.5)">PRECIO</div><div class="dp-vp-bar"><div class="dp-vp-mk" style="left:${{pctOf(d.c)}}%;background:white"></div></div><div class="dp-vp-val" style="color:white">$${{fmt(d.c)}}</div></div>
      <div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted)">Imán: POC ${{vp.magnet}} ($${{fmt(vp.magnetPoc)}}) · ${{fmt(vp.magnetDist)}}% dist</div>
      <div class="dp-vp-bias" style="background:${{vp.biasC}}11;border:1px solid ${{vp.biasC}}33;margin-top:10px">
        <div><div class="dp-vp-bias-txt" style="color:${{vp.biasC}}">${{vpEx.t}}</div><div class="dp-vp-bias-sub">${{vpEx.txt(d)}}</div></div></div>`;
  }}else{{vpDiv.innerHTML='<div style="color:var(--muted)">Sin datos VP</div>';}}
  document.getElementById('dpbars').innerHTML=d.hist.map(b=>{{
    const pct=Math.max(0,Math.min(100,(b.clv+1)/2*100));
    const clvC=b.clv>=0.5?'#00e676':b.clv>=0?'#ffab00':'#ff1744';
    const vC=b.volR>=1.5?'#00e676':b.volR>=1?'#00bcd4':'#4a6480';
    return `<div class="dp-br"><span>${{b.date.slice(5)}}</span><div style="display:flex;align-items:center;gap:4px;flex:1"><div class="dp-cbg"><div class="dp-cf" style="width:${{pct}}%;background:${{clvC}}"></div></div><span style="color:${{clvC}};font-size:9px;min-width:34px">${{fmt(b.clv,3)}}</span></div><span style="color:${{vC}}">${{fmt(b.volR,2)}}x</span><span>$${{fmt(b.close)}}</span></div>`;
  }}).join('');
  document.getElementById('dp').classList.add('open');
  document.querySelectorAll('tbody tr').forEach(r=>r.classList.remove('hi'));
  const row=document.querySelector(`tr[data-tk="${{ticker}}"]`);if(row){{row.classList.add('hi');row.scrollIntoView({{block:'nearest',behavior:'smooth'}});}}
}}
function closeDP(){{document.getElementById('dp').classList.remove('open');selTk=null;document.querySelectorAll('tbody tr').forEach(r=>r.classList.remove('hi'));}}
document.addEventListener('keydown',e=>{{if(e.key==='Escape')closeDP();}});
applyFilter();
</script>
</body>
</html>'''

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✓ Archivo generado: {output_file}")
    try:
        from google.colab import files
        files.download(output_file)
        print("✓ Descarga iniciada")
    except ImportError:
        print(f"Abrí: {output_file}")
    return output_file


# ══════════════════════════════════════════════════════════════
# SIGNAL HISTORY & TRANSITION TRACKING
# ══════════════════════════════════════════════════════════════

HISTORY_DIR = None  # Se configura al correr (Google Drive si está disponible)

def setup_history_dir():
    """Configura la carpeta de historial según el entorno."""
    global HISTORY_DIR

    # 1. GitHub Actions — usa env var
    if os.environ.get("GITHUB_ACTIONS"):
        HISTORY_DIR = os.environ.get("HISTORY_DIR", "bifs_scan_history")
        os.makedirs(HISTORY_DIR, exist_ok=True)
        print(f"  ✓ Historial GitHub Actions: {HISTORY_DIR}")
        return HISTORY_DIR

    # 2. Google Colab — usa Drive
    try:
        from google.colab import drive
        drive.mount('/content/drive', force_remount=False)
        HISTORY_DIR = "/content/drive/MyDrive/BIFS/scan_history"
        os.makedirs(HISTORY_DIR, exist_ok=True)
        print(f"  ✓ Historial en Google Drive: {HISTORY_DIR}")
    except ImportError:
        # 3. Local
        HISTORY_DIR = "bifs_scan_history"
        os.makedirs(HISTORY_DIR, exist_ok=True)
        print(f"  Historial local: {HISTORY_DIR}")
    return HISTORY_DIR

# ── Reglas de transición ─────────────────────────────────────
# Cada ticker tiene un estado compuesto: (VSA_bull, VP_bias, score)
# Las transiciones entre estados generan acciones

VP_RANK = {"DIST": 0, "T.BAJ": 1, "ROT": 2, "CONV": 3, "T.ALC": 4, "ACUM": 5}

def classify_transition(prev, curr):
    """
    Compara señal previa vs actual y genera recomendación.
    Retorna dict con: delta, action, action_color, detail
    """
    if prev is None:
        return {"delta": "NUEVO", "action": "EVALUAR", "actionC": "#00bcd4",
                "detail": "Primera aparición en el scanner"}

    p_vp = prev.get('vp_bias', 'ROT')
    c_vp = curr.get('vp', {}).get('bias', 'ROT') if curr.get('vp') else 'ROT'
    p_score = prev.get('score', 0)
    c_score = curr.get('score', 0)
    p_bull = prev.get('sig_bull')
    c_bull = curr.get('sig', {}).get('bull')
    p_sig = prev.get('sig_k', 'NEUTRAL')
    c_sig = curr.get('sig', {}).get('k', 'NEUTRAL')

    p_vp_rank = VP_RANK.get(p_vp, 2)
    c_vp_rank = VP_RANK.get(c_vp, 2)
    vp_delta = c_vp_rank - p_vp_rank
    score_delta = c_score - p_score

    # ── REVERSAL: VP flipped direction ────────────────────
    if p_vp in ('ACUM', 'T.ALC') and c_vp in ('DIST', 'T.BAJ'):
        return {"delta": "⚠ REVERSAL", "action": "LIQUIDAR", "actionC": "#ff1744",
                "detail": f"VP giró de {p_vp}→{c_vp}. Institucionales cambiaron dirección. Salir."}

    if p_vp in ('DIST', 'T.BAJ') and c_vp in ('ACUM', 'T.ALC'):
        return {"delta": "⚡ REVERSAL", "action": "ENTRAR", "actionC": "#00e676",
                "detail": f"VP giró de {p_vp}→{c_vp}. Institucionales cambian a alcista. Evaluar entrada."}

    # ── DOWNGRADE: Signal weakening ───────────────────────
    if vp_delta <= -2 or (p_bull == True and c_bull == False):
        return {"delta": "▼ DOWNGRADE", "action": "REDUCIR", "actionC": "#ff6d00",
                "detail": f"VP: {p_vp}→{c_vp}. Score: {p_score}→{c_score}. Señal debilitándose. Ajustar stop."}

    if vp_delta == -1 and score_delta < -1:
        return {"delta": "▼ DEGRADACIÓN", "action": "AJUSTAR STOP", "actionC": "#ffab00",
                "detail": f"VP bajó un nivel ({p_vp}→{c_vp}) + score cayó {score_delta:+.1f}. Tightear stop, no agregar."}

    # ── UPGRADE: Signal strengthening ─────────────────────
    if vp_delta >= 2 or (p_bull != True and c_bull == True and score_delta > 1):
        return {"delta": "▲ UPGRADE", "action": "AUMENTAR", "actionC": "#00e676",
                "detail": f"VP: {p_vp}→{c_vp}. Score: {p_score}→{c_score}. Señal fortaleciéndose. Considerar agregar."}

    if vp_delta == 1 and score_delta > 0.5:
        return {"delta": "▲ MEJORA", "action": "MANTENER+", "actionC": "#1de9b6",
                "detail": f"VP mejoró ({p_vp}→{c_vp}), score subió {score_delta:+.1f}. Mantener con confianza."}

    # ── CONFLICT EMERGENCE ────────────────────────────────
    if p_bull == True and c_bull == True and c_vp in ('DIST', 'T.BAJ'):
        return {"delta": "✗ CONFLICTO", "action": "PRECAUCIÓN", "actionC": "#e040fb",
                "detail": f"VSA sigue bull pero VP giró a {c_vp}. Señales contradictorias. No agregar."}

    # ── STABLE ────────────────────────────────────────────
    if abs(score_delta) <= 0.5 and abs(vp_delta) <= 1:
        if c_vp in ('ACUM', 'T.ALC') and c_bull == True:
            return {"delta": "= ESTABLE ✓", "action": "MANTENER", "actionC": "#00e676",
                    "detail": f"Señal bull sostenida. VP:{c_vp}, Score:{c_score}. Mantener posición."}
        elif c_vp in ('DIST', 'T.BAJ') and c_bull == False:
            return {"delta": "= ESTABLE ▼", "action": "FUERA", "actionC": "#ff1744",
                    "detail": f"Señal bear sostenida. VP:{c_vp}. No entrar."}
        else:
            return {"delta": "= SIN CAMBIO", "action": "ESPERAR", "actionC": "#4a6480",
                    "detail": f"VP:{p_vp}→{c_vp}. Score:{p_score}→{c_score}. Sin cambio material."}

    # ── DEFAULT ───────────────────────────────────────────
    direction = "↑" if score_delta > 0 else "↓" if score_delta < 0 else "="
    return {"delta": f"{direction} CAMBIO", "action": "EVALUAR", "actionC": "#00bcd4",
            "detail": f"VP:{p_vp}→{c_vp}. Score:{p_score}→{c_score}. Revisar contexto."}


def save_scan_history(data):
    """Guarda los resultados del scan actual como JSON con timestamp."""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(HISTORY_DIR, f"scan_{timestamp}.json")

    # Extraer solo los campos necesarios para comparación
    snapshot = {}
    for d in data:
        snapshot[d['ticker']] = {
            "score": d['score'],
            "sig_k": d['sig']['k'],
            "sig_bull": d['sig']['bull'],
            "vp_bias": d['vp']['bias'] if d.get('vp') else None,
            "vp_pocS": d['vp']['pocS'] if d.get('vp') else None,
            "vp_pocM": d['vp']['pocM'] if d.get('vp') else None,
            "vp_pocL": d['vp']['pocL'] if d.get('vp') else None,
            "clv": d['clvV'],
            "volR": d['volR'],
            "trend": d.get('trend', {}).get('trend', ''),
            "confluence": d.get('confluence', ''),
            "close": d['c'],
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    class NpEnc(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.bool_,)): return bool(obj)
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            return super().default(obj)

    with open(filename, 'w') as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2, cls=NpEnc)

    print(f"  ✓ Historial guardado: {filename}")
    return filename


def load_previous_scan():
    """Carga el scan anterior más reciente."""
    if not os.path.exists(HISTORY_DIR):
        return None, None

    files = sorted(glob.glob(os.path.join(HISTORY_DIR, "scan_*.json")))
    if len(files) < 1:
        return None, None

    # Si hay más de 1, el último es el que acabamos de guardar, queremos el penúltimo
    # Pero como guardamos DESPUÉS de comparar, cargamos el último existente
    latest = files[-1]
    try:
        with open(latest, 'r') as f:
            prev_data = json.load(f)
        # Extraer fecha del filename
        fname = os.path.basename(latest)
        date_str = fname.replace("scan_", "").replace(".json", "")
        return prev_data, date_str
    except:
        return None, None


def calc_transitions(data, prev_scan):
    """Calcula transiciones para todos los activos."""
    transitions = {}
    for d in data:
        tk = d['ticker']
        prev = prev_scan.get(tk) if prev_scan else None
        trans = classify_transition(prev, d)

        # Agregar info del scan anterior para contexto
        if prev:
            trans['prev_score'] = prev.get('score', 0)
            trans['prev_vp'] = prev.get('vp_bias', '—')
            trans['prev_sig'] = prev.get('sig_k', '—')
            trans['prev_date'] = prev.get('date', '—')
            trans['prev_close'] = prev.get('close', 0)
            trans['price_change'] = round(
                (d['c'] - prev['close']) / prev['close'] * 100, 2
            ) if prev.get('close', 0) > 0 else 0
        else:
            trans['prev_score'] = None
            trans['prev_vp'] = None
            trans['prev_sig'] = None
            trans['prev_date'] = None
            trans['prev_close'] = None
            trans['price_change'] = None

        transitions[tk] = trans

    return transitions


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def generate_scanner(output_file="bifs_vsa_scanner_v4.html"):
    print("=" * 60)
    print("BIFS VSA SCANNER v4")
    print("VSA v2 (8 señales) + VP Multi-TF + Confluencia + Tendencia")
    print("=" * 60)

    universe = UNIVERSE_CORE.copy()
    if EXTENDED_UNIVERSE:
        universe.extend(UNIVERSE_EXTENDED)
        print(f"  Universo extendido: {len(universe)} activos (USA + ARG + CEDEARs)")
    else:
        print(f"  Universo core: {len(universe)} activos (USA)")

    # ── Configurar historial ──
    setup_history_dir()

    # ── Cargar scan anterior ──
    prev_scan, prev_date = load_previous_scan()
    if prev_scan:
        print(f"  Scan anterior: {prev_date} ({len(prev_scan)} tickers)")
    else:
        print(f"  Sin scan anterior (primera corrida)")

    data = fetch_all(universe, period="1y")

    if not data:
        print("ERROR: Sin datos.")
        return

    # ── Calcular transiciones ──
    transitions = calc_transitions(data, prev_scan)

    # Inyectar transiciones en data para el HTML
    for d in data:
        d['transition'] = transitions.get(d['ticker'], {
            "delta": "—", "action": "—", "actionC": "#4a6480", "detail": "",
            "prev_score": None, "prev_vp": None, "prev_sig": None,
            "prev_date": None, "prev_close": None, "price_change": None
        })

    sector_summary = calc_sector_summary(data)

    print(f"\n{'─'*60}")
    print("  SECTOR SUMMARY:")
    for s in sector_summary:
        bc = "▲" if s['bias'] == 'BULL' else "▼" if s['bias'] == 'BEAR' else "◦"
        print(f"    {s['sector']:<18} Score:{s['avgScore']:>4.1f}  ▲{s['acum']} ▼{s['dist']}  {bc} {s['bias']}")

    # ── Imprimir transiciones importantes ──
    if prev_scan:
        print(f"\n{'─'*60}")
        print(f"  TRANSICIONES vs scan anterior ({prev_date}):")
        important = [(tk, t) for tk, t in transitions.items()
                     if t['delta'] not in ('= SIN CAMBIO', '= ESTABLE ▼', 'NUEVO', '= ESTABLE ✓')]
        important.sort(key=lambda x: x[1].get('actionC', ''), reverse=True)

        if important:
            for tk, t in important:
                print(f"    {tk:<6} {t['delta']:<16} → {t['action']:<14} {t['detail'][:60]}")
        else:
            print(f"    Sin transiciones materiales. Señales estables.")

        # Alertas críticas
        reversals = [(tk, t) for tk, t in transitions.items() if 'REVERSAL' in t.get('delta', '')]
        if reversals:
            print(f"\n  {'⚠'*20}")
            print(f"  ALERTAS DE REVERSAL:")
            for tk, t in reversals:
                print(f"    {tk}: {t['detail']}")
            print(f"  {'⚠'*20}")

    generate_html(data, sector_summary, output_file)

    # ── Guardar scan actual al historial ──
    save_scan_history(data)

    # Print summary
    bulls = sum(1 for d in data if d['sig']['bull'] == True)
    bears = sum(1 for d in data if d['sig']['bull'] == False)
    conf_aligned = sum(1 for d in data if 'ALINEADO' in d.get('confluence', ''))
    conf_conflict = sum(1 for d in data if 'CONFLICTO' in d.get('confluence', ''))
    top = max(data, key=lambda d: d['score'])

    print(f"\n{'='*60}")
    print(f"  Activos: {len(data)} · Bull: {bulls} · Bear: {bears}")
    print(f"  Confluencia ✓: {conf_aligned} · Conflicto ✗: {conf_conflict}")
    print(f"  Top: {top['ticker']} {top['score']} ({top['sig']['k']} + {top['vp']['bias'] if top.get('vp') else '—'})")
    print(f"{'='*60}")

    return output_file


# ══════════════════════════════════════════════════════════════
# TELEGRAM ALERTS
# ══════════════════════════════════════════════════════════════

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_telegram(text, parse_mode="HTML"):
    """Envía mensaje a Telegram. Silencioso si no hay token."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"  [TG OFF] {text[:80]}...")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"  [TG ERROR] {e}")
        return False


def send_critical_alert(ticker, data, transition):
    """Alerta LIQUIDAR/REDUCIR."""
    t = transition
    d = data
    vp = d.get('vp', {})
    emoji = "🚨" if t['action'] == 'LIQUIDAR' else "⚠️"
    msg = f"""{emoji} <b>BIFS: {t['action']}</b>
━━━━━━━━━━━━━━━━
<b>{ticker}</b> · ${d['c']}  ({'+' if d['chg1d']>=0 else ''}{d['chg1d']}%)
VSA: {d['sig']['k']} · VP: {vp.get('bias','—')}
Score: {d['score']} (prev: {t.get('prev_score','—')})

<i>{t['detail']}</i>
{f"Precio vs scan anterior: {'+' if t.get('price_change',0)>=0 else ''}{t.get('price_change','—')}%" if t.get('price_change') is not None else ''}
━━━━━━━━━━━━━━━━
<b>Acción: {t['action']}</b>"""
    send_telegram(msg)


def send_opportunity_alert(ticker, data, transition):
    """Alerta ENTRAR/AUMENTAR."""
    d = data
    vp = d.get('vp', {})
    msg = f"""🟢 <b>BIFS: {transition['action']}</b>
━━━━━━━━━━━━━━━━
<b>{ticker}</b> · ${d['c']}  ({'+' if d['chg1d']>=0 else ''}{d['chg1d']}%)
VSA: {d['sig']['k']} · VP: {vp.get('bias','—')}
Score: {d['score']} · {d.get('confluence','—')}

<i>{transition['detail']}</i>
━━━━━━━━━━━━━━━━
Evaluar entrada próxima sesión"""
    send_telegram(msg)


def send_daily_summary(data, transitions, sector_summary):
    """Resumen diario."""
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    bulls = sum(1 for d in data if d['sig']['bull'] == True)
    bears = sum(1 for d in data if d['sig']['bull'] == False)
    conf_a = sum(1 for d in data if 'ALINEADO' in d.get('confluence', ''))
    conf_x = sum(1 for d in data if 'CONFLICTO' in d.get('confluence', ''))

    top5 = sorted(data, key=lambda d: d['score'], reverse=True)[:5]
    top_lines = "\n".join(f"  {d['ticker']:<6} {d['score']:>4.1f}  {d['sig']['k']:<11} VP:{d['vp']['bias'] if d.get('vp') else '—'}"
                          for d in top5)

    sect_lines = "\n".join(f"  {s['sector']:<16} {s['avgScore']:>4.1f}  {'▲' if s['bias']=='BULL' else '▼' if s['bias']=='BEAR' else '◦'}"
                           for s in sector_summary[:5])

    # Transiciones relevantes
    trans = ""
    if transitions:
        critical = [(tk, t) for tk, t in transitions.items()
                    if t.get('action') in ('LIQUIDAR','REDUCIR','AUMENTAR','ENTRAR','AJUSTAR STOP')]
        if critical:
            t_lines = "\n".join(f"  {'🚨' if t['action'] in ('LIQUIDAR','REDUCIR') else '🟢'} {tk:<6} → {t['action']}"
                                for tk, t in critical[:8])
            trans = f"\n\n<b>TRANSICIONES:</b>\n{t_lines}"
        else:
            trans = "\n\n<i>Sin transiciones materiales</i>"

    msg = f"""📊 <b>BIFS SCAN</b> · {date_str}
━━━━━━━━━━━━━━━━━━
📈 Bull: {bulls}  📉 Bear: {bears}
✅ Confluencia: {conf_a}  ❌ Conflicto: {conf_x}

<b>TOP 5:</b>
<code>{top_lines}</code>

<b>SECTORES:</b>
<code>{sect_lines}</code>{trans}"""
    send_telegram(msg)


def send_watchlist(data):
    """Activos a punto de dar señal (score alto + VP bull + VSA neutro)."""
    wl = [d for d in data
          if d['score'] >= 7.5
          and d.get('vp', {}).get('bias') in ('ACUM', 'T.ALC')
          and d['sig']['bull'] is None
          and d.get('trend', {}).get('trend') in ('UP', 'RECOVERING')]

    if not wl:
        return

    wl.sort(key=lambda d: d['score'], reverse=True)
    lines = "\n".join(f"  {d['ticker']:<6} {d['score']:>4.1f}  VP:{d['vp']['bias']}  CLV:{d['clvV']:>6.3f}"
                      for d in wl[:8])

    msg = f"""👁 <b>WATCHLIST</b>
━━━━━━━━━━━━━━━━━━
Score alto + VP alcista + VSA neutro
Si mañana dan señal VSA bull → entrada

<code>{lines}</code>"""
    send_telegram(msg)


# ══════════════════════════════════════════════════════════════
# MAIN — Detecta entorno automáticamente
# ══════════════════════════════════════════════════════════════
def run_automated():
    """Corre scanner + envía alertas Telegram."""
    print("=" * 60)
    print("BIFS SCANNER v4 — MODO AUTOMÁTICO")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Setup
    universe = UNIVERSE_CORE.copy()
    if EXTENDED_UNIVERSE:
        universe.extend(UNIVERSE_EXTENDED)
    setup_history_dir()

    prev_scan, prev_date = load_previous_scan()
    if prev_scan:
        print(f"  Scan anterior: {prev_date} ({len(prev_scan)} tickers)")

    # Scan
    data = fetch_all(universe, period="1y")
    if not data:
        send_telegram("🚨 <b>BIFS ERROR:</b> Sin datos. Verificar yfinance.")
        return

    # Transiciones
    transitions = calc_transitions(data, prev_scan)
    for d in data:
        d['transition'] = transitions.get(d['ticker'], {
            "delta": "NUEVO", "action": "EVALUAR", "actionC": "#00bcd4",
            "detail": "Primera aparición", "prev_score": None, "prev_vp": None,
            "prev_sig": None, "prev_date": None, "prev_close": None, "price_change": None
        })

    sector_summary = calc_sector_summary(data)

    # ── Alertas por prioridad ──
    for tk, t in transitions.items():
        if t.get('action') == 'LIQUIDAR':
            d = next((x for x in data if x['ticker'] == tk), None)
            if d: send_critical_alert(tk, d, t)

    for tk, t in transitions.items():
        if t.get('action') in ('REDUCIR', 'AJUSTAR STOP'):
            d = next((x for x in data if x['ticker'] == tk), None)
            if d: send_critical_alert(tk, d, t)

    for tk, t in transitions.items():
        if t.get('action') in ('AUMENTAR', 'ENTRAR'):
            d = next((x for x in data if x['ticker'] == tk), None)
            if d: send_opportunity_alert(tk, d, t)

    send_daily_summary(data, transitions, sector_summary)
    send_watchlist(data)

    # HTML + historial
    generate_html(data, sector_summary, "bifs_vsa_scanner_v4.html")
    save_scan_history(data)

    print(f"\n✓ Scan completado · {len(data)} activos")

    try:
        from google.colab import files
        files.download("bifs_vsa_scanner_v4.html")
    except ImportError:
        pass


if __name__ == "__main__":
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("TELEGRAM_BOT_TOKEN"):
        # GitHub Actions o entorno con Telegram → automático
        run_automated()
    else:
        # Colab / local → solo scanner HTML
        generate_scanner("bifs_vsa_scanner_v4.html")
