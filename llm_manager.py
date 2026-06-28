import os 
import re
from langchain_ollama import OllamaLLM


FALLBACK_CEVAP = (
    "Kılavuzda bu işlemin nasıl yapılacağına dair detaylı bir adım bulunmamaktadır. "
    "Yetkili servise danışmanızı öneririm."
)

GENEL_NETLESTIRME_CEVABI = (
    "Sorunu netleştirmek için cihazda gördüğünüz belirtiyi biraz daha açık yazar mısınız?"
)


def secimi_coz(soru, konusma_gecmisi="", aktif_koleksiyon=None):
    """
    Eski sabit 1-2-3-4 eşleştirme artık kullanılmıyor.
    Seçimler Redis'teki dinamik seçeneklerden main1.py içinde çözülüyor.
    """
    return soru


def genel_soru_mu(soru):
    """
    Kullanıcı çok genel bir arıza yazıyorsa RAG'den gelen parçalara göre
    dinamik seçenek listesi üretilecek.
    """
    soru = str(soru).lower().strip()

    genel_ifadeler = [
        "çalışmıyor",
        "calismiyor",
        "çalışmıyo",
        "calismiyo",
        "bozuldu",
        "sorun var",
        "arıza var",
        "ariza var",
        "tepki vermiyor",
        "tepki vermiyo"
    ]

    return any(ifade in soru for ifade in genel_ifadeler)


def arama_sorusunu_genislet(soru):
    """
    RAG aramasını güçlendirmek için teknik anahtar kelimeler ekler.
    Kullanıcıya gösterilmez.
    """
    soru_lower = str(soru).lower()
    genisletilmis = str(soru)

    if "koku" in soru_lower or "kokuyor" in soru_lower:
        genisletilmis += (
            " kötü koku su haznesi temizleme bakım filtre kireç tortu "
            "hazne temizliği su değiştirme anormal koku"
        )

    if "kapak" in soru_lower and (
        "açılmıyor" in soru_lower or "acilmiyor" in soru_lower
    ):
        genisletilmis += (
            " kapak kilidi kapak açılmıyor program bitti su var bekleme süresi"
        )

    if (
        "tepki vermiyor" in soru_lower
        or "elektrik almıyor" in soru_lower
        or "ekran açılmıyor" in soru_lower
        or "ekran acilmiyor" in soru_lower
    ):
        genisletilmis += (
            " elektrik güç kablosu fiş priz sigorta ekran açılmıyor cihaz çalışmıyor"
        )

    if "program başlatılamıyor" in soru_lower or "program seçimi" in soru_lower:
        genisletilmis += (
            " program iptal program seçme düğmesi başlatma ürün kendini korumaya aldı"
        )

    if "şarj" in soru_lower or "sarj" in soru_lower:
        genisletilmis += (
            " şarj olmuyor şarj istasyonu dock batarya pil adaptör bağlantı"
        )

    if "fırça" in soru_lower or "firca" in soru_lower:
        genisletilmis += (
            " fırça sıkıştı ana fırça yan fırça temizleme tekerlek hazne"
        )

    if "harita" in soru_lower or "sensör" in soru_lower or "sensor" in soru_lower:
        genisletilmis += (
            " harita sensör engel algılama lidar konumlandırma temizlik rotası"
        )

    if "yetkili servis" in soru_lower or "servise nasıl ulaşabilirim" in soru_lower:
        genisletilmis += (
            " yetkili servis çağrı merkezi müşteri hizmetleri telefon iletişim"
        )

    return genisletilmis


def baglami_duzenle(bulunan_parcalar, max_parca=4, max_karakter=1000):
    """
    RAG'den gelen parçaları temizler ve modele kısa bağlam olarak verir.
    """
    if not bulunan_parcalar:
        return ""

    parcalar = []

    for i, doc in enumerate(bulunan_parcalar[:max_parca], start=1):
        metin = getattr(doc, "page_content", "")
        metin = str(metin).strip()
        metin = re.sub(r"\s+", " ", metin)

        if metin:
            parcalar.append(f"[Parça {i}] {metin[:max_karakter]}")

    return "\n".join(parcalar)


