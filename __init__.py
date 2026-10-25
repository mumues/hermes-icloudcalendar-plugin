"""apple-takvim plugin'i — kayıt noktası.

Apple Takvim'e iCloud CalDAV (https://caldav.icloud.com) üzerinden bağlanır.
Kimlik: APPLE_ID + APPLE_APP_PASSWORD (uygulamaya özel parola).
"""

from __future__ import annotations

import json
import logging

from . import client, schemas, tools

logger = logging.getLogger(__name__)

_HANDLERS = {
    "takvim_listele": tools.takvim_listele,
    "etkinlikleri_getir": tools.etkinlikleri_getir,
    "etkinlik_olustur": tools.etkinlik_olustur,
    "etkinlik_guncelle": tools.etkinlik_guncelle,
    "etkinlik_sil": tools.etkinlik_sil,
}


def _slash_takvim(raw_args: str) -> str:
    """/takvim [bugün|yarın|hafta|YYYY-AA-GG] — modele sormadan hızlı liste."""
    arg = (raw_args or "").strip().casefold() or "bugün"
    if arg in ("hafta", "week"):
        istek = {"gun_sayisi": 7}
    elif arg in ("bugün", "bugun", "yarın", "yarin"):
        istek = {"baslangic": arg, "gun_sayisi": 1}
    else:
        istek = {"baslangic": arg, "gun_sayisi": 1}
    veri = json.loads(tools.etkinlikleri_getir(istek))
    if "error" in veri:
        return f"Hata: {veri['error']}"
    if not veri["etkinlikler"]:
        return f"📅 {veri['aralik']['baslangic']} – {veri['aralik']['bitis']}: etkinlik yok."
    satirlar = [f"📅 {veri['adet']} etkinlik ({veri['aralik']['baslangic']} – {veri['aralik']['bitis']})"]
    for e in veri["etkinlikler"]:
        zaman = e["baslangic"][:10] + " (tüm gün)" if e["tum_gun"] else f"{e['baslangic']} → {e['bitis'][11:]}"
        ek = f" @ {e['konum']}" if e.get("konum") else ""
        satirlar.append(f"• {zaman}  {e['baslik']}{ek}  [{e['takvim']}]")
    return "\n".join(satirlar)


def register(ctx):
    # Kullanıcı ayarlarını (plugins.entries.apple-takvim.settings) bağlantı katmanına aktar
    client.configure(
        caldav_url=ctx.get_config("caldav_url", default=client.AYARLAR["caldav_url"]),
        timezone=ctx.get_config("timezone", default=client.AYARLAR["timezone"]),
        varsayilan_takvim=ctx.get_config("varsayilan_takvim", default=""),
    )

    for schema in schemas.HEPSI:
        ctx.register_tool(
            name=schema["name"],
            toolset="apple-takvim",
            schema=schema,
            handler=_HANDLERS[schema["name"]],
        )

    ctx.register_command(
        "takvim",
        handler=_slash_takvim,
        description="Apple Takvim: bugün/yarın/hafta etkinlikleri",
        args_hint="[bugün|yarın|hafta|YYYY-AA-GG]",
    )
    logger.info("apple-takvim yüklendi (%s, tz=%s)", client.AYARLAR["caldav_url"], client.AYARLAR["timezone"])
