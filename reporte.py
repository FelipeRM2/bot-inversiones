import os, json, asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from telegram import Bot

TOKEN        = os.environ["TELEGRAM_TOKEN"]
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]
CARTERA_FILE = "cartera.json"
TZ_ARG       = ZoneInfo("America/Argentina/Buenos_Aires")

# Mapa de tickers locales a Yahoo Finance (.BA = Bolsa Argentina)
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
    "COCOA":  "COCOA.BA",
    "TZXD6":  "TZXD6.BA",
}

def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        return {}
    with open(CARTERA_FILE) as f:
        return json.load(f)

async def obtener_precio(ticker):
    yahoo_ticker = YAHOO_MAP.get(ticker, ticker + ".BA")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}",
                headers=headers
            )
            if r.status_code == 200:
                data = r.json()
                precio = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
                return float(precio)
    except Exception as e:
        print(f"Error {ticker}: {e}")
    return None

async def main():
    cartera = cargar_cartera()
    if not cartera:
        bot = Bot(TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text="📭 Cartera vacía.")
        return

    ahora = datetime.now(TZ_ARG).strftime("%d/%m/%Y %H:%M")
    lineas = [f"📊 *Resumen* — {ahora}\n"]
    total_inv, total_act = 0.0, 0.0

    for ticker, d in cartera.items():
        cant, pc = d["cantidad"], d["precio_compra"]
        inv = cant * pc
        precio = await obtener_precio(ticker)
        if precio is None:
            lineas.append(f"⚠️ *{ticker}* — sin cotización")
            total_inv += inv
            continue
        val = cant * precio
        gan = val - inv
        pct = (gan / inv * 100) if inv else 0
        e = "🟢" if gan >= 0 else "🔴"
        s = "+" if gan >= 0 else ""
        lineas.append(
            f"{e} *{ticker}*\n"
            f"   {cant:,.0f} u. | Compra: ${pc:,.2f} | Actual: ${precio:,.2f}\n"
            f"   Valor: ${val:,.2f} ({s}{pct:.1f}%) | Ganancia: {s}${gan:,.2f}"
        )
        total_inv += inv
        total_act += val

    gan_t = total_act - total_inv
    pct_t = (gan_t / total_inv * 100) if total_inv else 0
    s = "+" if gan_t >= 0 else ""
    e = "🟢" if gan_t >= 0 else "🔴"
    lineas.append(
        f"\n{'─'*28}\n"
        f"{e} *Invertido:* ${total_inv:,.2f}\n"
        f"{e} *Actual:*    ${total_act:,.2f}\n"
        f"{e} *Resultado:* {s}${gan_t:,.2f} ({s}{pct_t:.1f}%)"
    )

    bot = Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")
    print("Reporte enviado!")

asyncio.run(main())
