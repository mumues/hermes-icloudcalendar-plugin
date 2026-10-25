# apple-takvim — Hermes için Apple (iCloud) Takvim plugin'i

Linux VPS'ten Apple Takvim'e bağlanmanın resmî yolu **iCloud CalDAV** servisidir
(`https://caldav.icloud.com`). Apple normal parolayla CalDAV girişine izin vermez;
**uygulamaya özel parola** gerekir.

## 1) Uygulamaya özel parola oluştur (bir kez)

1. https://account.apple.com → giriş yap (iki faktörlü doğrulama açık olmalı).
2. **Oturum Açma ve Güvenlik → Uygulamaya Özel Parolalar → +**
3. Ad ver (ör. `hermes-vps`), üretilen `xxxx-xxxx-xxxx-xxxx` parolayı kopyala.

Bu parola yalnızca bu plugin için kullanılır; istediğin an aynı ekrandan iptal edebilirsin.

## 2) Kurulum (VPS'te)

```bash
# plugin klasörünü Hermes'e kopyala
scp -r apple-takvim kullanici@VPS_IP:~/.hermes/plugins/

# VPS'te:
hermes plugins doctor ~/.hermes/plugins/apple-takvim      # yapı kontrolü
hermes plugins enable apple-takvim                         # caldav bağımlılığı için onay ister
```

`requires_env` nedeniyle Hermes `APPLE_ID` ve `APPLE_APP_PASSWORD` değerlerini ister
ve `~/.hermes/.env` içine yazar. Sormazsa elle ekle:

```bash
cat >> ~/.hermes/.env <<'ENV'
APPLE_ID=sen@icloud.com
APPLE_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
ENV
```

Başlat ve dene:

```bash
hermes
```

> "Bu hafta takvimimde ne var?"
> "Yarın 14:30'a 45 dakikalık diş hekimi randevusu ekle, Kadıköy."
> "1 Kasım'a tüm gün 'Trendyol kampanya' etkinliği koy, İş takvimine."
> "Diş hekimi randevusunu 16:00'a al."

Oturum içinde model olmadan hızlı liste: `/takvim`, `/takvim yarın`, `/takvim hafta`, `/takvim 2026-11-01`

## 3) Ayarlar (isteğe bağlı)

`~/.hermes/config.yaml`:

```yaml
plugins:
  entries:
    apple-takvim:
      settings:
        timezone: Europe/Istanbul     # tarihler bu dilimde okunur/gösterilir
        varsayilan_takvim: Kişisel    # takvim adı verilmezse buraya yazılır
        # caldav_url: https://caldav.icloud.com   # Apple için değiştirme
```

## Sağlanan araçlar

| Araç | Ne yapar |
|---|---|
| `takvim_listele` | Hesaptaki takvimler |
| `etkinlikleri_getir` | Tarih aralığındaki etkinlikler (tekrarlayanlar açılır; takvim ve metin filtresi) |
| `etkinlik_olustur` | Yeni etkinlik (saatli veya tüm gün, konum, not) |
| `etkinlik_guncelle` | uid ile başlık/zaman/konum/not değişikliği; süre korunur |
| `etkinlik_sil` | uid ile kalıcı silme |

Zaman biçimleri: `2026-11-01`, `2026-11-01 14:30`, `bugün`, `yarın 09:00`.
Sunucuya UTC yazılır, kullanıcıya `timezone` ayarındaki dilimde gösterilir.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `plugin.yaml` | Manifest (v2): araçlar, gerekli env değişkenleri, ayar şeması |
| `pyproject.toml` | Python bağımlılığı: `caldav` |
| `client.py` | CalDAV bağlantısı (thread-güvenli tek bağlantı), kimlik okuma, tarih yardımcıları |
| `schemas.py` | LLM'in gördüğü araç tanımları |
| `tools.py` | Araç handler'ları (hepsi JSON string döner, exception fırlatmaz) |
| `__init__.py` | `register(ctx)`: araçlar + `/takvim` komutu |

## Sorun giderme

- **401 / AuthorizationError** → normal Apple parolası kullanılmış olabilir; uygulamaya özel parola gerekir.
  2FA kapalı hesaplarda uygulamaya özel parola oluşturulamaz.
- **Plugin görünmüyor** → `HERMES_PLUGINS_DEBUG=1 hermes plugins list`
- **Takvim bulunamadı** → `takvim_listele` ile adları gör; eşleşme büyük/küçük harf duyarsız ve kısmi eşleşme destekler.

## Test

Gerçek hesap olmadan yerel bir CalDAV sunucusuyla (Radicale) uçtan uca test edildi:
listele → oluştur (saatli + tüm gün) → aralık/takvim/metin filtresiyle getir → güncelle → sil.
