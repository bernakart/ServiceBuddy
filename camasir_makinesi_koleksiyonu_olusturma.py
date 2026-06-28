import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from embedding import embedding_modelini_getir # Senin hazırladığın embedding modülü

# --- KONFİGÜRASYON ---
KAYNAK_DOSYA = "camasir_makinesi_inceleme.txt"
DB_YOLU = "./kilavuzlar.db"
KOLEKSIYON_ADI = "camasir_makinesi_koleksiyonu"

def koleksiyon_olustur():
    # 1. DOSYA KONTROLÜ
    if not os.path.exists(KAYNAK_DOSYA):
        print(f"[HATA] {KAYNAK_DOSYA} bulunamadı! İşlem iptal edildi.")
        return

    # 2. ESKİ VERİLERİ TEMİZLE (Idempotency)
    # Aynı isimli koleksiyon varsa üzerine yazmak yerine temizleyip baştan oluşturuyoruz
    client = chromadb.PersistentClient(path=DB_YOLU)
    mevcutlar = [c.name for c in client.list_collections()]
    if KOLEKSIYON_ADI in mevcutlar:
        print(f"[TEMİZLİK] '{KOLEKSIYON_ADI}' zaten mevcut. Güncelleme için siliniyor...")
        client.delete_collection(KOLEKSIYON_ADI)

    # 3. METNİ OKU VE PARÇALA
    with open(KAYNAK_DOSYA, "r", encoding="utf-8") as f:
        metin = f.read()

    # Az önceki chunking stratejini buraya birebir yansıtıyoruz
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    parcalar = text_splitter.create_documents([metin])
    print(f"[BİLGİ] {len(parcalar)} adet parça vektör veritabanına hazırlandı.")

    # 4. EMBEDDING MODELİNİ YÜKLE VE KAYDET
    print("[BİLGİ] Embedding modeli yükleniyor... (Bu biraz zaman alabilir)")
    model = embedding_modelini_getir()

    print(f"[BİLGİ] Vektörler oluşturuluyor ve '{DB_YOLU}' konumuna kaydediliyor...")
    
    # ChromaDB'ye kayıt işlemi
    vector_db = Chroma.from_documents(
        documents=parcalar,
        embedding=model,
        persist_directory=DB_YOLU,
        collection_name=KOLEKSIYON_ADI
    )

    print(f"\n[BAŞARILI] '{KOLEKSIYON_ADI}' koleksiyonu oluşturuldu!")
    print(f"Toplam Vektör Sayısı: {len(parcalar)}")

if __name__ == "__main__":
    koleksiyon_olustur()