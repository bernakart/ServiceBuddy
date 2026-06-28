from langchain_chroma import Chroma

from embedding import embedding_modelini_getir
from llm_manager import (
    cevap_olustur,
    secimi_coz,
    arama_sorusunu_genislet,
    genel_soru_mu,
    netlestirme_olustur
)
from router import koleksiyon_sec
from memory_manager import (
    hafizaya_kaydet,
    baglam_getir,
    hafiza_temizle,
    secenekleri_kaydet,
    secenekten_soru_getir,
    secenekleri_temizle
)

# Görüntü işleme / OCR modülü
try:
    from vision_manager import goruntu_sorgusunu_hazirla
    VISION_AKTIF = True
except Exception as e:
    print(f"⚠️ [GÖRÜNTÜ MODÜLÜ] vision_manager yüklenemedi: {e}")
    VISION_AKTIF = False


def img_komutunu_coz(soru):
    """
    Kullanıcı şu formatlardan biriyle görsel verebilir:

    img "C:\\Users\\Mert\\Desktop\\test.png"
    img camasir "C:\\Users\\Mert\\Desktop\\test.png"
    img çamaşır "C:\\Users\\Mert\\Desktop\\test.png"
    img hava "C:\\Users\\Mert\\Desktop\\test.png"
    img robot "C:\\Users\\Mert\\Desktop\\test.png"

    Dönüş:
    cihaz_tipi, image_path
    """

    img_komut = soru[4:].strip()

    cihaz_tipi = None
    image_path = img_komut

    img_komut_lower = img_komut.lower()

    if img_komut_lower.startswith("camasir "):
        cihaz_tipi = "camasir"
        image_path = img_komut[8:].strip()

    elif img_komut_lower.startswith("çamaşır "):
        cihaz_tipi = "camasir"
        image_path = img_komut[8:].strip()

    elif img_komut_lower.startswith("çamasir "):
        cihaz_tipi = "camasir"
        image_path = img_komut[8:].strip()

    elif img_komut_lower.startswith("hava "):
        cihaz_tipi = "hava"
        image_path = img_komut[5:].strip()

    elif img_komut_lower.startswith("nemlendirici "):
        cihaz_tipi = "hava"
        image_path = img_komut[13:].strip()

    elif img_komut_lower.startswith("robot "):
        cihaz_tipi = "robot"
        image_path = img_komut[6:].strip()

    elif img_komut_lower.startswith("supurge "):
        cihaz_tipi = "robot"
        image_path = img_komut[8:].strip()

    elif img_komut_lower.startswith("süpürge "):
        cihaz_tipi = "robot"
        image_path = img_komut[8:].strip()

    image_path = image_path.strip().strip('"').strip("'")

    return cihaz_tipi, image_path


