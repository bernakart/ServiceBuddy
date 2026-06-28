import pdfplumber
import re
import os

def metin_onar(metin):
    if not metin: return ""
    
    metin = metin.replace("üfleme", "###UFLEME###")
    
    # 2. Standart Karakter Onarımı
    onari = {
        '›': 'ı', 'fl': 'ş', '€': 'ğ', '‹': 'İ', 'çal›fl': 'çalış', 'ıflı': 'ışı',
        'fiflini': 'fişini', 'ifllemleri': 'işlemleri', 'de€ildir': 'değildir'
    }
    for h, d in onari.items():
        metin = metin.replace(h, d)
    
    # 3. Madde İşaretlerini Standartlaştır (LLM madde yapısını '*' ile daha iyi anlar)
    metin = metin.replace("•", "\n* ")
    
    # 4. TİRE VE SAYFA NO TEMİZLEME (GELİŞMİŞ): 
    # "döke- 5 \n rek" -> "dökerek" yapar. Sayfa numarasını (5) ve tireyi yok eder.
    metin = re.sub(r'(\w+)-\s*(?:\d+\s+)?\n\s*([a-zğüşiöçİĞÜŞÖÇ]+)', r'\1\2', metin)
    
    # 5. SATIR BİRLEŞTİRME (YENİ): 
    # Bir satır nokta, ünlem veya soru işareti ile bitmiyorsa; 
    # bir sonraki satırı (liste başı değilse) mevcut satırla birleştirir.
    # Bu, "su haznesi,\n yerine takılıyken" -> "su haznesi, yerine takılıyken" yapar.
    metin = re.sub(r'(?<![.!?:])\n\s*(?![*•\d\-])', ' ', metin)
    
    # 6. RAKAM VE KELİME YAPIŞIKLIĞINI ÇÖZ (Örn: 5damla -> 5 damla)
    metin = re.sub(r'(\d+)([a-zA-ZğüşiöçİĞÜŞÖÇ]+)', r'\1 \2', metin)
    
    # 7. Son Temizlik
    metin = metin.replace("###UFLEME###", "üfleme")
    metin = re.sub(r' +', ' ', metin) # Fazla boşlukları tek boşluğa indir
    
    return metin.strip()

def tabloyu_metne_donustur(tablo):
    if not tablo or len(tablo) < 2: return ""
    sutun_sayisi = len(tablo[0])
    basliklar = [metin_onar(str(tablo[0][i])) if tablo[0][i] else f"B_{i}" for i in range(sutun_sayisi)]
    son_degerler = [""] * sutun_sayisi
    temiz_metin = ""
    for satir in tablo[1:]:
        if not any(satir): continue
        hucreler = []
        for i in range(sutun_sayisi):
            val = str(satir[i]).strip() if i < len(satir) and satir[i] else ""
            if not val or val == "None": val = son_degerler[i]
            else: son_degerler[i] = val
            hucreler.append(metin_onar(val))
        temiz_metin += "Tablo Verisi -> " + " | ".join([f"{basliklar[i]}: {hucreler[i]}" for i in range(len(basliklar))]) + "\n"
    return temiz_metin

def akilli_sayfa_oku(sayfa, sayfa_no):
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
    for rect in sayfa.rects:
        if rect['x0'] < 100 and 10 < rect['width'] < 35:
            ayraclar.add(round(rect['top'], 1))
    
    sirali_ayraclar = sorted(list(ayraclar))
    final_metin = []

    for i in range(len(sirali_ayraclar) - 1):
        ust, alt = sirali_ayraclar[i], sirali_ayraclar[i+1]
        if alt - ust < 2: continue

        tablo_icerik = next((t["icerik"] for t in tablo_bantlari if abs(t["ust"] - ust) < 1), None)
        
        if tablo_icerik:
            final_metin.append(tablo_icerik)
        else:
            bolge = sayfa.within_bbox((0, ust, genislik, alt))
            maddeler = [c for c in bolge.chars if c['text'] == '•']
            ikinci_sutun = next((m for m in maddeler if m['x0'] > genislik * 0.4), None)
            
            if ikinci_sutun:
                sinir_x = ikinci_sutun['x0'] - 5
                sol = bolge.within_bbox((0, ust, sinir_x, alt)).extract_text() or ""
                sag = bolge.within_bbox((sinir_x, ust, genislik, alt)).extract_text() or ""
                # Sütunları önce onarıp sonra birleştiriyoruz
                content = metin_onar(sol) + "\n" + metin_onar(sag)
            else:
                content = metin_onar(bolge.extract_text())
                
            if content.strip():
                final_metin.append(content)

    return "\n".join(final_metin)

def pdf_oku(dosya_yolu):
    with pdfplumber.open(dosya_yolu) as pdf:
        # Sayfalar arasına boşluk koyarak bütünlüğü koruyoruz
        return "\n\n\n\n\n".join([f"BÖLÜM: {akilli_sayfa_oku(s, i)}" for i, s in enumerate(pdf.pages, 1)])

# --- DOSYA KAYIT BLOĞU ---
if __name__ == "__main__":
    yol = r"C:\Users\berna\Desktop\tubitak_proje\kilavuzlar\hava_nemlendiricisi.pdf"
    cikti_ismi = "hava_nemlendirici_inceleme.txt"

    if os.path.exists(yol):
        print(f"--- Hava Nemlendirici PDF Okunuyor ---")
        icerik = pdf_oku(yol)
        
        # UTF-8 encoding Türkçe karakterlerin (ğ, ş, ı) bozulmaması için kritiktir.
        with open(cikti_ismi, "w", encoding="utf-8") as f:
            f.write(icerik)
        
        print(f"\n[BAŞARILI] Tüm içerik '{cikti_ismi}' dosyasına kaydedildi.")
    else:
        print(f"[HATA] PDF dosyası belirtilen yolda bulunamadı: {yol}")