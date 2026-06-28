import re
import os
from langchain_core.documents import Document 
from embedding import embedding_modelini_getir
from database_manager import veri_tabanina_kaydet
from langchain_community.vectorstores import Chroma

def txt_dosyasindan_db_olustur():
    INPUT_TXT = "robot_supurge_hiyersarsik_chunks.txt" 
    KOLEKSIYON_ADI = "robot_supurge_koleksiyonu"
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

    # --- 3. TEXT PARSING (Hiyerarşik Format Uyumu) ---
    try:
        with open(INPUT_TXT, "r", encoding="utf-8") as f:
            ham_metin = f.read()
    except FileNotFoundError:
        print(f"[HATA] {INPUT_TXT} bulunamadı!")
        return

    parcalar = ham_metin.split("-" * 50)
    hazir_dokumanlar = []

    # GÜNCELLENEN REGEX: "BAŞLIK" kısmını da kapsayacak şekilde esnetildi
    # Format: ID: 0 | SAYFA: 4 | BAŞLIK: 1.1
    pattern = r"ID: \d+ \| SAYFA: (\d+).*?BAŞLIK: (.*?)\n(.*)"

    for p in parcalar:
        p = p.strip()
        if not p: continue
        
        match = re.search(pattern, p, re.DOTALL)
        if match:
            sayfa_no = int(match.group(1))
            baslik = match.group(2).strip()
            icerik = match.group(3).strip()
            
            doc = Document(
                page_content=icerik,
                metadata={
                    "source": "robot_supurge.pdf", 
                    "page": sayfa_no,
                    "section": baslik
                }
            )
            hazir_dokumanlar.append(doc)

    # --- 4. VERİTABANINA KAYIT ---
    print(f"🧩 {len(hazir_dokumanlar)} parça yeni hiyerarşik etiketlerle vektörleştiriliyor...")
    
    if len(hazir_dokumanlar) == 0:
        print("[HATA] Regex eşleşmesi başarısız! Parça sayısı 0.")
        return

    try:
        vector_db = veri_tabanina_kaydet(
            parcalar=hazir_dokumanlar,
            embedding_modeli=model,
            koleksiyon_adi=KOLEKSIYON_ADI,
            db_yolu=DB_YOLU
        )
        print(f"\n✅ BAŞARILI: '{KOLEKSIYON_ADI}' hiyerarşik yapıda oluşturuldu!")
        
    except Exception as e:
        print(f"\n❌ Veritabanı hatası: {e}")

if __name__ == "__main__":
    txt_dosyasindan_db_olustur()