import re
import cv2
import easyocr
import numpy as np


reader = None


def reader_getir():
    global reader

    if reader is None:
        print("[OCR] EasyOCR modeli ilk kez yükleniyor...")
        reader = easyocr.Reader(["tr", "en"], gpu=False)

    return reader


def resmi_guvenli_oku(image_path):
    """
    Windows'ta Türkçe karakterli dosya yollarını güvenli okumak için.
    """
    image_path = str(image_path).strip().strip('"').strip("'")

    file_bytes = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(f"Görüntü okunamadı: {image_path}")

    return img


def ocr_icin_varyasyonlar_uret(image_path):
    """
    Küçük ekran görüntülerinde OCR başarısını artırmak için
    birkaç farklı ön işleme varyasyonu üretir.
    """
    img = resmi_guvenli_oku(image_path)

    # Görseli büyüt
    scale = 4
    img_big = cv2.resize(
        img,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    gray = cv2.cvtColor(img_big, cv2.COLOR_BGR2GRAY)

    # Kontrast artır
    gray_eq = cv2.equalizeHist(gray)

    # Hafif blur
    blur = cv2.GaussianBlur(gray_eq, (3, 3), 0)

    # Otsu threshold
    otsu = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    # Ters görüntü
    inverted = cv2.bitwise_not(otsu)

    return [img_big, gray, gray_eq, otsu, adaptive, inverted]


def ocr_skorla(results):
    """
    EasyOCR çıktısını güven skoruna göre değerlendirir.
    """
    if not results:
        return "", 0

    metinler = []
    skorlar = []

    for item in results:
        try:
            text = item[1]
            conf = item[2]
            if text:
                metinler.append(text)
                skorlar.append(conf)
        except Exception:
            continue

    metin = " ".join(metinler)
    metin = re.sub(r"\s+", " ", metin).strip()

    if not skorlar:
        return metin, 0

    ort_skor = sum(skorlar) / len(skorlar)

    # Daha uzun ve anlamlı metne küçük bonus
    if len(metin) > 20:
        ort_skor += 0.10

    return metin, ort_skor


def resimden_metin_oku(image_path):
    """
    Görüntüden OCR ile metin çıkarır.
    Birden fazla ön işleme dener, en iyi sonucu seçer.
    """
    varyasyonlar = ocr_icin_varyasyonlar_uret(image_path)

    en_iyi_metin = ""
    en_iyi_skor = -1

    for img in varyasyonlar:
        try:
            results = reader_getir().readtext(
                img,
                detail=1,
                paragraph=False,
                decoder="beamsearch",
                width_ths=0.9,
                text_threshold=0.5,
                low_text=0.3
            )

            metin, skor = ocr_skorla(results)

            if skor > en_iyi_skor and metin:
                en_iyi_skor = skor
                en_iyi_metin = metin

        except Exception:
            continue

    en_iyi_metin = re.sub(r"\s+", " ", en_iyi_metin).strip()

    return en_iyi_metin


def sadece_hata_kodu_mu(metin):
    """
    OCR çıktısı sadece E1, F3, H05 gibi kısa bir kodsa True döner.
    """
    metin = str(metin).strip().upper()
    return bool(re.fullmatch(r"[A-Z]{1,3}\s?-?\s?\d{1,3}", metin))


def cihaz_on_eki_ekle(metin, cihaz_tipi=None):
    """
    OCR metnine cihaz bağlamı ekler.
    Böylece router doğru koleksiyonu seçebilir.
    """
    cihaz_tipi = str(cihaz_tipi or "").lower().strip()

    if cihaz_tipi in ["camasir", "çamaşır", "camasir_makinesi", "çamaşır_makinesi"]:
        return f"Çamaşır makinesi: {metin}"

    if cihaz_tipi in ["hava", "nemlendirici", "hava_nemlendirici"]:
        return f"Hava nemlendirici: {metin}"

    if cihaz_tipi in ["robot", "supurge", "süpürge", "robot_supurge", "robot_süpürge"]:
        return f"Robot süpürge: {metin}"

    return metin


def goruntu_sorgusunu_hazirla(image_path, cihaz_tipi=None):
    """
    Görüntüden metin çıkarır ve RAG'e gönderilecek sorguyu hazırlar.
    """
    metin = resimden_metin_oku(image_path)

    if not metin:
        return {
            "ocr_text": "",
            "query": "Görüntüden anlamlı metin okunamadı."
        }

    metin_baglamli = cihaz_on_eki_ekle(metin, cihaz_tipi)

    if sadece_hata_kodu_mu(metin):
        return {
            "ocr_text": metin,
            "query": (
                f"{metin_baglamli} ifadesi görüntüden okundu. "
                "Bu hata kodu veya uyarı kılavuzda geçiyorsa anlamını ve çözümünü açıkla. "
                "Kılavuzda geçmiyorsa bilgi bulunamadığını söyle."
            )
        }

    return {
        "ocr_text": metin,
        "query": (
            f"Görüntüden okunan metin: {metin_baglamli}. "
            "Bu metne göre kılavuzdaki ilgili arıza, bakım veya kullanım çözümünü açıkla."
        )
    }