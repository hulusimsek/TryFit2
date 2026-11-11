"""Build a standalone Colab notebook from the experiment runner and manifest."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "7c0f10af3f91ad4048fe9729c470a13ef905d25a"


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def build():
    runner = (ROOT / "ai-worker/app/experiment.py").read_text(encoding="utf-8")
    manifest = (ROOT / "evaluation/manifests/trendyol-10.template.json").read_text(encoding="utf-8")
    cells = [cell("markdown", """# TryFit Next — gerçek mankenli ürün testi
Bu notebook kendi Colab GPU oturumunuzda FASHN VTON v1.5 çalıştırır. Ücretli API veya HF Space çağrısı yapmaz.

**Araştırma/değerlendirme kullanımı:** VTON Apache 2.0; resmî human parser NVIDIA SegFormer araştırma/değerlendirme lisansını devralır. Ticari dağıtım onayı değildir.

1. Colab: Runtime → Change runtime type → ücretsiz GPU. GPU tahsisi garanti değildir.
2. Kurulum hücrelerini çalıştırın. Yeniden başlatma istenirse oturumu yeniden başlatıp ilk hücreden devam edin.
3. Yerel manifesti gerçek ürün URL’leriyle doldurun; izinli `person.jpg` ve on ürün fotoğrafını hazırlayın.
4. Yükleme hücresinde fotoğrafları ve doldurduğunuz `manifest.json` dosyasını seçin.
5. Önce tek ürün, sonra on ürün deneyini çalıştırın. Sonuçları hemen indirin.

T4 BF16 desteklemez; resmî pipeline FP32 seçebilir. 8 GB iddiası T4 garantisi değildir. Bellek hatasında ücretsiz kaynakta çalışmadı olarak kaydedin.
"""), cell("code", """from pathlib import Path
import sys, subprocess, json, os
ROOT = Path('/content/tryfit-next')
ROOT.mkdir(parents=True, exist_ok=True)
def checked(*args):
    subprocess.run(list(args), check=True)
checked('nvidia-smi')
import torch
print('Python:', sys.version, 'Torch:', torch.__version__, 'CUDA:', torch.version.cuda)
if not torch.cuda.is_available():
    raise RuntimeError('GPU tahsis edilmedi. Runtime ayarlarını kontrol edin.')
print('GPU:', torch.cuda.get_device_name(0), 'BF16:', torch.cuda.is_bf16_supported())
print('VRAM GiB:', torch.cuda.get_device_properties(0).total_memory / 2**30)
"""), cell("code", f"""UPSTREAM_COMMIT = {UPSTREAM!r}
vendor = ROOT / 'vendor/fashn-vton-1.5'
vendor.parent.mkdir(exist_ok=True)
if not vendor.exists():
    checked('git', 'clone', 'https://github.com/fashn-AI/fashn-vton-1.5.git', str(vendor))
checked('git', '-C', str(vendor), 'checkout', '--detach', UPSTREAM_COMMIT)
checked(sys.executable, '-m', 'pip', 'install', '-e', str(vendor))
checked(sys.executable, '-m', 'pip', 'check')
"""), cell("code", f"""# Runner bu notebook'a gömülüdür; başka bir TryFit deposu indirilmez.
(ROOT / 'experiment.py').write_text({runner!r}, encoding='utf-8')
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import importlib
import experiment
importlib.reload(experiment)
environment = experiment.preflight()
print(json.dumps(environment, indent=2))
if 'CUDAExecutionProvider' not in environment['onnx_providers']:
    raise RuntimeError('ONNX CUDA provider eksik. CUDA/cuDNN uyumunu çözmeden ilerlemeyin.')
"""), cell("code", """# Ana model ve DWPose indirmelerini çözümlenen HF revision kimliklerine sabitle.
from huggingface_hub import HfApi, hf_hub_download, snapshot_download
api = HfApi()
weights = ROOT / 'ai-worker/models'
weights.mkdir(parents=True, exist_ok=True)
provenance = {'upstream_commit': UPSTREAM_COMMIT, 'repositories': {}}
for repo, filenames, destination in [
    ('fashn-ai/fashn-vton-1.5', ['model.safetensors'], weights),
    ('fashn-ai/DWPose', ['yolox_l.onnx', 'dw-ll_ucoco_384.onnx'], weights / 'dwpose'),
]:
    revision = api.model_info(repo).sha
    provenance['repositories'][repo] = revision
    for filename in filenames:
        hf_hub_download(repo, filename=filename, revision=revision, local_dir=destination)
