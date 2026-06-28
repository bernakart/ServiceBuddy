import redis

def redis_test_et():
    try:
        # Docker üzerinde çalışan Redis'e bağlanıyoruz
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # 'ping' komutu Redis'in hayatta olup olmadığını kontrol eder
        if r.ping():
            print("\n✅ BAŞARILI: Redis konteynerine ulaşıldı!")
            
            # Küçük bir veri yazma ve okuma testi
            r.set("kullanici_notu", "Selam Berna, Redis hafızası çalışıyor!")
            mesaj = r.get("kullanici_notu")
            print(f"📥 Veritabanından Okunan: {mesaj}")
            
    except redis.exceptions.ConnectionError:
        print("\n❌ HATA: Redis konteynerine bağlanılamadı. Docker Desktop'ın açık olduğundan emin ol.")
    except Exception as e:
        print(f"\n❌ BEKLENMEDİK HATA: {e}")

if __name__ == "__main__":
    redis_test_et()