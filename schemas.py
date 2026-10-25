"""Tool şemaları — LLM'in gördüğü kısım."""

_TARIH_ACIKLAMA = (
    "Tarih/saat. Kabul edilen biçimler: 'YYYY-AA-GG' (tüm gün), 'YYYY-AA-GG SS:DD', "
    "ISO 8601, ayrıca 'bugün' / 'yarın'. Saat dilimi verilmezse kullanıcının saat dilimi varsayılır."
)

TAKVIM_LISTELE = {
    "name": "takvim_listele",
    "description": (
        "Kullanıcının Apple (iCloud) hesabındaki takvimleri listeler (ad ve kimlik). "
        "Hangi takvimlerin var olduğunu öğrenmek veya kullanıcı 'takvimlerim neler' dediğinde kullan."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

ETKINLIKLERI_GETIR = {
    "name": "etkinlikleri_getir",
    "description": (
        "Apple Takvim'den belirli bir tarih aralığındaki etkinlikleri getirir. "
        "Kullanıcı 'bugün ne var', 'yarın toplantım var mı', 'bu hafta programım', "
        "'gelecek ay X ne zaman' gibi sorular sorduğunda kullan. Tekrarlayan etkinlikler açılarak döner. "
        "Varsayılan: bugünden başlayarak 7 gün, tüm takvimler."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "baslangic": {"type": "string", "description": "Aralık başlangıcı. " + _TARIH_ACIKLAMA + " Varsayılan: bugün 00:00"},
            "bitis": {"type": "string", "description": "Aralık bitişi (hariç). " + _TARIH_ACIKLAMA + " Verilmezse baslangic + gun_sayisi"},
            "gun_sayisi": {"type": "integer", "description": "bitis verilmediğinde kaç gün ileriye bakılacağı (varsayılan 7, en fazla 366)"},
            "takvim": {"type": "string", "description": "Yalnızca bu takvime bak (ad). Boşsa tüm takvimler."},
            "arama": {"type": "string", "description": "Başlık/konum/notlarda geçmesi gereken metin (isteğe bağlı filtre)"},
        },
        "required": [],
    },
}

ETKINLIK_OLUSTUR = {
    "name": "etkinlik_olustur",
    "description": (
        "Apple Takvim'e yeni etkinlik ekler. Kullanıcı 'takvime ekle', 'toplantı oluştur', "
        "'yarın 14:00'e hatırlatma koy' dediğinde kullan. Dönen uid, sonraki güncelleme/silme için gerekir. "
        "Saat verilmeden yalnızca tarih verildiyse tum_gun=true ile oluştur."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "baslik": {"type": "string", "description": "Etkinlik başlığı"},
            "baslangic": {"type": "string", "description": "Başlangıç. " + _TARIH_ACIKLAMA},
            "bitis": {"type": "string", "description": "Bitiş. Verilmezse başlangıç + sure_dakika (tüm günde: tek gün)"},
            "sure_dakika": {"type": "integer", "description": "bitis verilmediğinde süre (varsayılan 60)"},
            "tum_gun": {"type": "boolean", "description": "Tüm gün etkinliği mi? (varsayılan false)"},
            "takvim": {"type": "string", "description": "Hedef takvim adı. Boşsa varsayılan takvim."},
            "konum": {"type": "string", "description": "Konum (isteğe bağlı)"},
            "notlar": {"type": "string", "description": "Açıklama/notlar (isteğe bağlı)"},
        },
        "required": ["baslik", "baslangic"],
    },
}

ETKINLIK_GUNCELLE = {
    "name": "etkinlik_guncelle",
    "description": (
        "Var olan bir Apple Takvim etkinliğini günceller (başlık, zaman, konum, notlar). "
        "Önce etkinlikleri_getir ile uid'yi bul. Yalnızca verilen alanlar değişir."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "uid": {"type": "string", "description": "Etkinliğin uid'si (etkinlikleri_getir çıktısından)"},
            "takvim": {"type": "string", "description": "Etkinliğin bulunduğu takvim (biliniyorsa; arama hızlanır)"},
            "baslik": {"type": "string", "description": "Yeni başlık"},
            "baslangic": {"type": "string", "description": "Yeni başlangıç. " + _TARIH_ACIKLAMA},
            "bitis": {"type": "string", "description": "Yeni bitiş. " + _TARIH_ACIKLAMA},
            "tum_gun": {"type": "boolean", "description": "Zaman değişiyorsa tüm gün mü?"},
            "konum": {"type": "string", "description": "Yeni konum (boş string silmez, yok sayılır)"},
            "notlar": {"type": "string", "description": "Yeni notlar"},
        },
        "required": ["uid"],
    },
}

ETKINLIK_SIL = {
    "name": "etkinlik_sil",
    "description": (
        "Bir Apple Takvim etkinliğini kalıcı olarak siler. Önce etkinlikleri_getir ile uid'yi bul "
        "ve kullanıcıya hangi etkinliğin silineceğini doğrulat. Geri alınamaz."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "uid": {"type": "string", "description": "Silinecek etkinliğin uid'si"},
            "takvim": {"type": "string", "description": "Etkinliğin bulunduğu takvim (biliniyorsa)"},
        },
        "required": ["uid"],
    },
}

HEPSI = [TAKVIM_LISTELE, ETKINLIKLERI_GETIR, ETKINLIK_OLUSTUR, ETKINLIK_GUNCELLE, ETKINLIK_SIL]
