import os
from embedding import embedding_modelini_getir
from langchain_community.vectorstores import Chroma
from llm_manager import cevap_olustur 

def main():
    DB_YOLU = "./kilavuzlar.db"
    
    print("="*50)
    print("🛠️ ARÇELİK TEKNİK DESTEK SİSTEMİ")
    print("="*50)
    print("Lütfen bilgi almak istediğiniz cihazı seçin:")
    print("1: Çamaşır Makinesi ")
    print("2: Hava Nemlendirici ")
    print("3: Robot Süpürge  ") 
    
    secim = input("\nSeçiminiz (1/2/3): ")
    
    if secim == "1":
        koleksiyon = "camasir_makinesi_koleksiyonu"
    elif secim == "2":
        koleksiyon = "hava_nemlendirici_koleksiyonu"
    elif secim == "3":
        koleksiyon = "robot_supurge_koleksiyonu"
    else:
        print("[HATA] Geçersiz seçim! Program sonlandırılıyor.")
        return

    # --- 2. EMBEDDING VE DB BAĞLANTISI ---
    print(f"\n[BİLGİ] {koleksiyon} veritabanı bağlantısı kuruluyor...")
    
    # ECE Mühendisliği yaklaşımıyla: Modeli belleğe bir kez yükleyip verimli kullanıyoruz
    model = embedding_modelini_getir()
    
    try:
        db = Chroma(
            persist_directory=DB_YOLU,
            embedding_function=model,
            collection_name=koleksiyon
        )
        print(f"[BAŞARILI] {koleksiyon} koleksiyonu aktif edildi.")
    except Exception as e:
        print(f"[HATA] Veritabanı bağlantısı başarısız: {e}")
        return

    # --- 3. SORU-CEVAP DÖNGÜSÜ ---
    print("\n" + "-"*40)
    print("Asistan hazır. Sorularınızı sorabilirsiniz.")
    print("(Çıkış yapmak için 'q' yazın)")
    print("-"*40)

    while True:
        soru = input("\nSorgunuz: ")
        
        if soru.lower() == 'q':
            print("\n[SİSTEM] Oturum sonlandırıldı. İyi çalışmalar Berna!")
            break

        if not soru.strip():
            continue

        # A. Benzerlik Araması (Similarity Search)
        # H-2 Doğruluk için en alakalı 5 parçayı (chunk) getiriyoruz
        print(f"[İŞLEM] Vektör tabanında arama yapılıyor...")
        # main.py içinde arama kısmını böyle güncelle:
        docs = db.max_marginal_relevance_search(soru, k=4, fetch_k=10)
        print(f"DEBUG: Çekilen ilk parçanın içeriği: {docs[0].page_content[:100]}...")
        # B. Yanıt Üretimi (RAG İş akışı)
        print("[İŞLEM] Llama 3 verileri analiz ediyor...")
        cevap = cevap_olustur(soru, docs)
       # Metadata'dan sayfa numaralarını çekiyoruz
        sayfalar = []
        for d in docs:
            p = d.metadata.get('page', 'Bilinmiyor')
            if str(p) not in sayfalar:
                sayfalar.append(str(p))

        # Çıktıyı birleştiriyoruz
        final_output = f"{cevap}\n\n[Bu bilgiler kılavuzun {', '.join(sayfalar)}. sayfalarından alınmıştır.]"
        print(final_output)
if __name__ == "__main__":
    main()