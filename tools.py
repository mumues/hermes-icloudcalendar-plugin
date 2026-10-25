"""Tool handler'ları — her biri JSON string döndürür, asla exception fırlatmaz."""

from __future__ import annotations

import functools
import json
import logging
import uuid
from datetime import date, datetime, timedelta

from . import client as c

logger = logging.getLogger(__name__)


def _json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _guvenli(fn):
    """Tüm handler'ları saran ortak hata yakalayıcı."""
    @functools.wraps(fn)
    def sarmal(args: dict | None = None, **kwargs) -> str:
        try:
            return fn(args or {}, **kwargs)
        except (ValueError, LookupError) as e:          # kullanıcı hatası
            return _json({"error": str(e)})
        except RuntimeError as e:                       # yapılandırma hatası
            return _json({"error": str(e)})
        except Exception as e:  # noqa: BLE001        # ağ / sunucu hatası
            logger.exception("apple-takvim: %s başarısız", fn.__name__)
            ad = type(e).__name__
            ipucu = ""
            if "Authorization" in ad or "401" in str(e):
                ipucu = " — APPLE_ID / APPLE_APP_PASSWORD doğru mu? Uygulamaya özel parola kullanılmalı."
            return _json({"error": f"{ad}: {e}{ipucu}"})
    return sarmal


# ------------------------------------------------------------------ yardımcı

def _vevent_sozluk(vevent, takvim_adi: str) -> dict:
    dtstart = vevent.get("dtstart")
    dtend = vevent.get("dtend")
    bas = dtstart.dt if dtstart is not None else None
    bit = dtend.dt if dtend is not None else None
    tum_gun = isinstance(bas, date) and not isinstance(bas, datetime)
    if bit is None and bas is not None:
        bit = bas + timedelta(days=1) if tum_gun else bas
    return {
        "uid": str(vevent.get("uid", "")),
        "baslik": str(vevent.get("summary", "") or "(başlıksız)"),
        "baslangic": c.goster(bas) if bas is not None else None,
        "bitis": c.goster(bit) if bit is not None else None,
        "tum_gun": tum_gun,
        "konum": str(vevent.get("location", "") or "") or None,
        "notlar": str(vevent.get("description", "") or "") or None,
        "tekrarlayan": "rrule" in vevent or "recurrence-id" in vevent,
        "takvim": takvim_adi,
    }


def _etkinlik_bul(uid: str, takvim: str | None):
    """uid'ye göre etkinliği ve bulunduğu takvimi döndür."""
    from caldav.lib.error import NotFoundError

    adaylar = [c.takvim_bul(takvim)] if takvim else c.takvimler()
    for cal in adaylar:
        try:
            return cal.event_by_uid(uid), cal
        except NotFoundError:
            continue
    raise LookupError(f"uid={uid!r} olan etkinlik bulunamadı")


def _sinir(x, alt, ust, varsayilan):
    try:
        return max(alt, min(ust, int(x)))
    except (TypeError, ValueError):
        return varsayilan


# ------------------------------------------------------------------ handler'lar

@_guvenli
def takvim_listele(args: dict, **kwargs) -> str:
    sonuc = [{"ad": c.takvim_adi(cal), "id": str(cal.url)} for cal in c.takvimler()]
    return _json({"takvimler": sonuc, "adet": len(sonuc), "saat_dilimi": c.AYARLAR["timezone"]})


@_guvenli
def etkinlikleri_getir(args: dict, **kwargs) -> str:
    gun = _sinir(args.get("gun_sayisi"), 1, 366, 7)
    if args.get("baslangic"):
        bas = c.parse_zaman(args["baslangic"], tum_gun=True)  # salt tarih → date, saatli → datetime
        if isinstance(bas, date) and not isinstance(bas, datetime):
            bas = datetime.combine(bas, datetime.min.time(), tzinfo=c.tz())
    else:
        bas = c.simdi().replace(hour=0, minute=0, second=0, microsecond=0)
    if args.get("bitis"):
        bit = c.parse_zaman(args["bitis"], tum_gun=True)
        if isinstance(bit, date) and not isinstance(bit, datetime):  # salt tarih → o günün sonu
            bit = datetime.combine(bit, datetime.min.time(), tzinfo=c.tz()) + timedelta(days=1)
    else:
        bit = bas + timedelta(days=gun)
    if bit <= bas:
        raise ValueError("bitis, baslangic'tan sonra olmalı")

    cals = [c.takvim_bul(args["takvim"])] if args.get("takvim") else c.takvimler()
    arama = (args.get("arama") or "").strip().casefold()

    etkinlikler = []
    for cal in cals:
        ad = c.takvim_adi(cal)
        for ev in cal.search(start=c.utc(bas), end=c.utc(bit), event=True, expand=True):
            for vevent in ev.icalendar_instance.walk("VEVENT"):
                e = _vevent_sozluk(vevent, ad)
                if arama and arama not in " ".join(
                    filter(None, [e["baslik"], e["konum"], e["notlar"]])).casefold():
                    continue
                etkinlikler.append(e)

    etkinlikler.sort(key=lambda e: (e["baslangic"] or "", e["baslik"]))
    return _json({
        "aralik": {"baslangic": c.goster(bas), "bitis": c.goster(bit)},
        "saat_dilimi": c.AYARLAR["timezone"],
        "adet": len(etkinlikler),
        "etkinlikler": etkinlikler,
    })