def main():
    DB_YOLU = "./kilavuzlar.db"
    SESSION_ID = "berna_test_01"

    aktif_koleksiyon = None
    db = None

    print("\n" + "=" * 60)
    print("🤖 ARÇELİK TEKNİK ASİSTAN v7.0 | [RAG + REDIS + OCR]")
    print("=" * 60)

    # Program başlarken test oturumunun hafızasını temizle
    hafiza_temizle(SESSION_ID)

    print("[SİSTEM] Embedding modeli yerel bellekten yükleniyor...")
    model = embedding_modelini_getir()

    print("\nAsistan hazır! Teknik çözüm için bekliyorum.")
    print("Metin soru yazabilir veya görsel için şu formatları kullanabilirsiniz:")
    print('img camasir "C:\\Users\\Mert\\Desktop\\test.png"')
    print('img hava "C:\\Users\\Mert\\Desktop\\test.png"')
    print('img robot "C:\\Users\\Mert\\Desktop\\test.png"')
    print("-" * 40)

    while True:
        soru = input("\n👤 Sorgunuz: ")

        if soru.lower().strip() == "q":
            print("[SİSTEM] Çıkış yapıldı.")
            break

        if not soru.strip():
            continue

        # --------------------------------------------------
        # 1. GÖRÜNTÜ GİRİŞİ KONTROLÜ
        # --------------------------------------------------
        if soru.lower().strip().startswith("img "):
            if not VISION_AKTIF:
                print("⚠️ [GÖRÜNTÜ HATA] vision_manager.py bulunamadı veya OCR modülü yüklenemedi.")
                continue

            cihaz_tipi, image_path = img_komutunu_coz(soru)

            try:
                goruntu_sonucu = goruntu_sorgusunu_hazirla(
                    image_path,
                    cihaz_tipi=cihaz_tipi
                )

                print(f"🖼️ [OCR] Okunan metin: {goruntu_sonucu['ocr_text']}")

                if not goruntu_sonucu["ocr_text"]:
                    print("⚠️ [OCR] Görüntüden anlamlı metin okunamadı.")
                    continue

                soru = goruntu_sonucu["query"]
                print(f"🧠 [OCR->RAG] Oluşan sorgu: {soru}")

            except Exception as e:
                print(f"⚠️ [GÖRÜNTÜ HATA] {e}")
                continue

        # --------------------------------------------------
        # 2. CİHAZ / KOLEKSİYON SEÇİMİ
        # --------------------------------------------------
        yeni_koleksiyon = koleksiyon_sec(
            soru,
            mevcut_koleksiyon=aktif_koleksiyon
        )

        if yeni_koleksiyon == "genel_koleksiyon":
            print(
                "⚠️ [SİSTEM] Cihaz türü belirlenemedi. "
                "Lütfen çamaşır makinesi, hava nemlendirici veya robot süpürge olarak belirtin."
            )
            continue

        # --------------------------------------------------
        # 3. HAFIZA VE CİHAZ GEÇİŞ YÖNETİMİ
        # --------------------------------------------------
        if aktif_koleksiyon is not None and yeni_koleksiyon != aktif_koleksiyon:
            print(
                f"🔄 [SİSTEM] Cihaz değişimi: "
                f"{yeni_koleksiyon.replace('_', ' ').title()}. Hafıza sıfırlanıyor..."
            )

            hafiza_temizle(SESSION_ID)
            gecmis_diyalog = ""

        else:
            gecmis_diyalog = baglam_getir(SESSION_ID)

        # --------------------------------------------------
        # 4. VERİTABANI YÜKLEME
        # --------------------------------------------------
        if aktif_koleksiyon is None or yeni_koleksiyon != aktif_koleksiyon:
            try:
                db = Chroma(
                    persist_directory=DB_YOLU,
                    embedding_function=model,
                    collection_name=yeni_koleksiyon
                )

                aktif_koleksiyon = yeni_koleksiyon

                print(
                    f"✅ [VERİTABANI] "
                    f"{aktif_koleksiyon.replace('_', ' ').title()} yüklendi."
                )

            except Exception as e:
                print(f"⚠️ [HATA] Koleksiyon yüklenemedi: {e}")
                continue

        # --------------------------------------------------
        # 5. DİNAMİK SEÇENEK KONTROLÜ
        # --------------------------------------------------
        secimden_gelen_soru = secenekten_soru_getir(SESSION_ID, soru)

        if secimden_gelen_soru:
            arama_sorusu = secimden_gelen_soru
            secenekleri_temizle(SESSION_ID)

            print(f"🧠 [HAFIZA] Seçim çözüldü: {arama_sorusu}")

        else:
            arama_sorusu = secimi_coz(
                soru,
                gecmis_diyalog,
                aktif_koleksiyon
            )

            if arama_sorusu != soru:
                print(f"🧠 [HAFIZA] Seçim çözüldü: {arama_sorusu}")

        # --------------------------------------------------
        # 6. RAG ARAMA SORUSUNU GÜÇLENDİRME
        # --------------------------------------------------
        rag_sorusu = arama_sorusunu_genislet(arama_sorusu)

        print("🔍 [İŞLEM] Teknik dökümanlar analiz ediliyor...")

        try:
            docs = db.similarity_search(rag_sorusu, k=4)
        except Exception as e:
            print(f"⚠️ [HATA] RAG araması yapılamadı: {e}")
            continue

        # --------------------------------------------------
        # 7. GENEL SORUDA RAG'DEN DİNAMİK SEÇENEK ÜRET
        # --------------------------------------------------
        if genel_soru_mu(soru) and not secimden_gelen_soru:
            print("\n" + "—" * 30 + " YANIT " + "—" * 30)

            netlestirme_metni, secenekler = netlestirme_olustur(
                soru,
                docs
            )

            print(netlestirme_metni)

            if secenekler:
                secenekleri_kaydet(SESSION_ID, secenekler)

            print("\n" + "—" * 67)

            hafizaya_kaydet(
                SESSION_ID,
                soru,
                netlestirme_metni
            )

            continue

        # --------------------------------------------------
        # 8. NORMAL CEVAP ÜRETİMİ
        # --------------------------------------------------
        print("\n" + "—" * 30 + " YANIT " + "—" * 30)

        cevap_akisi = cevap_olustur(
            gecmis_diyalog,
            arama_sorusu,
            docs
        )

        tam_cevap = ""

        for parca in cevap_akisi:
            print(parca, end="", flush=True)
            tam_cevap += parca

        print("\n" + "—" * 67)

        # --------------------------------------------------
        # 9. HAFIZAYA KAYDET
        # --------------------------------------------------
        hafizaya_kaydet(
            SESSION_ID,
            arama_sorusu,
            tam_cevap
        )


if __name__ == "__main__":
    main()