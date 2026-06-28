import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- AYARLAR ---
KAYNAK_DOSYA = "camasir_makinesi_inceleme.txt"
CHUNKS_CIKTI_DOSYASI = "camasir_makinesi_chunks.txt"

def chunking_islem_merkezi():
    # 1. DOSYA KONTROLÜ
    if not os.path.exists(KAYNAK_DOSYA):
        print(f"[HATA] {KAYNAK_DOSYA} bulunamadı! Lütfen dosya adını kontrol edin.")
        return

    # 2. METNİ OKU
    with open(KAYNAK_DOSYA, "r", encoding="utf-8") as f:
        metin = f.read()

    # 3. METNİ PARÇALA (Chunking Stratejisi)
    # Tabloların ve 'Sorun Giderme' maddelerinin bölünmemesi için chunk_size'ı 
    # optimize ediyoruz. Overlap ise bölümler arası geçişi yumuşatır.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,    # 1200 karakter, tabloları tek parça tutmak için idealdir.
        chunk_overlap=200,   # 200 karakterlik örtüşme, bağlam kaybını önler.
        separators=["\n\n", "\n", " ", ""] # Önce çift satıra, sonra tek satıra odaklanır.
    )
    
    parcalar = text_splitter.create_documents([metin])
    print(f"[BİLGİ] Metin toplam {len(parcalar)} parçaya bölündü.")

    # 4. PARÇALARI TXT OLARAK KAYDET (Görsel Analiz İçin)
    try:
        with open(CHUNKS_CIKTI_DOSYASI, "w", encoding="utf-8") as f:
            f.write(f"=== {KAYNAK_DOSYA} CHUNKS ANALİZ RAPORU ===\n")
            f.write(f"Parça Sayısı: {len(parcalar)}\n")
            f.write("="*50 + "\n\n")
            
            for i, doc in enumerate(parcalar, 1):
                f.write(f"--- PARÇA {i} (Karakter Sayısı: {len(doc.page_content)}) ---\n")
                f.write(doc.page_content)
                f.write("\n\n" + "*"*20 + " PARÇA SONU " + "*"*20 + "\n\n")
        
        print(f"[BAŞARILI] Chunks'lar kontrol için '{CHUNKS_CIKTI_DOSYASI}' dosyasına yazıldı.")
        print(f"Lütfen '{CHUNKS_CIKTI_DOSYASI}' dosyasını açıp bölümleri kontrol edin.")
        
    except Exception as e:
        print(f"[UYARI] Dosya yazılırken bir hata oluştu: {e}")

if __name__ == "__main__":
    chunking_islem_merkezi()