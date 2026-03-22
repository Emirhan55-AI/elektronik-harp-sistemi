# Plugins Dizini

Bu dizine harici EH algoritma plugin'lerini yerleştirin.

Her `.py` dosyası uygulama başlatılırken otomatik taranır
ve `@NodeRegistry.register` decorator'ı ile işaretlenmiş
adaptörler sisteme kaydedilir.

## Örnek Plugin

```python
from ehcore.adapters._base import BaseAdapter
from ehcore.contracts import NodeDescriptor, PortDef, PortType
from ehcore.registry import NodeRegistry

@NodeRegistry.register
class MyPlugin(BaseAdapter):
    descriptor = NodeDescriptor(
        node_id="my_plugin",
        display_name="Örnek Plugin",
        category="Tespit",
        description="Harici tespit algoritması",
        input_ports=(
            PortDef(name="fft_in", port_type=PortType.FFT, display_name="FFT Giriş"),
        ),
        output_ports=(
            PortDef(name="det_out", port_type=PortType.DETECTIONS, display_name="Tespit Çıkış"),
        ),
    )
    
    def configure(self, config):
        self._config = config
        
    def process(self, inputs):
        # Algoritma kodu buraya
        return {}
```