def gecmisi_sadelestir(konusma_gecmisi):
    """
    Redis geçmişini sadece takip sorularını anlamak için sadeleştirir.
    Eski cevapların aynen tekrar edilmesini engeller.
    """
    if not konusma_gecmisi:
        return "Geçmiş yok."

    metin = str(konusma_gecmisi)

    kesilecekler = [
        "KULLANICI MESAJI:",
        "KULLANICI SORUSU:",
        "ASİSTAN YANITI:",
        "KILAVUZ BİLGİLERİ:",
        "GEÇMİŞ SOHBET:",
        "KESİN KURALLAR:",
        "ANALİZ:",
        "İÇ SES:"
    ]

    for ifade in kesilecekler:
        if ifade in metin:
            metin = metin.split(ifade)[0]

    metin = re.sub(r"\s+", " ", metin).strip()
    metin = metin[-700:]

    return metin if metin else "Geçmiş yok."


def secenekleri_parse_et(metin):
    """
    LLM'in ürettiği 1. 2. 3. formatındaki listeyi Redis'e kaydedilebilir hale getirir.
    """
    secenekler = []

    for satir in str(metin).splitlines():
        satir = satir.strip()

        eslesme = re.match(r"^([1-4])[\.\)]\s*(.+)$", satir)

        if eslesme:
            no = eslesme.group(1).strip()
            baslik = eslesme.group(2).strip()

            baslik = baslik.replace(":", "").strip()
            baslik = re.sub(r"\s+", " ", baslik)

            if baslik:
                secenekler.append(
                    {
                        "no": no,
                        "baslik": baslik,
                        "arama_sorusu": baslik
                    }
                )

    return secenekler


def netlestirme_olustur(soru, bulunan_parcalar):
    """
    Kullanıcı çok genel bir soru sorduğunda hazır liste kullanmaz.
    RAG'den gelen kılavuz parçalarına bakarak LLM'e dinamik seçenek listesi ürettirir.
    """
    baglam = baglami_duzenle(
        bulunan_parcalar,
        max_parca=5,
        max_karakter=1000
    )

    if not baglam:
        return GENEL_NETLESTIRME_CEVABI, []

    prompt = f"""
Sen ServiceBuddy adlı teknik destek asistanısın.

GÖREV:
Kullanıcının genel sorununu netleştirmek için sadece KILAVUZ BİLGİLERİ içindeki arıza belirtilerinden 3 veya 4 seçenek üret.

KATI KURALLAR:
- Hazır cihaz listesi kullanma.
- Seçenekleri sadece verilen kılavuz bağlamından çıkar.
- Çamaşır makinesi, robot süpürge, hava nemlendirici gibi cihazlara göre ezberden liste yapma.
- Kılavuzda hangi arıza belirtileri varsa onları sadeleştirerek seçenek yap.
- "Merhaba", "Not", "Kılavuzu oku", "Tablo Verisi" yazma.
- Açıklama yazma.
- Sadece numaralı liste ver.
- Her seçenek kısa ve anlaşılır olsun.
- En fazla 4 seçenek üret.

ÇIKTI FORMATI:
1. ...
2. ...
3. ...
4. ...

KULLANICI SORUSU:
{soru}

KILAVUZ BİLGİLERİ:
{baglam}

SEÇENEKLER:
""".strip()

    try:
        llm = OllamaLLM(
            model="llama3.1",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            temperature=0.0,
            top_p=0.75,
            num_ctx=4096,
            num_predict=250,
            repeat_penalty=1.2,
            timeout=60
        )

        cevap = llm.invoke(
            prompt,
            stop=[
                "KULLANICI SORUSU:",
                "KILAVUZ BİLGİLERİ:",
                "ANALİZ:",
                "CEVAP:",
                "ASİSTAN:"
            ]
        )

        cevap = str(cevap).strip()
        cevap = cevap.replace("Tablo Verisi", "")
        cevap = cevap.replace("Kılavuzu oku.", "")
        cevap = re.sub(r"\n{3,}", "\n\n", cevap).strip()

        secenekler = secenekleri_parse_et(cevap)

        if not secenekler:
            return GENEL_NETLESTIRME_CEVABI, []

        temiz_metin = "\n".join(
            [f"{s['no']}. {s['baslik']}" for s in secenekler]
        )

        temiz_metin = (
            "Sorunu netleştirmek için aşağıdakilerden hangisi olduğunu yazın:\n"
            + temiz_metin
        )

        return temiz_metin, secenekler

    except Exception as e:
        metin = (
            "Sistem Hatası: Netleştirme seçenekleri üretilemedi. "
            f"Hata detayı: {str(e)}"
        )
        return metin, []


