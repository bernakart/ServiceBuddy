import os
import re
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

KAYNAK_DOSYA = "hava_nemlendirici_inceleme.txt"
CIKTI_TXT = "hava_nemlendirici_chunks.txt"
KOLEKSIYON_ADI = "hava_nemlendirici_koleksiyonu"
DB_YOLU = "./kilavuzlar.db"

def metin_onar(metin):
    """
    Sadece gereksiz yatay boşlukları temizler. 
    Dikey yapıları (\n) korur ki splitter başlıkları yakalayabilsin.
    """
    if not metin: return ""
    # Birden fazla boşluğu teke indir ama satır sonlarına dokunma
    metin = re.sub(r'[ \t]+', ' ', metin)
    return metin.strip()

def metni_parcala(ham_metin):
    """
    H-2 Doğruluk için: Metni BÖLÜM başlıklarına ve madde işaretlerine (* ) 
    göre akıllıca böler. Tekrarları (overlap) minimize eder.
    """
    temiz_metin = metin_onar(ham_metin)
    
    # SEPARATORS: Öncelik sırası çok önemli.
    # Önce Bölümlere, sonra paragraflara, sonra madde işaretlerine bakar.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=50,   # Tekrarı önlemek için overlap'i 200'den 50'ye çektik.
        separators=[
            "\nBÖLÜM",      # Ana bölümleri asla bölme
            "\n\n",         # Büyük paragraflar
            "\n*",          # Madde işaretleri (En kritik ayar!)
            "\n",           # Satır sonları
            ". ",           # Cümleler
            " "             # Kelimeler
        ],
        is_separator_regex=False
    )
    
    parcalar = text_splitter.create_documents([temiz_metin])
    return parcalar

def chunk_dosyasi_olustur(parcalar, dosya_adi):
    """Gözle kontrol için ID bazlı temiz bir txt çıktısı üretir."""
    print(f"[İŞLEM] '{dosya_adi}' oluşturuluyor...")
    with open(dosya_adi, "w", encoding="utf-8") as f:
        for i, doc in enumerate(parcalar):
            # Metadata eklemesi (Varsa orijinal metindeki sayfa bilgisini çekebilirsin)
            f.write(f"ID: {i}\n")
            f.write(f"{doc.page_content}\n")
            f.write("-" * 50 + "\n")
    print(f"[TAMAM] Kontrol dosyası hazır.")

def hava_nemlendirici_islem_merkezi():
    print("="*50)
    print("💧 HAVA NEMLENDİRİCİ VERİ ENTEGRASYONU")
    print("="*50)

    # 1. DOSYA OKUMA
    if not os.path.exists(KAYNAK_DOSYA):
        print(f"[HATA] {KAYNAK_DOSYA} bulunamadı!")
        return

    with open(KAYNAK_DOSYA, "r", encoding="utf-8") as f:
        ham_metin = f.read()

    # 2. PARÇALAMA (CHUNKING)
    parcalar = metni_parcala(ham_metin)
    print(f"[BİLGİ] Metin {len(parcalar)} anlamlı parçaya ayrıldı.")

    # 3. TXT ÇIKTISI (Validation)
    chunk_dosyasi_olustur(parcalar, CIKTI_TXT)

if __name__ == "__main__":
    hava_nemlendirici_islem_merkezi()