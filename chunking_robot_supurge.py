import re
import os

def chunk_verisi_hiyersarsik(input_dosyasi):
    """
    Metni 1., 1.1., 3.2.1. gibi başlık numaralarına göre böler.
    Bu yöntem anlamsal bütünlüğü (Semantic Integrity) en üst düzeye çıkarır.
    """
    if not os.path.exists(input_dosyasi):
        return print(f"[HATA] Dosya yok: {input_dosyasi}")

    with open(input_dosyasi, "r", encoding="utf-8") as f:
        ham_metin = f.read()

    # 1. BÖLÜM etiketlerini temizle (Sayfa numarasını metadata için sakla)
    sayfa_bazli = re.split(r'--- BÖLÜM: (\d+) ---', ham_metin)
    
    final_chunks = []

    for i in range(1, len(sayfa_bazli), 2):
        sayfa_no = int(sayfa_bazli[i])
        icerik = sayfa_bazli[i+1].strip()

        # 2. HİYERARŞİK BAŞLIKLARI YAKALA
        # Regex Açıklaması: Satır başında "1.", "1.1", "3.2.1" gibi sayı dizilerini yakalar.
        pattern = r'(\n(?:\d+\.)+\d*\s+|^\d+\.\d*\s+)'
        parcalar = re.split(pattern, icerik, flags=re.MULTILINE)
        
        # Parçaları birleştir (Regex split başlığı ayırdığı için çiftleri birleştiriyoruz)
        mevcut_baslik = ""
        for j in range(len(parcalar)):
            p = parcalar[j].strip()
            if not p: continue
            
            # Eğer parça bir başlık numarası ise (Örn: 3.2.1)
            if re.match(r'^(\d+\.)+\d*$', p):
                mevcut_baslik = p
            else:
                # İçerik ve başlığı birleştirip paketle
                tam_metin = f"{mevcut_baslik} {p}".strip()
                final_chunks.append({
                    "text": tam_metin,
                    "metadata": {
                        "source": "robot_supurge.pdf", 
                        "page": sayfa_no,
                        "section": mevcut_baslik
                    }
                })

    return final_chunks

def chunk_kaydet(chunks, cikti_dosyasi):
    with open(cikti_dosyasi, "w", encoding="utf-8") as f:
        for i, c in enumerate(chunks):
            f.write(f"ID: {i} | SAYFA: {c['metadata']['page']} | BAŞLIK: {c['metadata']['section']}\n")
            f.write(f"{c['text']}\n")
            f.write("-" * 50 + "\n")

if __name__ == "__main__":
    input_yolu = "robot_supurge_inceleme.txt" 
    cikti_yolu = "robot_supurge_hiyersarsik_chunks.txt"
    
    print(f"[İŞLEM] {input_yolu} hiyerarşik olarak bölünüyor...")
    parcalar = chunk_verisi_hiyersarsik(input_yolu)
    
    if parcalar:
        chunk_kaydet(parcalar, cikti_yolu)
        print(f"[BAŞARILI] {len(parcalar)} adet yapısal chunk oluşturuldu.")