def cevabi_temizle(cevap, soru=""):
    """
    Llama'nın gereksiz girişlerini, prompt yankısını ve tekrarlarını temizler.
    """
    if not cevap:
        return FALLBACK_CEVAP

    cevap = str(cevap).strip()

    if "ASİSTAN YANITI:" in cevap:
        cevap = cevap.split("ASİSTAN YANITI:")[-1].strip()

    if "CEVAP:" in cevap:
        cevap = cevap.split("CEVAP:")[-1].strip()

    kesilecekler = [
        "KULLANICI MESAJI:",
        "KULLANICI SORUSU:",
        "KILAVUZ BİLGİLERİ:",
        "GEÇMİŞ SOHBET:",
        "KESİN KURALLAR:",
        "GÖREV:",
        "ANALİZ:",
        "İÇ SES:",
        "Sen ServiceBuddy",
        "Sen ev aletleri"
    ]

    for ifade in kesilecekler:
        if ifade in cevap:
            cevap = cevap.split(ifade)[0].strip()

    yasakli_baslangiclar = [
        r"^Merhaba[!,. ]*",
        r"^Maalesef[!,. ]*",
        r"^Üzülüyorum[!,. ]*",
        r"^Tabii[!,. ]*",
        r"^Elbette[!,. ]*",
        r"^Anladım[!,. ]*"
    ]

    for pattern in yasakli_baslangiclar:
        cevap = re.sub(pattern, "", cevap, flags=re.IGNORECASE).strip()

    cevap = re.sub(
        r"Lütfen daha fazla bilgi verin.*?(söyleyin\.|çalışacağım\.)",
        "",
        cevap,
        flags=re.IGNORECASE | re.DOTALL
    )

    cevap = re.sub(
        r"\(Lütfen.*?seçiniz\.\)",
        "",
        cevap,
        flags=re.IGNORECASE | re.DOTALL
    )

    cevap = re.sub(
        r"Lütfen sorununuzu seçerek devam edelim!?",
        "",
        cevap,
        flags=re.IGNORECASE
    )

    yasakli_cumleler = [
        "Kılavuzu oku.",
        "kılavuzu oku.",
        "Kullanma kılavuzunu okuyun.",
        "kullanma kılavuzunu okuyun.",
        "Ürünü kurmadan ve çalıştırmadan önce kullanma kılavuzunu okuyun.",
        "Özellikle güvenlikle ilgili bilgilere uyun."
    ]

    for cumle in yasakli_cumleler:
        cevap = cevap.replace(cumle, "")

    cevap = re.sub(
        r"Tablo Verisi\s*[-–>]*\s*",
        "",
        cevap,
        flags=re.IGNORECASE
    )

    cevap = cevap.replace("Yada,", "Ya da")
    cevap = cevap.replace("Yada", "Ya da")
    cevap = cevap.replace("Nedenlerin analizi:", "Neden:")
    cevap = cevap.replace("Nedenlerin analizinin biri de", "Nedenlerden biri")
    cevap = cevap.replace("Arıza giderme yöntemi:", "Çözüm:")
    cevap = cevap.replace("Arıza belirtisi:", "Belirti:")
    cevap = cevap.replace("Kılavuz BİLGİLERİ bölümünde", "Kılavuzda")
    cevap = cevap.replace("KILAVUZ BİLGİLERİ bölümünde", "Kılavuzda")
    cevap = cevap.replace("Bu sorunuzun çözümü için", "")

    # Sadece parantez içindeki gereksiz fallback notunu temizle
    cevap = re.sub(
        r"\(\s*Kılavuzda bu işlemin nasıl yapılacağına dair detaylı bir adım bulunmamaktadır\.?\s*\)",
        "",
        cevap,
        flags=re.IGNORECASE
    )

    if FALLBACK_CEVAP in cevap:
        kalan = cevap.replace(FALLBACK_CEVAP, "").strip()
        if len(kalan) > 40:
            cevap = kalan

    cevap = re.sub(r"\n{3,}", "\n\n", cevap)
    cevap = re.sub(r"[ \t]+", " ", cevap)
    cevap = cevap.strip()

    bos_cevaplar = [
        "yardımcı olabilirim",
        "konusunda yardımcı olabilirim",
        "daha fazla bilgi verin",
        "sorunu çözmeye yardımcı",
        "ne tür bir sorun yaşadığınızı",
        "hangi hata kodunu"
    ]

    if any(ifade in cevap.lower() for ifade in bos_cevaplar):
        return FALLBACK_CEVAP

    if not cevap:
        return FALLBACK_CEVAP

    return cevap


