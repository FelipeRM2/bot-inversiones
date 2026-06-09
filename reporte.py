import os, json, asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from telegram import Bot

TOKEN        = os.environ["TELEGRAM_TOKEN"]
CHAT_ID      = os.environ["TELEGRAM_CHAT_ID"]
CARTERA_FILE = "cartera.json"
TZ_ARG       = ZoneInfo("America/Argentina/Buenos_Aires")

def cargar_cartera():
    if not os.path.exists(CARTERA_FILE):
        return {}
    with open(CARTERA_FILE) as f:
        return json.load(f)

async def obtener_precio(ticker):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://www.rava.com/empresas/precioshistoricos.php?e={ticker}&r=ajax",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = r.json()
            if data and isinstance(data, list):
                return float(data[-1].get("c", 0)) or None
    except:
        pass
    return None

async def main():
    cartera = cargar_cartera()
    if not cartera:
        bot = Bot(TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text="📭 Cartera vacía. Agregá activos editando cartera.json en GitHub.", parse_mode="Markdown")
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
        lineas.append(f"{e} *{ticker}*\n   {cant:,.0f} u. | Compra: ${pc:,.2f} | Actual: ${precio:,.2f}\n   Valor: ${val:,.2f} ({s}{pct:.1f}%) | Ganancia: {s}${gan:,.2f}")
        total_inv += inv
        total_act += val

    gan_t = total_act - total_inv
    pct_t = (gan_t / total_inv * 100) if total_inv else 0
    s = "+" if gan_t >= 0 else ""
    e = "🟢" if gan_t >= 0 else "🔴"
    lineas.append(f"\n{'─'*28}\n{e} *Invertido:* ${total_inv:,.2f}\n{e} *Actual:*    ${total_act:,.2f}\n{e} *Resultado:* {s}${gan_t:,.2f} ({s}{pct_t:.1f}%)")

    bot = Bot(TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text="\n".join(lineas), parse_mode="Markdown")
    print("Reporte enviado!")

asyncio.run(main())
