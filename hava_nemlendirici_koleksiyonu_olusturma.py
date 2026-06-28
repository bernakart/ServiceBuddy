import re
import os
from langchain_core.documents import Document 
from embedding import embedding_modelini_getir
from database_manager import veri_tabanina_kaydet
from langchain_community.vectorstores import Chroma

def hava_nemlendirici_db_olustur():
    # --- 1. AYARLAR ---
    INPUT_TXT = "hava_nemlendirici_chunks.txt" 
    KOLEKSIYON_ADI = "hava_nemlendirici_koleksiyonu"
    DB_YOLU = "./kilavuzlar.db"

    print(f"📂 {INPUT_TXT} dosyası okunuyor...")

    # --- 2. KOLEKSİYON TEMİZLEME ---
    model = embedding_modelini_getir()
    if os.path.exists(DB_YOLU):
        try:
            gecici_db = Chroma(persist_directory=DB_YOLU, collection_name=KOLEKSIYON_ADI, embedding_function=model)
            gecici_db.delete_collection()
            print(f"🗑️ Eski '{KOLEKSIYON_ADI}' koleksiyonu silindi.")
        except:
            print(f"[BİLGİ] Temizlenecek eski bir koleksiyon bulunamadı.")

    # --- 3. TEXT PARSING (Basit Format Uyumu) ---
    try:
        with open(INPUT_TXT, "r", encoding="utf-8") as f:
            ham_metin = f.read()
    except FileNotFoundError:
        print(f"[HATA] {INPUT_TXT} bulunamadı!")
        return

    # Parçaları ayırıcıya göre böl
    parcalar = ham_metin.split("-" * 50)
    hazir_dokumanlar = []

    # YENİ REGEX: Sadece ID'yi yakalar ve altındaki her şeyi içerik olarak alır
    # Senin hava_nemlendirici_chunks.txt dosyanın formatına (ID: 0) tam uyumlu.
    pattern = r"ID: \d+\n(.*)"

    for p in parcalar:
        p = p.strip()
        if not p: continue
        
        match = re.search(pattern, p, re.DOTALL)
        if match:
            icerik = match.group(1).strip()
            
            # Not: Bu dosyada sayfa/başlık bilgisi başlıkta olmadığı için 
            # metadata'yı varsayılan değerlerle dolduruyoruz.
            doc = Document(
                page_content=icerik,
                metadata={
                    "source": "hava_nemlendiricisi.pdf", 
                    "page": "Bilinmiyor",
                    "section": "Genel"
                }
            )
            hazir_dokumanlar.append(doc)

    # --- 4. VERİTABANINA KAYIT ---
    print(f"🧩 {len(hazir_dokumanlar)} parça vektörleştiriliyor...")
    
    if len(hazir_dokumanlar) == 0:
        print("[HATA] Regex eşleşmesi başarısız! Parça sayısı hala 0. Lütfen dosya içeriğini kontrol et.")
        return

    try:
        vector_db = veri_tabanina_kaydet(
            parcalar=hazir_dokumanlar,
            embedding_modeli=model,
            koleksiyon_adi=KOLEKSIYON_ADI,
            db_yolu=DB_YOLU
        )
        print(f"\n✅ BAŞARILI: '{KOLEKSIYON_ADI}' başarıyla oluşturuldu!")
        
    except Exception as e:
        print(f"\n❌ Veritabanı hatası: {e}")

if __name__ == "__main__":
    hava_nemlendirici_db_olustur()