import pdfplumber
import re
import os

def metin_onar(metin):
    """Bölünmüş kelimeleri birleştirir ve karakterleri onarır."""
    if not metin: return ""
    metin = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', metin)
    onari = {'›': 'ı', 'fl': 'ş', '€': 'ğ', '‹': 'İ', 'çal›fl': 'çalış', 'ıflı': 'ışı'}
    for h, d in onari.items(): metin = metin.replace(h, d)
    metin = metin.replace("•", "\n* ")
    metin = re.sub(r'(?<![.!?:])\n\s*(?![*•\d\-])', ' ', metin)
    return re.sub(r' +', ' ', metin).strip()

def kirmizi_sinyal_var_mi(sayfa):
    """
    Sayfada kırmızı renkte nesne olup olmadığını kontrol eder.
    Float hatasını (TypeError) engellemek için tip kontrolü eklenmiştir.
    """
    for obj in sayfa.chars + sayfa.rects + sayfa.lines:
        color = obj.get("non_stroking_color") or obj.get("stroking_color")
        
        # HATA ÇÖZÜMÜ: Sadece liste veya tuple ise len() kontrolü yap
        if isinstance(color, (list, tuple)) and len(color) == 3:
            # RGB: Kırmızı yoğunluğu yüksek, diğerleri düşük mü?
            if color[0] > 0.8 and color[1] < 0.2 and color[2] < 0.2:
                return True
        # Eğer color tek bir float ise (gri tonlama), sistem hata vermeden devam eder.
    return False

def akilli_sayfa_oku(sayfa, sayfa_no):
    genislik, yukseklik = sayfa.width, sayfa.height
    
    # KALİBRASYON: Header %8, Footer %94
    header_hizasi = yukseklik * 0.08 
    footer_hizasi = yukseklik * 0.94

    if sayfa_no in [7, 8]: return ""

    # 1. SABİT KOORDİNATLI OKUMA (Sayfa 4, 5, 6)
    if sayfa_no in [4, 5, 6]:
        fixed_split_x = 214.72 
        baslik = sayfa.within_bbox((0, 0, genislik, header_hizasi)).extract_text() or ""
        sol = sayfa.within_bbox((0, header_hizasi, fixed_split_x, footer_hizasi)).extract_text() or ""
        sag = sayfa.within_bbox((fixed_split_x, header_hizasi, genislik, footer_hizasi)).extract_text() or ""
        return metin_onar(baslik) + "\n\n" + metin_onar(sol) + "\n\n" + metin_onar(sag)

    # 2. DİNAMİK RENK TETİKLEMESİ
    elif kirmizi_sinyal_var_mi(sayfa):
        # Sayfayı 3 sütuna bölerek oku
        sinir1, sinir2 = genislik * 0.33, genislik * 0.66
        kirmizi = sayfa.within_bbox((0, header_hizasi, sinir1, footer_hizasi)).extract_text() or ""
        mavi = sayfa.within_bbox((sinir1, header_hizasi, sinir2, footer_hizasi)).extract_text() or ""
        sari = sayfa.within_bbox((sinir2, header_hizasi, genislik, footer_hizasi)).extract_text() or ""
        return metin_onar(kirmizi) + "\n\n" + metin_onar(mavi) + "\n\n" + metin_onar(sari)

    # 3. STANDART OKUMA
    else:
        kirpilmis = sayfa.within_bbox((0, 0, genislik, footer_hizasi))
        return metin_onar(kirpilmis.extract_text(layout=True) or "")

def robot_supurge_loader_main():
    yol = r"C:\Users\berna\Desktop\tubitak_proje\kilavuzlar\robot_supurge.pdf"
    if not os.path.exists(yol): return print(f"[HATA] Dosya bulunamadı: {yol}")
    
    with pdfplumber.open(yol) as pdf:
        final_metin = []
        print("[İŞLEM] Veriler tip kontrolü ve renk tetiklemesiyle işleniyor...")
        for i, sayfa in enumerate(pdf.pages, 1):
            icerik = akilli_sayfa_oku(sayfa, i)
            if icerik: final_metin.append(f"--- BÖLÜM: {i} ---\n{icerik}")
        
        with open("robot_supurge_inceleme.txt", "w", encoding="utf-8") as f:
            f.write("\n\n\n".join(final_metin))
    print("\n[BAŞARILI] Dataset hatasız şekilde 'robot_supurge_dataset.txt' dosyasına kaydedildi.")

if __name__ == "__main__":
    robot_supurge_loader_main()