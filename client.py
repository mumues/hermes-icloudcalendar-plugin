"""CalDAV bağlantısı, kimlik bilgileri ve tarih yardımcıları.

Apple Takvim'e Linux'tan bağlanmanın resmî yolu iCloud CalDAV servisidir:
    https://caldav.icloud.com  +  Apple ID  +  uygulamaya özel parola
"""

from __future__ import annotations

import os
import threading
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# register() tarafından doldurulur
AYARLAR = {
    "caldav_url": "https://caldav.icloud.com",
    "timezone": "Europe/Istanbul",
    "varsayilan_takvim": "",
}

_lock = threading.Lock()
_client = None
_principal = None


def configure(**kwargs) -> None:
    """register() içinden çağrılır; boş/None değerler varsayılanı ezmez."""
    for k, v in kwargs.items():
        if k in AYARLAR and v not in (None, ""):
            AYARLAR[k] = v
    reset()


def reset() -> None:
    global _client, _principal
    with _lock:
        _client = _principal = None


def _secret(name: str) -> str:
    """Önce Hermes'in gizli anahtar deposu, yoksa ortam değişkeni."""
    try:
        from agent.secret_scope import get_secret  # Hermes içinde mevcut
        val = get_secret(name)
        if val:
            return str(val).strip()
    except Exception:  # noqa: BLE001 — Hermes dışında (test) bu modül yok
        pass
    return os.environ.get(name, "").strip()


def principal():
    """Thread-güvenli, tembel (lazy) tek bağlantı. Hata olursa cache'lenmez."""
    global _client, _principal
    if _principal is not None:
        return _principal
    with _lock:
        if _principal is not None:
            return _principal
        import caldav  # pyproject.toml ile kurulur

        apple_id = _secret("APPLE_ID")
        parola = _secret("APPLE_APP_PASSWORD")
        if not apple_id or not parola:
            raise RuntimeError("APPLE_ID veya APPLE_APP_PASSWORD tanımlı değil")
        client = caldav.DAVClient(url=AYARLAR["caldav_url"], username=apple_id, password=parola)
        prin = client.principal()  # burada kimlik doğrulama yapılır
        _client, _principal = client, prin
        return prin


def takvimler() -> list:
    return principal().calendars()


def takvim_adi(cal) -> str:
    try:
        return str(cal.name or "").strip() or str(cal.url)
    except Exception:  # noqa: BLE001
        return str(cal.url)


def takvim_bul(ad: str | None):
    """Ada göre (büyük/küçük harf duyarsız) takvim; ad boşsa varsayılan/ilk takvim."""
    cals = takvimler()
    if not cals:
        raise RuntimeError("Hesapta hiç takvim bulunamadı")
    hedef = (ad or AYARLAR["varsayilan_takvim"] or "").strip().casefold()
    if not hedef:
        return cals[0]
    for c in cals:
        if takvim_adi(c).casefold() == hedef:
            return c
    for c in cals:  # kısmi eşleşme ("İş" → "İş Takvimi")
        if hedef in takvim_adi(c).casefold():
            return c
    mevcut = ", ".join(takvim_adi(c) for c in cals)
    raise LookupError(f"'{ad}' adında takvim yok. Mevcut takvimler: {mevcut}")


# --------------------------------------------------------------------- tarih

def tz() -> ZoneInfo:
    return ZoneInfo(AYARLAR["timezone"])


def simdi() -> datetime:
    return datetime.now(tz())


def parse_zaman(metin: str, *, tum_gun: bool = False):
    """'2026-10-26', '2026-10-26 14:30', '2026-10-26T14:30', 'bugün', 'yarın' → date | aware datetime."""
    s = (metin or "").strip()
    if not s:
        raise ValueError("Tarih boş")
    bugun = simdi().date()
    kisayol = {"bugün": bugun, "bugun": bugun, "today": bugun,
               "yarın": bugun + timedelta(days=1), "yarin": bugun + timedelta(days=1),
               "tomorrow": bugun + timedelta(days=1)}
    ilk, _, kalan = s.partition(" ")
    if ilk.casefold() in kisayol:  # 'yarın' veya 'yarın 14:30'
        d = kisayol[ilk.casefold()]
        if kalan.strip():
            try:
                saat = time.fromisoformat(kalan.strip())
            except ValueError as e:
                raise ValueError(f"Saat anlaşılamadı: {kalan.strip()!r} (beklenen SS:DD)") from e
            return datetime.combine(d, saat, tzinfo=tz())
        return d if tum_gun else datetime.combine(d, time(0, 0), tzinfo=tz())
    s = s.replace(" ", "T", 1) if " " in s and "T" not in s else s
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        deger = datetime.fromisoformat(s)
    except ValueError as e:
        raise ValueError(f"Tarih anlaşılamadı: {metin!r} (beklenen: YYYY-AA-GG veya YYYY-AA-GG SS:DD)") from e
    if "T" not in s and tum_gun:
        return deger.date()
    if deger.tzinfo is None:
        deger = deger.replace(tzinfo=tz())
    return deger


def utc(dt: datetime) -> datetime:
    """Sunucuya her zaman UTC yaz: VTIMEZONE gereksinimi olmaz, Apple sorunsuz kabul eder."""
    return dt.astimezone(timezone.utc)


def goster(deger) -> str:
    """ical değerini kullanıcı saat diliminde okunur metne çevir."""
    if isinstance(deger, datetime):
        if deger.tzinfo is None:  # floating time → yerel kabul et
            deger = deger.replace(tzinfo=tz())
        return deger.astimezone(tz()).strftime("%Y-%m-%d %H:%M")
    if isinstance(deger, date):
        return deger.strftime("%Y-%m-%d")
    return str(deger)
