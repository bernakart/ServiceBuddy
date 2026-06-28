import difflib


def normalize_metin(metin):
    """
    Türkçe karakterleri sadeleştirir.
    Böylece 'çamaşır' ve 'camasir' gibi yazımlar aynı algılanır.
    """
    metin = str(metin).lower()

    ceviri = str.maketrans({
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u"
    })

    return metin.translate(ceviri)


def koleksiyon_sec(soru, mevcut_koleksiyon=None):
    """
    Kullanıcı sorusuna göre doğru cihaz koleksiyonunu seçer.

    Mantık:
    1. Açık cihaz adı varsa kesin o koleksiyona geçer.
    2. Açık cihaz adı yoksa anahtar kelime skorlaması yapar.
    3. Belirsiz takip sorularında mevcut koleksiyonu korur.
    """

    soru_norm = normalize_metin(soru)
    soru_kelimeleri = soru_norm.split()

    # 1. AŞAMA: Açık cihaz adı varsa direkt seç
    camasir_ifadeleri = [
        "camasir",
        "camasir makinesi",
        "camasir makinem",
        "camasir makinemin",
        "yikama",
        "deterjan",
        "tambur",
        "sikma",
        "yumusatici"
    ]

    hava_ifadeleri = [
        "hava nemlendirici",
        "hava nemlemdirici",
        "nemlendirici",
        "nemlendiricim",
        "nemlendiricimden",
        "buhar",
        "iyonizer",
        "su tanki",
        "su haznesi",
        "kotu koku",
        "koku geliyor"
    ]

    robot_ifadeleri = [
        "robot supurge",
        "robot supurgem",
        "robot supurgesi",
        "robot",
        "supurge",
        "sarj istasyonu",
        "istasyon",
        "harita",
        "firca",
        "sensor",
        "engel",
        "tekerlek",
        "toz haznesi"
    ]

    if any(ifade in soru_norm for ifade in camasir_ifadeleri):
        return "camasir_makinesi_koleksiyonu"

    if any(ifade in soru_norm for ifade in hava_ifadeleri):
        return "hava_nemlendirici_koleksiyonu"

    if any(ifade in soru_norm for ifade in robot_ifadeleri):
        return "robot_supurge_koleksiyonu"

    # 2. AŞAMA: Açık cihaz adı yoksa skorlamaya geç
    cihaz_haritasi = {
        "camasir_makinesi_koleksiyonu": [
            "camasir",
            "yikama",
            "deterjan",
            "tambur",
            "sikma",
            "yumusatici",
            "program",
            "kapak",
            "kilit",
            "7103"
        ],

        "hava_nemlendirici_koleksiyonu": [
            "hava",
            "nem",
            "buhar",
            "tank",
            "tanki",
            "hazne",
            "koku",
            "filtre",
            "iyonizer",
            "nemlendirici"
        ],

        "robot_supurge_koleksiyonu": [
            "robot",
            "supurge",
            "istasyon",
            "harita",
            "firca",
            "sensor",
            "temizlik",
            "sarj",
            "engel",
            "tekerlek",
            "hazne"
        ]
    }

    skorlar = {koleksiyon: 0 for koleksiyon in cihaz_haritasi.keys()}

    for koleksiyon, anahtar_kelimeler in cihaz_haritasi.items():
        # Tam / parça eşleşme
        for anahtar in anahtar_kelimeler:
            if anahtar in soru_norm:
                skorlar[koleksiyon] += 1

        # Yazım hatası toleransı
        for kelime in soru_kelimeleri:
            benzerler = difflib.get_close_matches(
                kelime,
                anahtar_kelimeler,
                n=1,
                cutoff=0.78
            )

            if benzerler:
                skorlar[koleksiyon] += 1

    en_yuksek_skor = max(skorlar.values())
    secilen = max(skorlar, key=skorlar.get)

    # 3. AŞAMA: Karar
    # Hiç sinyal yoksa mevcut cihazı koru
    if en_yuksek_skor == 0:
        return mevcut_koleksiyon if mevcut_koleksiyon else "genel_koleksiyon"

    # Güçlü yeni cihaz sinyali varsa cihaz değiştir
    if mevcut_koleksiyon and secilen != mevcut_koleksiyon and en_yuksek_skor >= 2:
        return secilen

    # Zayıf sinyal varsa mevcut cihazı koru
    if mevcut_koleksiyon:
        return mevcut_koleksiyon

    return secilen