def cevap_olustur(konusma_gecmisi, soru, bulunan_parcalar):
    """
    Ana cevap üretme fonksiyonu.
    Mevcut sistem generator beklediği için yield ile döner.
    """
    sade_gecmis = gecmisi_sadelestir(konusma_gecmisi)
    baglam = baglami_duzenle(bulunan_parcalar)

    if not baglam:
        yield FALLBACK_CEVAP
        return

    prompt = f"""
Sen ServiceBuddy adlı ev aletleri teknik destek asistanısın.

GÖREV:
Kullanıcının sorusuna sadece KILAVUZ BİLGİLERİ bölümündeki teknik bilgilere göre cevap ver.

KATI KURALLAR:
- "Merhaba", "Maalesef", "Üzülüyorum", "Tabii", "Elbette" ile başlama.
- Eski asistan cevaplarını tekrar etme.
- Kullanıcıya "kılavuzu oku" deme.
- İç ses, analiz, not, meta yorum veya parantezli açıklama yazma.
- Kullanıcıya "cevabınız şuna denk geliyor" gibi açıklama yapma.
- "Tablo Verisi" ifadesini yazma.
- Cevap kısa, net ve uygulanabilir olsun.
- Kılavuzdaki bilgi yeterliyse doğrudan çözümü ver.
- Kılavuzda çözüm adımı yoksa sadece şu cümleyi yaz:
{FALLBACK_CEVAP}

GEÇMİŞ SOHBET SADECE TAKİP SORULARINI ANLAMAK İÇİNDİR.
BU BÖLÜMDEKİ METİNLERİ CEVAP OLARAK KOPYALAMA:
{sade_gecmis}

KILAVUZ BİLGİLERİ:
{baglam}

KULLANICI SORUSU:
{soru}

CEVAP:
""".strip()

    try:
        llm = OllamaLLM(
            model="llama3.1",
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            temperature=0.0,
            top_p=0.75,
            num_ctx=4096,
            num_predict=350,
            repeat_penalty=1.25,
            timeout=60
        )

        ham_cevap = llm.invoke(
            prompt,
            stop=[
                "KULLANICI MESAJI:",
                "KULLANICI SORUSU:",
                "KILAVUZ BİLGİLERİ:",
                "GEÇMİŞ SOHBET:",
                "ASİSTAN YANITI:",
                "ANALİZ:",
                "İÇ SES:"
            ]
        )

        temiz_cevap = cevabi_temizle(ham_cevap, soru=soru)

        yield temiz_cevap

    except Exception as e:
        yield f"Sistem Hatası: Model ile bağlantı kurulamadı. Hata detayı: {str(e)}"