"""
BIFS SCANNER v4 — MÓDULO DE AUTOMATIZACIÓN
═══════════════════════════════════════════
Agrega a tu bifs_vsa_scanner_v4.py:
  1. Alertas Telegram para transiciones críticas
  2. Resumen diario automático
  3. Compatible con GitHub Actions (cron schedule)

SETUP:
  1. Crear bot en Telegram: hablar con @BotFather → /newbot → guardar token
  2. Obtener chat_id: hablar con el bot, luego ir a
     https://api.telegram.org/bot<TOKEN>/getUpdates
  3. Configurar secrets en GitHub Actions:
     - TELEGRAM_BOT_TOKEN
     - TELEGRAM_CHAT_ID
  4. Pegar este código al final de bifs_vsa_scanner_v4.py
     (o importarlo como módulo)

pip install yfinance requests --quiet
"""

import requests
import os
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════════
# TELEGRAM ALERTS
# ══════════════════════════════════════════════════════════════

# Config — puede venir de env vars (GitHub Actions) o hardcoded
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "TU_BOT_TOKEN_AQUI")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID",   "TU_CHAT_ID_AQUI")

def send_telegram(text, parse_mode="HTML"):
    """Envía mensaje a Telegram. Silencioso si no hay token configurado."""
    if "TU_BOT_TOKEN" in TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN:
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
        if resp.status_code == 200:
            return True
        else:
            print(f"  [TG ERROR] {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  [TG ERROR] {e}")
        return False


def format_alert_critical(ticker, data, transition):
    """Formatea alerta para transiciones críticas (LIQUIDAR/REDUCIR)."""
    t = transition
    d = data
    vp = d.get('vp', {})
    emoji = "🚨" if t['action'] == 'LIQUIDAR' else "⚠️"

    return f"""{emoji} <b>BIFS ALERTA: {t['action']}</b>
━━━━━━━━━━━━━━━━
<b>{ticker}</b> · ${d['c']}  ({'+' if d['chg1d']>=0 else ''}{d['chg1d']}%)
VSA: {d['sig']['k']} · VP: {vp.get('bias','—')}
Score: {d['score']} (prev: {t.get('prev_score','—')})
{t['delta']}

<i>{t['detail']}</i>
{f"Precio desde último scan: {'+' if t.get('price_change',0)>=0 else ''}{t.get('price_change','—')}%" if t.get('price_change') is not None else ''}
━━━━━━━━━━━━━━━━
<b>Acción requerida: {t['action']}</b>"""


def format_alert_opportunity(ticker, data, transition):
    """Formatea alerta para oportunidades (AUMENTAR/ENTRAR)."""
    d = data
    vp = d.get('vp', {})
    conf = d.get('confluence', '—')

    return f"""🟢 <b>BIFS OPORTUNIDAD: {transition['action']}</b>
━━━━━━━━━━━━━━━━
<b>{ticker}</b> · ${d['c']}  ({'+' if d['chg1d']>=0 else ''}{d['chg1d']}%)
VSA: {d['sig']['k']} · VP: {vp.get('bias','—')}
Score: {d['score']} · Confluencia: {conf}
Trend: {d.get('trend',{}).get('trend','—')}

<i>{transition['detail']}</i>
━━━━━━━━━━━━━━━━
Evaluar entrada en próxima sesión"""


