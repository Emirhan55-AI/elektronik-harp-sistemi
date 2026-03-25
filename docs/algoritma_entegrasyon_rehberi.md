# Algoritma Entegrasyon Rehberi

Bu dokumanin amaci, algoritma gelistirme isi ile sistem entegrasyonu isini kesin olarak ayirmaktir.

## Sahiplik Siniri

Algoritma sahibi yalnizca su klasore dokunur:

- `src/algorithms/**`

Sistem entegrasyonu su alanlarda kalir:

- `src/ehplatform/catalog/**`
- `src/ehplatform/runtime/**`
- `src/app/**`

Manifest dosyalari moduler olarak su klasorde tutulur:

- `src/ehplatform/catalog/manifests/**`

## Yeni Algoritma Yazari Icin Kurallar

1. Yeni dosyayi `src/algorithms/**` altinda olustur.
2. Algoritma sinifi `AlgorithmKernel` sozlesmesini uygulasin.
3. Dosya UI, registry, persistence veya plotting import etmesin.
4. Girdi ve ciktilar `AlgorithmPacket` ile temsil edilsin.

Zorunlu sinif arayuzu:

```python
class MyKernel(AlgorithmKernel):
    def configure(self, params: dict[str, object]) -> None:
        ...

    def start(self) -> None:
        ...

    def process(
        self,
        inputs: dict[str, AlgorithmPacket],
        context: AlgorithmContext,
    ) -> dict[str, AlgorithmPacket]:
        ...

    def stop(self) -> None:
        ...

    def reset(self) -> None:
        ...
```

## AI'ye Verilecek En Kucuk Entegrasyon Paketi

Yeni algoritma yazildiktan sonra AI'ye su bilgileri vermek yeterlidir:

- algoritma dosya yolu
- sinif adi
- `node_id`
- gorunen blok adi
- kategori
- giris portlari
- cikis portlari
- config schema
- varsa grafik baglari

AI'nin bundan sonra dokunacagi yerler:

- `src/ehplatform/catalog/manifests/**`
- gerekiyorsa `src/app/**` icindeki gorunum baglari

Baslangic noktasi olarak su yardimcilar kullanilir:

- `ehplatform.catalog.render_manifest_module(...)`
- `ehplatform.catalog.build_ai_handoff_text(...)`
- `ehplatform.catalog.build_integration_checklist_text(...)`
- `ehplatform.catalog.suggest_manifest_module(...)`

Kesif mantigi:

- `ehplatform.catalog.discovery.discover_manifests()` paket tarar
- `_` ile baslayan dosyalar import edilmez
- her modul `MANIFESTS` veya `get_manifests()` donmelidir
- manifestler yukleme sirasinda otomatik dogrulanir

## Manifest Taslagi Uretme

Sistem tarafinda su yardimcilar vardir:

- `ehplatform.catalog.ManifestDraft`
- `ehplatform.catalog.ManifestPortDraft`
- `ehplatform.catalog.ManifestConfigDraft`
- `ehplatform.catalog.render_manifest_module(...)`
- `ehplatform.catalog.suggest_manifest_module(...)`

Amac:

1. Algoritma sahibi sadece algoritma detaylarini verir.
2. AI bu detaylardan manifest taslagi uretir.
3. Sistem manifesti yuklerken yapisal hatalari otomatik yakalar.

Manifest dogrulama sunlari kontrol eder:

- `node_id`, kategori ve gorunen ad bos mu
- algoritma modulu ve sinifi gercekten var mi
- port adlari cakisiyor mu
- `visualization_bindings` gercek cikis portuna bagli mi
- `config_schema` bozuk mu
- `compat_aliases` cakisiyor mu

## Yeni Blok Entegrasyonu Icin AI Checklist

1. Algoritma dosyasi `src/algorithms/**` altinda mi
2. `AlgorithmKernel` sozlesmesi uygulanmis mi
3. Manifest eklendi mi
4. `node_id` benzersiz mi
5. Port tipleri dogru mu
6. Zorunlu config alanlari tanimli mi
7. Tooltip ve gorunen isimler acik mi
8. Gereksiz debug portlari gizli mi
9. Gorsellestirme baglari tanimli mi
10. Eski proje dosyalariyla cakisacak bir degisiklik var mi

## AI'ye Gonderilecek Ornek Gorev

```text
src/algorithms/detection/my_detector.py altina algoritmayi ekledim.
Sinif adi: MyDetectorKernel
Node id: my_detector
Gorunen ad: Yeni Tespit
Kategori: Tespit
Giris: fft_in / FFT / zorunlu
Cikis: detections_out / DETECTIONS
Config:
- threshold_db (float, default 8.0)
- min_width (int, default 3)
Spectrum'ta ham tespitler gorunsun.
Manifesti ve UI entegrasyonunu bagla, algoritma dosyasina dokunma.
```
