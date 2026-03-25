# Plugins Dizini

Bu dizine harici EH algoritma plugin'lerini yerlestirin.

Her `.py` dosyasi veya `__init__.py` iceren plugin klasoru uygulama baslatilirken otomatik taranir.
Asagidaki uc yol desteklenir:

1. `MANIFESTS` sabiti ile manifest tabanli kayit
2. `get_manifests()` fonksiyonu ile dinamik manifest uretimi
3. `register_plugin()` fonksiyonu ile elle kayit

Kesif sonunda sistem basarili ve hatali pluginleri ayri ayri raporlar. Bu sayede bozuk bir plugin tum uygulama baslangicini bozmaz.

## Hizli Yonetim Akisi

Algoritma sahibi ve AI entegrasyon akisi icin su dokumanlara bak:

- `docs/algoritma_sahibi_hizli_baslangic.md`
- `docs/algoritma_entegrasyon_rehberi.md`
- `docs/manifest_taslak_olusturma.md`

## Onerilen Plugin Ornegi

```python
from ehplatform.catalog.types import NodeManifest, PortManifest
from ehplatform.contracts import PortType

MANIFESTS = (
    NodeManifest(
        node_id="my_plugin",
        display_name="Ornek Plugin",
        category="Tespit",
        description="Harici tespit algoritmasi",
        algorithm_import_path="algorithms.detection.my_plugin",
        algorithm_class_name="MyPluginKernel",
        input_ports=(
            PortManifest(
                name="fft_in",
                port_type=PortType.FFT,
                display_name="FFT",
                tooltip="Bu blok FFT girdisi bekler.",
            ),
        ),
        output_ports=(
            PortManifest(
                name="det_out",
                port_type=PortType.DETECTIONS,
                display_name="Tespitler",
                tooltip="Bulunan aday hedefler bu cikistan verilir.",
            ),
        ),
    ),
)
```
