import os, json, asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from telegram import Bot

TOKEN        = os.environ["TELEGRAM_TOKEN"]
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]
CARTERA_FILE = "cartera.json"
TZ_ARG       = ZoneInfo("America/Argentina/Buenos_Aires")

YAHOO_MAP = {
    "PAMP":   "PAMP.BA",
    "AAPLD":  "AAPL.BA",
    "AMZND":  "AMZN.BA",
    "TSLAD":  "TSLA.BA",
    "NVDAD":  "NVDA.BA",
    "METAD":  "META.BA",
    "VALED":  "VALE.BA",
    "ITUBD":  "ITUB.BA",
    "BBDD":   "BBD.BA",
    "VISTD":  "VIST.BA",
    "TZXD6":  "TZXD6.BA",
}

# Activos con valor fijo (FCIs, no cotizan en bolsa)
VALOR_FIJO = {
    "COCOA": {"valor_total": 574245.02, "descripcion": "Cocos Ahorro FCI"},
    "TZXD6": {"valor_total": 123978.37, "descripcion": "Bono CER TZXD6"},
}

def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        return {}
    with open(CARTERA_FILE) as f:
        return json.load(f)

async def obtener_datos(ticker):
    yahoo_ticker = YAHOO_MAP.get(ticker, ticker + ".BA")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}",
                headers=headers
            )
            if r.status_code == 200:
                meta = r.json()["chart"]["result"][0]["meta"]
                precio      = float(meta["regularMarketPrice"])
                cierre_ayer = float(meta["chartPreviousClose"])
                var_pct     = ((precio - cierre_ayer) / cierre_ayer) * 100
                return precio, cierre_ayer, var_pct
    except Exception as e:
        print(f"Error {ticker}: {e}")
    return None, None, None

async def main():
    cartera = cargar_cartera()
    if not cartera:
        bot = Bot(TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text="📭 Cartera vacía.")
        return

    ahora = datetime.now(TZ_ARG).strftime("%d/%m/%Y %H:%M")
    lineas = [f"📊 *Resumen del día* — {ahora}\n"]

    total_ganancia_dia = 0.0
    total_valor        = 0.0

    for ticker, d in cartera.items():
        cant = d["cantidad"]

        # Activo con valor fijo (FCI)
        if ticker in VALOR_FIJO:
            info  = VALOR_FIJO[ticker]
            valor = info["valor_total"]
            lineas.append(
                f"💰 *{ticker}* — {info['descripcion']}\n"
                f"   Valor: ${valor:,.2f} _(rinde diario, sin variación bursátil)_"
            )
            total_valor += valor
            continue

        precio, cierre_ayer, var_pct = await obtener_datos(ticker)

        if precio is None:
            lineas.append(f"⚠️ *{ticker}* — sin cotización")
            continue

        valor_hoy    = cant * precio
        valor_ayer   = cant * cierre_ayer
        ganancia_dia = valor_hoy - valor_ayer

        e = "🟢" if ganancia_dia >= 0 else "🔴"
        s = "+" if ganancia_dia >= 0 else ""

        lineas.append(
            f"{e} *{ticker}* ({s}{var_pct:.2f}% hoy)\n"
            f"   {cant:,.0f} u. × ${precio:,.2f}\n"
            f"   Valor: ${valor_hoy:,.2f} | Hoy: {s}${ganancia_dia:,.2f}"
        )

        total_ganancia_dia += ganancia_dia
        total_valor        += valor_hoy

    s = "+" if total_ganancia_dia >= 0 else ""
    e = "🟢" if total_ganancia_dia >= 0 else "🔴"
    lineas.append(
        f"\n{'─'*28}\n"
        f"💼 *Valor total cartera:* ${total_valor:,.2f}\n"
        f"{e} *Ganancia del día:* {s}${total_ganancia_dia:,.2f}"
    )

    bot = Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")
    print("Reporte enviado!")

asyncio.run(main())