def format_daily_summary(data, transitions, sector_summary):
    """Formatea resumen diario del scan."""
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")

    # Counts
    bulls = sum(1 for d in data if d['sig']['bull'] == True)
    bears = sum(1 for d in data if d['sig']['bull'] == False)
    conf_aligned = sum(1 for d in data if 'ALINEADO' in d.get('confluence', ''))
    conf_conflict = sum(1 for d in data if 'CONFLICTO' in d.get('confluence', ''))

    # Top 5 by score
    top5 = sorted(data, key=lambda d: d['score'], reverse=True)[:5]
    top5_lines = []
    for d in top5:
        vp_bias = d['vp']['bias'] if d.get('vp') else '—'
        sig = d['sig']['k']
        top5_lines.append(f"  {d['ticker']:<6} {d['score']:>4.1f}  {sig:<11} VP:{vp_bias}")

    # Sectors top 5
    top_sectors = sector_summary[:5]
    sector_lines = [f"  {s['sector']:<16} {s['avgScore']:>4.1f}  {'▲' if s['bias']=='BULL' else '▼' if s['bias']=='BEAR' else '◦'}"
                    for s in top_sectors]

    # Transitions
    trans_lines = []
    if transitions:
        critical = [(tk, t) for tk, t in transitions.items()
                    if t.get('action') in ('LIQUIDAR', 'REDUCIR', 'AUMENTAR', 'ENTRAR')]
        for tk, t in critical[:5]:
            emoji = "🚨" if t['action'] in ('LIQUIDAR','REDUCIR') else "🟢"
            trans_lines.append(f"  {emoji} {tk:<6} → {t['action']}")

    # Build message
    msg = f"""📊 <b>BIFS SCAN DIARIO</b> · {date_str}
━━━━━━━━━━━━━━━━━━
📈 Bull: {bulls}  📉 Bear: {bears}
✅ Confluencia: {conf_aligned}  ❌ Conflicto: {conf_conflict}

<b>TOP 5 SCORE:</b>
<code>{chr(10).join(top5_lines)}</code>

<b>TOP SECTORES:</b>
<code>{chr(10).join(sector_lines)}</code>"""

    if trans_lines:
        msg += f"""

<b>TRANSICIONES:</b>
{chr(10).join(trans_lines)}"""
    else:
        msg += "\n\n<i>Sin transiciones materiales vs scan anterior</i>"

    return msg


def format_watchlist_alert(data):
    """Alerta especial: activos en watchlist (score alto + VP bull pero VSA neutro)."""
    watchlist = []
    for d in data:
        vp = d.get('vp')
        if not vp:
            continue
        # Score alto + VP alcista + VSA neutro = "a punto de dar señal"
        if (d['score'] >= 7.5 and
            vp.get('bias') in ('ACUM', 'T.ALC') and
            d['sig']['bull'] is None and
            d.get('trend', {}).get('trend') in ('UP', 'RECOVERING')):
            watchlist.append(d)

    if not watchlist:
        return None

    watchlist.sort(key=lambda d: d['score'], reverse=True)
    lines = []
    for d in watchlist[:8]:
        vp_bias = d['vp']['bias']
        lines.append(f"  {d['ticker']:<6} {d['score']:>4.1f}  VP:{vp_bias}  CLV:{d['clvV']:>6.3f}  T:{d.get('trend',{}).get('trend','—')[:3]}")

    return f"""👁 <b>WATCHLIST — Esperando señal VSA</b>
━━━━━━━━━━━━━━━━━━
Score alto + VP alcista + VSA neutro
Si mañana dan TEST/ABSORCION/NO SUPPLY → entrada

<code>{chr(10).join(lines)}</code>

<i>Estos activos tienen la estructura VP alineada.
Solo falta la confirmación de la barra del día.</i>"""


# ══════════════════════════════════════════════════════════════
# ORQUESTADOR — REEMPLAZA EL MAIN
# ══════════════════════════════════════════════════════════════

