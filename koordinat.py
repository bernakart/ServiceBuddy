import pdfplumber

def ifade_konumu_bul(pdf_yolu, sayfa_no, hedef_kelime):
    print(f"--- Sayfa {sayfa_no} üzerinde '{hedef_kelime}' aranıyor ---")
    
    with pdfplumber.open(pdf_yolu) as pdf:
        if sayfa_no > len(pdf.pages):
            print("Hata: Sayfa numarası PDF sınırları dışında.")
            return

        sayfa = pdf.pages[sayfa_no - 1] # Index 0'dan başlar
        
        # 1. Kelime bazlı arama yapalım
        kelimeler = sayfa.extract_words()
        bulundu = False

        for i, kelime in enumerate(kelimeler):
            # "•" ve "Şebeke" kelimeleri yan yana mı kontrol et
            if "Şebeke" in kelime['text']:
                # Bir önceki kelime madde işareti mi?
                onceki = kelimeler[i-1]['text'] if i > 0 else ""
                
                print(f"Bulunan Kelime: '{kelime['text']}'")
                print(f"Tam Koordinatlar:")
                print(f"  - Sol Sınır (x0): {round(kelime['x0'], 2)}")
                print(f"  - Üst Sınır (top): {round(kelime['top'], 2)}")
                print(f"  - Sağ Sınır (x1): {round(kelime['x1'], 2)}")
                print(f"  - Alt Sınır (bottom): {round(kelime['bottom'], 2)}")
                
                if "•" in onceki:
                    print(f"\n[BİLGİ] Madde işareti (•) hemen solunda tespit edildi (x0={round(kelimeler[i-1]['x0'], 2)})")
                
                bulundu = True
                # Genelde sayfada bir tane olur, istersen break'i kaldırıp hepsini görebilirsin
                break 

        if not bulundu:
            print("İfade bu sayfada bulunamadı.")

# Kullanım:
pdf_yolu = r"C:\Users\berna\Desktop\tubitak_proje\kilavuzlar\robot_supurge.pdf"
ifade_konumu_bul(pdf_yolu, 4, "Şebeke")