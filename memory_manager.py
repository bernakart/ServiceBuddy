import os
import json
import re
import redis


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True
)


def temizle_metin(metin):
    if not metin:
        return ""

    metin = str(metin)

    kesilecekler = [
        "KULLANICI MESAJI:",
        "KULLANICI SORUSU:",
        "ASİSTAN YANITI:",
        "KILAVUZ BİLGİLERİ:",
        "GEÇMİŞ SOHBET:",
        "KESİN KURALLAR:",
        "ANALİZ:",
        "İÇ SES:"
    ]

    for ifade in kesilecekler:
        if ifade in metin:
            metin = metin.split(ifade)[0]

    metin = re.sub(r"Merhaba[!,. ]*", "", metin, flags=re.IGNORECASE)
    metin = re.sub(r"Lütfen daha fazla bilgi verin.*", "", metin, flags=re.IGNORECASE | re.DOTALL)
    metin = re.sub(r"Lütfen sorununuzu seçerek devam edelim!?", "", metin, flags=re.IGNORECASE)
    metin = re.sub(r"\(Lütfen.*?seçiniz\.\)", "", metin, flags=re.IGNORECASE | re.DOTALL)
    metin = re.sub(r"\s+", " ", metin).strip()

    return metin


def cevap_ozeti_olustur(cevap):
    cevap = temizle_metin(cevap)

    if not cevap:
        return ""

    return cevap[:300]


def hafizaya_kaydet(session_id, soru, cevap):
    """
    Redis'e tam asistan cevabı değil, kontrollü kısa bağlam kaydeder.
    Böylece model eski cevabı kopyalayıp tekrar etmez.
    """
    try:
        anahtar_mesajlar = f"chat:{session_id}:messages"
        anahtar_durum = f"chat:{session_id}:state"

        soru_temiz = temizle_metin(soru)
        cevap_ozeti = cevap_ozeti_olustur(cevap)

        if soru_temiz:
            r.rpush(
                anahtar_mesajlar,
                json.dumps(
                    {
                        "role": "user",
                        "content": soru_temiz
                    },
                    ensure_ascii=False
                )
            )

        # Sadece son 5 kullanıcı mesajını tut
        r.ltrim(anahtar_mesajlar, -5, -1)

        if soru_temiz:
            r.hset(anahtar_durum, "son_kullanici_sorusu", soru_temiz)

        if cevap_ozeti:
            r.hset(anahtar_durum, "son_teknik_ozet", cevap_ozeti)

        # Oturum 1 saat kullanılmazsa temizlensin
        r.expire(anahtar_mesajlar, 3600)
        r.expire(anahtar_durum, 3600)

    except Exception as e:
        print(f"⚠️ [REDIS HATA] Kayıt yapılamadı: {e}")


def baglam_getir(session_id):
    """
    LLM'e eski asistan cevaplarını aynen vermiyoruz.
    Sadece kısa konuşma bağlamı veriyoruz.
    """
    try:
        anahtar_mesajlar = f"chat:{session_id}:messages"
        anahtar_durum = f"chat:{session_id}:state"

        gecmis_raw = r.lrange(anahtar_mesajlar, 0, -1)
        kullanici_mesajlari = []

        for item in gecmis_raw:
            try:
                data = json.loads(item)
                if data.get("role") == "user":
                    kullanici_mesajlari.append(data.get("content", ""))
            except Exception:
                continue

        son_soru = r.hget(anahtar_durum, "son_kullanici_sorusu") or ""
        son_ozet = r.hget(anahtar_durum, "son_teknik_ozet") or ""

        baglam = ""

        if kullanici_mesajlari:
            baglam += "Önceki kullanıcı mesajları:\n"
            for mesaj in kullanici_mesajlari[-3:]:
                baglam += f"- {mesaj}\n"

        if son_soru:
            baglam += f"\nSon kullanıcı problemi: {son_soru}\n"

        if son_ozet:
            baglam += f"Son teknik durum özeti: {son_ozet}\n"

        return baglam.strip()

    except Exception as e:
        print(f"⚠️ [REDIS HATA] Bağlam çekilemedi: {e}")
        return ""


def secenekleri_kaydet(session_id, secenekler):
    """
    RAG + LLM ile üretilen dinamik seçenekleri Redis'e kaydeder.
    Kullanıcı 1, 2, 3, 4 yazınca gerçek sorun buradan çekilir.
    """
    try:
        anahtar = f"chat:{session_id}:options"
        r.delete(anahtar)

        for secenek in secenekler:
            no = str(secenek.get("no", "")).strip()
            arama_sorusu = str(secenek.get("arama_sorusu", "")).strip()

            if no and arama_sorusu:
                r.hset(anahtar, no, arama_sorusu)

        r.expire(anahtar, 3600)

    except Exception as e:
        print(f"⚠️ [REDIS HATA] Seçenekler kaydedilemedi: {e}")


def secenekten_soru_getir(session_id, secim):
    """
    Kullanıcı 1, 2, 3, 4 yazarsa Redis'teki dinamik seçeneğin karşılığını getirir.
    """
    try:
        anahtar = f"chat:{session_id}:options"
        secim = str(secim).strip()

        if not secim.isdigit():
            return None

        return r.hget(anahtar, secim)

    except Exception as e:
        print(f"⚠️ [REDIS HATA] Seçenek getirilemedi: {e}")
        return None


def secenekleri_temizle(session_id):
    try:
        r.delete(f"chat:{session_id}:options")
    except Exception as e:
        print(f"⚠️ [REDIS HATA] Seçenekler temizlenemedi: {e}")


def hafiza_temizle(session_id):
    try:
        r.delete(f"chat:{session_id}:messages")
        r.delete(f"chat:{session_id}:state")
        r.delete(f"chat:{session_id}:options")
        r.delete(f"chat:{session_id}")
    except Exception as e:
        print(f"⚠️ [REDIS HATA] Hafıza temizlenemedi: {e}")