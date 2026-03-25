# Algoritma Sahibi Hizli Baslangic

Bu notun amaci, algoritma gelistiren kisi ile sistem entegrasyonunu ayirmayi pratik hale getirmektir.

## Senin Dokunacagin Tek Yer

Algoritma sahibi olarak varsayilan calisma alanin:

- `src/algorithms/**`

Bu alanin disina cikmadan yeni algoritma yazabilmelisin.

Dokunmaman gereken alanlar:

- `src/ehplatform/catalog/**`
- `src/ehplatform/runtime/**`
- `src/app/**`

Bu alanlar sistem, UI, manifest ve entegrasyon katmanidir. Gerektiginde AI buralari baglar.

## Yeni Algoritma Eklerken En Kisa Akis

1. `src/algorithms/**` altinda yeni dosyani olustur.
2. `AlgorithmKernel` sozlesmesine uyan sinifi yaz.
3. AI'ye su bilgileri ver:
   - algoritma dosya yolu
   - sinif adi
   - `node_id`
   - blok gorunen adi
   - kategori
   - giris ve cikis portlari
   - config alanlari
   - varsa spektrum, waterfall veya tespit baglari
4. AI manifesti eklesin.
5. Sistem node'u palette ve runtime icinde gorunur hale getirir.

JSON spec uzerinden hizli kontrol almak icin:

```bash
python -m ehplatform.catalog check spec.json --print-module
```

Bu komut sana sunlari verir:

- onerilen manifest modul yolu
- AI'ye verilecek handoff metni
- entegrasyon checklist'i

## AI'ye Gonderilecek Minimal Paket

```text
Algoritma dosyasi: src/algorithms/detection/my_detector.py
Sinif adi: MyDetectorKernel
Node id: my_detector
Gorunen ad: Yeni Tespit
Kategori: Tespit
Girisler:
- fft_in / FFT / zorunlu
Cikislar:
- detections_out / DETECTIONS
Config:
- threshold_db (float, default 8.0)
- min_width (int, default 3)
Gorsellestirme:
- detections_out -> cfar_detections
Manifesti ve UI entegrasyonunu bagla. Algoritma dosyasina dokunma.
```

## Algoritma Dosyasi Icin Kurallar

- UI import etme.
- `NodeRegistry`, `QWidget`, `QDockWidget`, plotting ya da persistence import etme.
- Girdi ve ciktilari `AlgorithmPacket` ile ele al.
- Runtime baglami sadece `AlgorithmContext` uzerinden kullan.

## Yardimci Dokumanlar

- [Algoritma Entegrasyon Rehberi](/C:/Users/emirhan55/OneDrive/Desktop/Elektronik%20Harp/Sistem/docs/algoritma_entegrasyon_rehberi.md)
- [Manifest Taslak Olusturma](/C:/Users/emirhan55/OneDrive/Desktop/Elektronik%20Harp/Sistem/docs/manifest_taslak_olusturma.md)

## Sistem Tarafinin Sorumlulugu

AI veya sistem entegrasyon katmani su isleri yapar:

- manifest kaydi
- port tanimlari
- tooltip ve gorunen adlar
- plotting baglari
- issue, inspector ve runtime entegrasyonu
- preset ve recipe uyumlulugu

Hedef su:

- sen sadece algoritmayi yazarsin
- sistem geri kalan entegrasyonu tasir