@_guvenli
def etkinlik_olustur(args: dict, **kwargs) -> str:
    baslik = (args.get("baslik") or "").strip()
    if not baslik:
        raise ValueError("baslik gerekli")
    if not args.get("baslangic"):
        raise ValueError("baslangic gerekli")
    tum_gun = bool(args.get("tum_gun"))

    bas = c.parse_zaman(args["baslangic"], tum_gun=tum_gun)
    if tum_gun and isinstance(bas, datetime):
        bas = bas.date()
    if args.get("bitis"):
        bit = c.parse_zaman(args["bitis"], tum_gun=tum_gun)
        if tum_gun and isinstance(bit, datetime):
            bit = bit.date()
        if tum_gun and bit == bas:
            bit = bas + timedelta(days=1)  # DTEND tüm günde "hariç"tir
    else:
        bit = bas + (timedelta(days=1) if tum_gun else timedelta(minutes=_sinir(args.get("sure_dakika"), 1, 10080, 60)))
    if bit <= bas:
        raise ValueError("bitis, baslangic'tan sonra olmalı")

    cal = c.takvim_bul(args.get("takvim"))
    uid = str(uuid.uuid4())
    veri = {
        "uid": uid,
        "summary": baslik,
        "dtstart": bas if tum_gun else c.utc(bas),
        "dtend": bit if tum_gun else c.utc(bit),
        "dtstamp": c.utc(c.simdi()),
    }
    if args.get("konum"):
        veri["location"] = str(args["konum"]).strip()
    if args.get("notlar"):
        veri["description"] = str(args["notlar"]).strip()
    ev = cal.save_event(**veri)
    vevent = ev.icalendar_component
    return _json({"durum": "oluşturuldu", "etkinlik": _vevent_sozluk(vevent, c.takvim_adi(cal))})


@_guvenli
def etkinlik_guncelle(args: dict, **kwargs) -> str:
    uid = (args.get("uid") or "").strip()
    if not uid:
        raise ValueError("uid gerekli")
    ev, cal = _etkinlik_bul(uid, args.get("takvim"))
    vevent = ev.icalendar_component
    degisen = []

    def ayarla(alan, deger):
        vevent.pop(alan, None)
        vevent.add(alan, deger)
        degisen.append(alan)

    if args.get("baslik"):
        ayarla("summary", str(args["baslik"]).strip())
    if args.get("konum"):
        ayarla("location", str(args["konum"]).strip())
    if args.get("notlar"):
        ayarla("description", str(args["notlar"]).strip())

    if args.get("baslangic") or args.get("bitis"):
        eski_bas = vevent.get("dtstart").dt if vevent.get("dtstart") is not None else None
        eski_bit = vevent.get("dtend").dt if vevent.get("dtend") is not None else eski_bas
        eski_tum_gun = isinstance(eski_bas, date) and not isinstance(eski_bas, datetime)
        tum_gun = bool(args["tum_gun"]) if "tum_gun" in args and args["tum_gun"] is not None else eski_tum_gun
        sure = (eski_bit - eski_bas) if (eski_bas is not None and eski_bit is not None) else timedelta(hours=1)

        bas = c.parse_zaman(args["baslangic"], tum_gun=tum_gun) if args.get("baslangic") else eski_bas
        bit = c.parse_zaman(args["bitis"], tum_gun=tum_gun) if args.get("bitis") else (bas + sure if args.get("baslangic") else eski_bit)
        if tum_gun:
            bas = bas.date() if isinstance(bas, datetime) else bas
            bit = bit.date() if isinstance(bit, datetime) else bit
            if bit <= bas:
                bit = bas + timedelta(days=1)
        else:
            if not isinstance(bas, datetime):
                bas = datetime.combine(bas, datetime.min.time(), tzinfo=c.tz())
            if not isinstance(bit, datetime):
                bit = datetime.combine(bit, datetime.min.time(), tzinfo=c.tz())
            bas, bit = c.utc(bas), c.utc(bit)
            if bit <= bas:
                raise ValueError("bitis, baslangic'tan sonra olmalı")
        ayarla("dtstart", bas)
        ayarla("dtend", bit)
        vevent.pop("duration", None)

    if not degisen:
        raise ValueError("Değiştirilecek alan verilmedi (baslik, baslangic, bitis, konum, notlar)")

    vevent.pop("last-modified", None)
    vevent.add("last-modified", c.utc(c.simdi()))
    seq = int(vevent.get("sequence", 0) or 0)
    vevent.pop("sequence", None)
    vevent.add("sequence", seq + 1)
    ev.save()
    return _json({"durum": "güncellendi", "degisen_alanlar": degisen,
                  "etkinlik": _vevent_sozluk(vevent, c.takvim_adi(cal))})


@_guvenli
def etkinlik_sil(args: dict, **kwargs) -> str:
    uid = (args.get("uid") or "").strip()
    if not uid:
        raise ValueError("uid gerekli")
    ev, cal = _etkinlik_bul(uid, args.get("takvim"))
    ozet = _vevent_sozluk(ev.icalendar_component, c.takvim_adi(cal))
    ev.delete()
    return _json({"durum": "silindi", "etkinlik": ozet})