# Parser paketi main cache'ini kullandığı için aynı snapshot önceden indirilir ve hash'lenir.
parser_snapshot = Path(snapshot_download('fashn-ai/fashn-human-parser', revision='main'))
provenance['repositories']['fashn-ai/fashn-human-parser'] = parser_snapshot.name
provenance['parser_files_sha256'] = {
    str(p.relative_to(parser_snapshot)): experiment.sha256(p)
    for p in sorted(parser_snapshot.rglob('*')) if p.is_file()
}
experiment.write_json(ROOT / 'model-provenance.json', provenance)
print(json.dumps(provenance, indent=2))
"""), cell("markdown", """## Girdileri yükleyin
Manifestte boş URL bırakmayın. Kaynak fotoğraf URL’si ile ürün sayfası URL’si ayrı alanlardır.
`person.consent_confirmed` yalnızca fotoğrafı kullanma izniniz varsa `true` olmalı.
Manifestte görseller `data/person.jpg`, `data/oversize-hoodie.jpg` vb. yolları kullanır.
Dosyaları bu adlarla hazırlayın. Farklı ad kullanırsanız manifestte değiştirin.
Ürün görsellerini otomatik kazımıyoruz; seçtiğiniz gerçek mankenli fotoğrafları yükleyin.
"""), cell("code", f"""from google.colab import files
data_dir = ROOT / 'data'
data_dir.mkdir(exist_ok=True)
manifest_path = ROOT / 'manifest.json'
if not manifest_path.exists():
    manifest_path.write_text({manifest!r}, encoding='utf-8')
uploaded = files.upload()
for name, content in uploaded.items():
    basename = Path(name).name
    destination = manifest_path if basename == 'manifest.json' else data_dir / basename
    destination.write_bytes(content)
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
print(json.dumps(manifest, ensure_ascii=False, indent=2))
# Eksik girdi varsa anlaşılır hata verir, inference başlamaz.
experiment.validate_manifest(manifest, ROOT)
"""), cell("markdown", """## Önce bir ürünle doğrulayın
Bu deneme kalite eşiğini geçiremez; on ürünlük matris ayrıca çalıştırılmalıdır.
Hücre hata verse bile en alttaki arşiv indirme hücresini çalıştırarak logları alabilirsiniz.
"""), cell("code", """smoke_run = experiment.run_experiment(
    ROOT, manifest_path, weights, selected_ids=['tshirt'], seed=42, steps=30)
smoke_record = json.loads((smoke_run / 'run.json').read_text())
if smoke_record['status'] != 'completed':
    raise RuntimeError('İlk üretim başarısız. Logları inceleyin; toplu denemeye geçmeyin.')
from IPython.display import display, Image as DisplayImage
display(DisplayImage(filename=str(smoke_run / 'tshirt-comparison.jpg')))
"""), cell("markdown", """## On ürünlük ana deney
İlk çıktıyı inceleyip ortamın çalıştığını gördükten sonra bu hücreyi çalıştırın.
OOM hatası deneyi durdurur; kalan ürünler `not_run` olur. Başarısız sonuç yerine başka görsel konmaz.
"""), cell("code", """if 'smoke_record' not in globals() or smoke_record['status'] != 'completed':
    raise RuntimeError('Önce tek ürün üretimini tamamlayın.')
batch_run = experiment.run_experiment(ROOT, manifest_path, weights, seed=42, steps=30)
experiment.evaluate(batch_run)
for comparison in sorted(batch_run.glob('*-comparison.jpg')):
    display(DisplayImage(filename=str(comparison)))
files.download(str(batch_run / 'review.csv'))
"""), cell("markdown", """## İnsan değerlendirmesi
`review.csv` dosyasında her metriği 0–4 puanlayın: 0 yanlış/kullanılamaz, 1 ağır bozulma,
2 belirgin hata, 3 kabul edilebilir küçük hata, 4 güçlü koruma.
`source_pose`: 4 kaynak pozundan belirgin hata yok, 0 ağır kaynak poz/kaynak kişi aktarımı.
`reviewer` adını, `critical_failure` ve `untargeted_changes` alanlarına `yes` veya `no` ve hata notlarını girin.
Seçilmemiş kıyafetin değişmesi veya kaynak ayakkabı/aksesuarının taşınması `untargeted_changes=yes` olur ve örnek başarısız sayılır.
Yanlış kıyafet, belirgin yüz değişimi veya anatomi bozulması kritik hatadır.
Boş değerlendirme başarı değildir. Her metriği en az 3 olan ve kritik hatası olmayan örnek geçer.
10 örneğin en az 8'i geçerse önerilen araştırma eşiği geçilir; bu genel kullanıcı/beden garantisi değildir.
"""), cell("code", """review_upload = files.upload()
if set(review_upload) != {'review.csv'}:
    raise ValueError('Yalnızca doldurduğunuz review.csv dosyasını seçin.')
(batch_run / 'review.csv').write_bytes(review_upload['review.csv'])
print(json.dumps(experiment.evaluate(batch_run), ensure_ascii=False, indent=2))
"""), cell("code", """# Hata oluşmuş olsa da tüm deney kayıtlarını indirir. Fotoğrafları özel tutun.
import shutil
if not (ROOT / 'runs').exists():
    raise RuntimeError('Henüz deney kaydı yok.')
archive = shutil.make_archive('/content/tryfit-next-results', 'zip', ROOT, 'runs')
files.download(archive)
""")]
    notebook = {"nbformat": 4, "nbformat_minor": 5, "metadata": {
        "colab": {"name": "TryFitNext_FASHN_Quality_Test.ipynb"},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"}, "accelerator": "GPU"}, "cells": cells}
    for index, item in enumerate(cells):
        item["id"] = f"tryfit-{index:02d}"
    destination = ROOT / 'notebooks/TryFitNext_FASHN_Quality_Test.ipynb'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    build()
