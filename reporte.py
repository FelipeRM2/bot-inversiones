import os, json, asyncio, sys
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from telegram import Bot

TOKEN        = os.environ["TELEGRAM_TOKEN"]
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]
CARTERA_FILE = "cartera.json"
TZ_ARG       = ZoneInfo("America/Argentina/Buenos_Aires")

YAHOO_MAP = {
    "PAMP":  "PAMP.BA",
    "AAPLD": "AAPL.BA",
    "AMZND": "AMZN.BA",
    "TSLAD": "TSLA.BA",
    "NVDAD": "NVDA.BA",
    "METAD": "META.BA",
    "VALED": "VALE.BA",
    "ITUBD": "ITUB.BA",
    "BBDD":  "BBD.BA",
    "VISTD": "VIST.BA",
}

def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        return {}
    with open(CARTERA_FILE) as f:
        return json.load(f)

def parsear_numero_arg(s):
    """Convierte '574.245,02' (formato argentino) a 574245.02 (float)"""
    if not s:
        return 0.0
    s = s.strip()
    # Si tiene coma, es el separador decimal -> sacar puntos de miles y cambiar coma por punto
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)

async def obtener_datos(ticker):
    yahoo_ticker = YAHOO_MAP.get(ticker, ticker + ".BA")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(f"https://query2.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}", headers=headers)
            if r.status_code == 200:
                meta = r.json()["chart"]["result"][0]["meta"]
                precio      = float(meta["regularMarketPrice"])
                cierre_ayer = float(meta["chartPreviousClose"])
                var_pct     = ((precio - cierre_ayer) / cierre_ayer) * 100
                return precio, cierre_ayer, var_pct
    except Exception as e:
        print(f"Error {ticker}: {e}")
    return None, None, None

def fmt(n):
    """Formatea un numero con separador de miles . y decimal , (formato argentino)"""
    s = f"{n:,.2f}"
    # f-string da formato US (1,234.56) -> convertir a AR (1.234,56)
    s = s.replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
    return s

async def main():
    cartera = cargar_cartera()

    valores_fijos = {}
    for arg in sys.argv[1:]:
        if "=" in arg:
            k, v = arg.split("=")
            valores_fijos[k.upper()] = parsear_numero_arg(v)

    cocoa_val = valores_fijos.get("COCOA", 0)
    tzxd6_val = valores_fijos.get("TZXD6", 0)

    ahora = datetime.now(TZ_ARG).strftime("%d/%m/%Y %H:%M")
    lineas = [f"📊 *Resumen del día* — {ahora}\n"]

    total_ganancia_dia = 0.0
    total_valor        = 0.0

    if cocoa_val:
        lineas.append(f"💰 *COCOA* — Cocos Ahorro FCI\n   Valor: ${fmt(cocoa_val)} _(rinde diario)_")
        total_valor += cocoa_val

    for ticker, d in cartera.items():
        if ticker in ("COCOA", "TZXD6"):
            continue
        cant = d["cantidad"]
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
            f"   {cant:,.0f} u. × ${fmt(precio)}\n"
            f"   Valor: ${fmt(valor_hoy)} | Hoy: {s}${fmt(ganancia_dia)}"
        )
        total_ganancia_dia += ganancia_dia
        total_valor        += valor_hoy

    if tzxd6_val:
        lineas.append(f"💰 *TZXD6* — Bono CER\n   Valor: ${fmt(tzxd6_val)} _(ajusta por CER)_")
        total_valor += tzxd6_val

    s = "+" if total_ganancia_dia >= 0 else ""
    e = "🟢" if total_ganancia_dia >= 0 else "🔴"
    lineas.append(
        f"\n{'─'*28}\n"
        f"💼 *Valor total cartera:* ${fmt(total_valor)}\n"
        f"{e} *Ganancia del día:* {s}${fmt(total_ganancia_dia)}"
    )

    bot = Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")
    print("Reporte enviado!")

asyncio.run(main())
