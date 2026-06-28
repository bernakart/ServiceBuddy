import pdfplumber
import re
import os

def akilli_ayna_duzelt(metin):
    """
    Dikey yazıldığı için ters dönen başlıkları (Örn: ')tl( imiteküt uS') 
    büyük harf takibi yaparak düzeltir.
    """
    if not metin or len(metin) < 2: return metin
    temiz = metin.strip()
    
    # MÜHENDİSLİK MANTIĞI: Eğer ilk harf büyük DEĞİLSE ama son harf BÜYÜKSE terstir.
    # Ayrıca parantezlerin yerleşimini de kontrol eder.
    if (not temiz[0].isupper() and temiz[-1].isupper()) or (temiz.startswith(')') and temiz.endswith('(')):
        return temiz[::-1].strip()
    return temiz

def metin_onar(metin):
    """
    Karakter hatalarını giderir ve font kaynaklı 'u' madde işaretlerini düzeltir.
    """
    if not metin: return ""
    
    # 1. Madde İşareti Onarımı (Özel Font Hataları)
    # Satır başındaki 'u ' parazitlerini '*' işaretine çevirir.
    metin = re.sub(r'(?m)^u\s+', '* ', metin)
    
    # 2. Teknik Terim Koruma (Mürsas projesi için kritik)
    metin = metin.replace("üfleme", "###UFLEME###")
    
    # 3. Arçelik PDF Karakter Onarımı
    onari = {
        '›': 'ı', 'fl': 'ş', '€': 'ğ', '‹': 'İ', 'çal›fl': 'çalış', 
        'ıflı': 'ışı', 'fiflini': 'fişini', 'ifllemleri': 'işlemleri', 'de€ildir': 'değildir'
    }
    for h, d in onari.items():
        metin = metin.replace(h, d)
    
    # 4. Standart Madde ve Yazım Düzeltmeleri
    metin = metin.replace("•", "\n* ")
    metin = re.sub(r'(\w+)-\s*(?:\d+\s+)?\n\s*([a-zğüşiöçİĞÜŞÖÇ]+)', r'\1\2', metin)
    metin = re.sub(r'(?<![.!?:])\n\s*(?![*•\d\-])', ' ', metin)
    metin = re.sub(r'(\d+)([a-zA-ZğüşiöçİĞÜŞÖÇ]+)', r'\1 \2', metin)
    
    # 5. Son Temizlik
    metin = metin.replace("###UFLEME###", "üfleme")
    metin = re.sub(r' +', ' ', metin)
    
    return metin.strip()

def tabloyu_metne_donustur(tablo):
    """
    Tabloyu sütun sütun (Kumaş Tipi bazlı) okuyarak atomik hale getirir.
    Sıralama: Kumaş Tipi -> Tüm Kir Seviyeleri.
    """
    if not tablo or len(tablo) < 4: return ""

    # 1. BAŞLIKLARI VE KİRLİLİK TANIMLARINI HAZIRLA
    # image_59a5e4.png'de 0. satır kumaş tipleridir.
    kumas_tipleri = [akilli_ayna_duzelt(metin_onar(str(h))) for h in tablo[0]]
    
    # Kir seviyelerini ve açıklamalarını bir listede tutalım (Sol sütun)
    kir_bilgileri = []
    for satir in tablo[2:]: # 2. satırdan itibaren (Sıcaklıkları geçiyoruz)
        kir_adi = akilli_ayna_duzelt(metin_onar(str(satir[0])))
        if kir_adi and "Kir Miktarı" not in kir_adi:
            kir_bilgileri.append(kir_adi)

    serilestirilmis_metin = ""

    # 2. SÜTUN BAZLI DÖNGÜ (Dış döngü sütunlar olmalı)
    # i=2'den başlıyoruz çünkü 0 ve 1. sütunlar açıklama kısımlarıdır.
    for i in range(2, len(tablo[0])):
        su_anli_kumas = kumas_tipleri[i]
        if not su_anli_kumas or su_anli_kumas == "None": continue

        # İç döngüde bu kumaş tipi için tüm satırları (kir seviyelerini) gez
        for satir_idx, satir in enumerate(tablo[2:]):
            if satir_idx >= len(kir_bilgileri): break
            
            su_anli_kir = kir_bilgileri[satir_idx]
            oneri = akilli_ayna_duzelt(metin_onar(str(satir[i])))

            if oneri and len(oneri) > 10:
                # TEKNİK VERİ: Tüm kimlik bilgileri en başta.
                serilestirilmis_metin += (
                    f"Cihaz: Çamaşır Makinesi | Kumaş Tipi: {su_anli_kumas} | "
                    f"Kir Seviyesi: {su_anli_kir} | "
                    f"Yıkama Önerisi: {oneri}\n\n"
                )
        
        # Her kumaş tipi bitiminde bir sayfa ayracı koyarak chunking'i kolaylaştırabilirsin
        serilestirilmis_metin += "\n" + "-"*30 + "\n\n"
    
    return serilestirilmis_metin
def akilli_sayfa_oku(sayfa):
    """
    Sayfa koordinatlarını kullanarak metin ve tabloları doğru sırada birleştirir.
    """
    genislik, yukseklik = sayfa.width, sayfa.height
    y0, y1 = yukseklik * 0.03, yukseklik * 0.95 

    tablolar = sayfa.find_tables()
    tablo_bantlari = []
    for t in tablolar:
        tablo_bantlari.append({
            "ust": t.bbox[1],
            "alt": t.bbox[3],
            "icerik": tabloyu_metne_donustur(t.extract())
        })

    ayraclar = {y0, y1}
    for t in tablo_bantlari:
        ayraclar.add(t["ust"])
        ayraclar.add(t["alt"])
    
    sirali_ayraclar = sorted(list(ayraclar))
    final_metin = []

    for i in range(len(sirali_ayraclar) - 1):
        ust, alt = sirali_ayraclar[i], sirali_ayraclar[i+1]
        if alt - ust < 2: continue

        # Tablo mu yoksa metin bölgesi mi kontrol et
        tablo_icerik = next((t["icerik"] for t in tablo_bantlari if abs(t["ust"] - ust) < 1), None)
        
        if tablo_icerik:
            final_metin.append(tablo_icerik)
        else:
            bolge = sayfa.within_bbox((0, ust, genislik, alt))
            content = metin_onar(bolge.extract_text())
            if content.strip():
                final_metin.append(content)

    return "\n".join(final_metin)

def pdf_oku(dosya_yolu):
    with pdfplumber.open(dosya_yolu) as pdf:
        # Sayfaları 5 adet boş satırla ayırarak bütünlüğü korur.
        return "\n\n\n\n\n".join([f"BÖLÜM: {akilli_sayfa_oku(s)}" for i, s in enumerate(pdf.pages, 1)])

if __name__ == "__main__":
    yol = r"C:\Users\berna\Desktop\tubitak_proje\kilavuzlar\camasir_makinesi.pdf"
    cikti_ismi = "camasir_makinesi_inceleme.txt"

    if os.path.exists(yol):
        print(f"[İŞLEM] Çamaşır Makinesi PDF serileştiriliyor...")
        icerik = pdf_oku(yol)
        
        with open(cikti_ismi, "w", encoding="utf-8") as f:
            f.write(icerik)
        
        print(f"\n[BAŞARILI] '{cikti_ismi}' dosyası hatasız şekilde oluşturuldu.")
    else:
        print(f"[HATA] PDF bulunamadı: {yol}")