def run_automated_scan():
    """
    Función principal para ejecución automática.
    Corre el scanner, compara con scan anterior, envía alertas.
    Diseñada para GitHub Actions o Colab scheduler.
    """
    print("=" * 60)
    print("BIFS SCANNER v4 — EJECUCIÓN AUTOMATIZADA")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ── 1. Correr el scanner (importa funciones del scanner principal) ──
    # Si estás en el mismo archivo, las funciones ya están disponibles
    # Si es módulo separado: from bifs_vsa_scanner_v4 import *

    try:
        # Asumimos que las funciones del scanner están disponibles
        # (pegaste este código al final del scanner o lo importaste)
        universe = UNIVERSE_CORE.copy()
        if EXTENDED_UNIVERSE:
            universe.extend(UNIVERSE_EXTENDED)

        setup_history_dir()

        # Cargar scan anterior
        prev_scan, prev_date = load_previous_scan()
        if prev_scan:
            print(f"  Scan anterior: {prev_date} ({len(prev_scan)} tickers)")
        else:
            print(f"  Primera corrida — sin historial previo")

        # Descargar y calcular
        data = fetch_all(universe, period="1y")
        if not data:
            send_telegram("🚨 <b>BIFS ERROR:</b> Sin datos del scanner. Verificar yfinance.")
            return

        # Transiciones
        transitions = calc_transitions(data, prev_scan)
        for d in data:
            d['transition'] = transitions.get(d['ticker'], {
                "delta": "NUEVO", "action": "EVALUAR", "actionC": "#00bcd4",
                "detail": "Primera aparición", "prev_score": None,
                "prev_vp": None, "prev_sig": None, "prev_date": None,
                "prev_close": None, "price_change": None
            })

        sector_summary = calc_sector_summary(data)

    except Exception as e:
        send_telegram(f"🚨 <b>BIFS ERROR:</b>\n<code>{str(e)[:200]}</code>")
        raise

    # ── 2. Enviar alertas por prioridad ──────────────────────

    alerts_sent = 0

    # PRIORIDAD 1: LIQUIDAR (salir ya)
    for tk, t in transitions.items():
        if t.get('action') == 'LIQUIDAR':
            d = next((x for x in data if x['ticker'] == tk), None)
            if d:
                send_telegram(format_alert_critical(tk, d, t))
                alerts_sent += 1

    # PRIORIDAD 2: REDUCIR (ajustar)
    for tk, t in transitions.items():
        if t.get('action') in ('REDUCIR', 'AJUSTAR STOP'):
            d = next((x for x in data if x['ticker'] == tk), None)
            if d:
                send_telegram(format_alert_critical(tk, d, t))
                alerts_sent += 1

    # PRIORIDAD 3: ENTRAR/AUMENTAR (oportunidades)
    for tk, t in transitions.items():
        if t.get('action') in ('AUMENTAR', 'ENTRAR'):
            d = next((x for x in data if x['ticker'] == tk), None)
            if d:
                send_telegram(format_alert_opportunity(tk, d, t))
                alerts_sent += 1

    # ── 3. Resumen diario ─────────────────────────────────────
    summary = format_daily_summary(data, transitions, sector_summary)
    send_telegram(summary)

    # ── 4. Watchlist (activos a punto de dar señal) ───────────
    watchlist_msg = format_watchlist_alert(data)
    if watchlist_msg:
        send_telegram(watchlist_msg)

    # ── 5. Generar HTML y guardar historial ───────────────────
    try:
        generate_html(data, sector_summary, "bifs_vsa_scanner_v4.html")
        save_scan_history(data)
    except Exception as e:
        print(f"  Error generando HTML: {e}")

    print(f"\n{'='*60}")
    print(f"  ✓ Scan completado · {len(data)} activos · {alerts_sent} alertas enviadas")
    print(f"{'='*60}")

    # En Colab: descargar HTML
    try:
        from google.colab import files
        files.download("bifs_vsa_scanner_v4.html")
    except ImportError:
        pass

    return data


# ══════════════════════════════════════════════════════════════
# MAIN — Detecta entorno y ejecuta
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Si hay env vars de GitHub Actions, correr automatizado
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("TELEGRAM_BOT_TOKEN"):
        run_automated_scan()
    else:
        # Modo manual (Colab) — pregunta qué hacer
        print("BIFS Scanner v4")
        print("1. Scanner normal (HTML)")
        print("2. Scanner + Telegram alerts")
        print()
        choice = input("Elegí (1/2): ").strip()
        if choice == "2":
            run_automated_scan()
        else:
            generate_scanner("bifs_vsa_scanner_v4.html")
