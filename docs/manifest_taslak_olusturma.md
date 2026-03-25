# Manifest Taslak Olusturma

Bu not, yeni bir algoritma cekirdegini sisteme baglarken AI'nin nasil daha mekanik calisacagini tarif eder.

## Hedef

Algoritma sahibi yalnizca su bilgileri verir:

- algoritma dosya yolu
- sinif adi
- `node_id`
- gorunen blok adi
- kategori
- giris ve cikis portlari
- config alanlari
- gerekiyorsa gorsellestirme baglari

AI bundan manifest taslagi uretir ve uygun modul dosyasina ekler.

## Kullanilacak Yardimcilar

- `ehplatform.catalog.ManifestDraft`
- `ehplatform.catalog.ManifestPortDraft`
- `ehplatform.catalog.ManifestConfigDraft`
- `ehplatform.catalog.render_manifest_module(...)`
- `ehplatform.catalog.build_ai_handoff_text(...)`
- `ehplatform.catalog.build_integration_checklist_text(...)`
- `ehplatform.catalog.suggest_manifest_module(...)`
- `ehplatform.catalog.manifest_draft_from_mapping(...)`
- `python -m ehplatform.catalog suggest-module ...`
- `python -m ehplatform.catalog render ...`
- `python -m ehplatform.catalog check ...`

## Beklenen Akis

1. Algoritma dosyasi `src/algorithms/**` altinda yazilir.
2. AI gerekli metadata ile bir `ManifestDraft` olusturur.
3. `suggest_manifest_module(...)` ile uygun manifest modulunu secer.
4. `render_manifest_module(...)` ile Python taslagini uretir.
5. Manifest dosyasina ekler.
6. Sistem yuklenirken manifest otomatik dogrulanir.

## CLI Akisi

Ornek spec:

```json
{
  "node_id": "my_detector",
  "display_name": "Yeni Tespit",
  "category": "Tespit",
  "description": "FFT uzerinde yeni aday hedefleri bulur.",
  "algorithm_import_path": "algorithms.detection.my_detector",
  "algorithm_class_name": "MyDetectorKernel",
  "input_ports": [
    {
      "name": "fft_in",
      "port_type": "FFT",
      "display_name": "FFT",
      "tooltip": "Bu blok FFT girdisi bekler."
    }
  ],
  "output_ports": [
    {
      "name": "detections_out",
      "port_type": "DETECTIONS",
      "display_name": "Tespitler",
      "tooltip": "Bulunan aday hedefler bu cikistan verilir."
    }
  ],
  "config_fields": [
    {
      "name": "threshold_db",
      "field_type": "float",
      "default": 8.0,
      "label": "Esik (dB)"
    }
  ],
  "visualization_bindings": [
    ["detections_out", "cfar_detections"]
  ]
}
```

Manifest modul yeri onermek icin:

```bash
python -m ehplatform.catalog suggest-module "Tespit" --node-id my_detector
```

Spec'ten manifest ve AI handoff cikarmak icin:

```bash
python -m ehplatform.catalog render spec.json --output src/ehplatform/catalog/manifests/detection.py --print-handoff
```

Spec'ten AI handoff ve entegrasyon checklist'i almak icin:

```bash
python -m ehplatform.catalog check spec.json --print-module
```

## Ornek Taslak

```python
from ehplatform.catalog import (
    ManifestConfigDraft,
    ManifestDraft,
    ManifestPortDraft,
    build_ai_handoff_text,
    build_integration_checklist_text,
    render_manifest_module,
)

draft = ManifestDraft(
    node_id="my_detector",
    display_name="Yeni Tespit",
    category="Tespit",
    description="FFT uzerinde yeni aday hedefleri bulur.",
    algorithm_import_path="algorithms.detection.my_detector",
    algorithm_class_name="MyDetectorKernel",
    input_ports=(
        ManifestPortDraft(
            name="fft_in",
            port_type="FFT",
            display_name="FFT",
            tooltip="Bu blok FFT girdisi bekler.",
        ),
    ),
    output_ports=(
        ManifestPortDraft(
            name="detections_out",
            port_type="DETECTIONS",
            display_name="Tespitler",
            tooltip="Bulunan aday hedefler bu cikistan verilir.",
        ),
    ),
    config_fields=(
        ManifestConfigDraft(
            name="threshold_db",
            field_type="float",
            default=8.0,
            label="Esik (dB)",
        ),
    ),
    visualization_bindings=(
        ("detections_out", "cfar_detections"),
    ),
)

python_source = render_manifest_module(draft)
handoff_text = build_ai_handoff_text(draft)
checklist_text = build_integration_checklist_text(draft)
```
