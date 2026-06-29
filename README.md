# ServiceBuddy: LLM Tabanlı Kullanım Kılavuzu Asistanı

ServiceBuddy, ev aletleri kullanım kılavuzları üzerinden teknik destek sağlayan LLM tabanlı bir asistandır. Proje; RAG mimarisi, yerel LLM, Redis tabanlı oturum hafızası, OCR destekli görsel işleme, FastAPI backend servisi, Streamlit kullanıcı arayüzü ve Docker Compose tabanlı servis mimarisi kullanılarak geliştirilmiştir.

## Projenin Amacı

Kullanıcıların çamaşır makinesi, hava nemlendirici ve robot süpürge gibi cihazlara ilişkin teknik sorunlarını doğal dilde sormalarını sağlamak ve kullanım kılavuzlarından alınan bilgilerle doğru, kısa ve uygulanabilir cevaplar üretmektir.

Kullanıcılar sisteme metin tabanlı soru sorabilir veya cihaz ekranı/kılavuz görseli yükleyebilir. Görsel yükleme durumunda OCR ile metin çıkarılır ve çıkarılan metin RAG sürecine aktarılır.

## Temel Özellikler

* Kullanım kılavuzları üzerinden RAG tabanlı cevap üretimi
* Ollama Llama 3.1 ile yerel LLM kullanımı
* ChromaDB ile vektör tabanlı doküman arama
* Redis ile oturum hafızası ve dinamik seçenek takibi
* FastAPI ile backend API servisi
* Streamlit ile kullanıcı dostu web arayüzü
* EasyOCR ve OpenCV ile görselden metin çıkarma
* Docker Compose ile çok servisli çalışma yapısı
* GitHub Actions ile CI otomasyonu

## Sistem Mimarisi

```text
Kullanıcı
↓
Streamlit Web Arayüzü
↓
FastAPI Backend
↓
Router
↓
ChromaDB / RAG
↓
Ollama Llama 3.1
↓
Redis Hafıza
↓
Yanıt
```

Görsel yükleme durumunda akış şu şekilde çalışır:

```text
Görsel
↓
EasyOCR + OpenCV
↓
OCR Metni
↓
Router
↓
RAG
↓
LLM Yanıtı
```

## Kullanılan Teknolojiler

* Python
* FastAPI
* Streamlit
* Redis
* ChromaDB
* LangChain
* Ollama
* Llama 3.1
* EasyOCR
* OpenCV
* Docker
* Docker Compose
* GitHub Actions

## Proje Servisleri

Docker Compose ile üç ana servis çalıştırılır:

```text
redis       → Oturum hafızası
api         → FastAPI backend servisi
streamlit   → Kullanıcı arayüzü
```

## Yerel Çalıştırma

Önce Ollama üzerinde Llama 3.1 modelinin kurulu olduğundan emin olun:

```bash
ollama list
```

Docker Compose ile uygulamayı başlatmak için:

```bash
docker compose -p servicebuddy up --build
```

Streamlit arayüzü:

```text
http://localhost:8501
```

FastAPI Swagger ekranı:

```text
http://localhost:8000/docs
```

## GitHub Actions CI

Projede GitHub Actions ile CI süreci yapılandırılmıştır. Her push işleminde aşağıdaki kontroller otomatik olarak yapılır:

* Python dosyalarının sözdizimi kontrolü
* Gerekli proje dosyalarının varlık kontrolü
* Docker Compose yapılandırma kontrolü

CI workflow dosyası:

```text
.github/workflows/ci.yml
```

## Notlar

Embedding modeli, ChromaDB veritabanı ve büyük model dosyaları GitHub reposuna dahil edilmemiştir. Bu dosyalar yerel çalışma veya sunucu ortamında ayrıca bulundurulmalıdır.

Gerçek yayın ortamı için proje AWS EC2, Azure VM, DigitalOcean Droplet veya benzeri bir Linux sanal sunucu üzerinde Docker Compose ile çalıştırılabilir.
