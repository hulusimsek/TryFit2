"""Complete frozen ten-case control: target masking + the same SAM source masks."""
import json
from pathlib import Path
from experiment import run_experiment,evaluate,write_json,sha256
from masked_outfit import MaskedOutfitPipeline


def run():
    root=Path(__file__).resolve().parents[2]
    manifest=root/'evaluation/manifests/trendyol-10.actual.json'
    cases=json.loads(manifest.read_text(encoding='utf-8'))['cases']
    provenance={}
    def factory(weights):
        if Path(weights).resolve()!=root/'ai-worker/models':raise ValueError('Unexpected weights directory')
        pipeline=MaskedOutfitPipeline(root,cases,allow_masked_target=True)
        provenance.update(pipeline.provenance)
        return pipeline
    result=run_experiment(root,manifest,root/'ai-worker/models',segmentation_free=False,pipeline_factory=factory)
    baseline=root/'runs/20261110T095148Z-cf9135a6'
    write_json(result/'target-mask-provenance.json',{
        'baseline':baseline.relative_to(root).as_posix(),'baseline_run_sha256':sha256(baseline/'run.json'),
        'controlled_change':'Only target segmentation_free True -> False, for every category',
        'unchanged':['same ten cases and categories','same person','same source photos and SAM masks','original source/target poses','seed42','30 steps','guidance1.5'],
        'source_extractions':provenance,'output_compositing':False,
        'limits':['Manual source-instance annotations','Single synthetic person','No measured body or garment fit','No best-case mixing with old results']})
    evaluate(result)
    (root/'runs/latest-target-masked-benchmark.txt').write_text(str(result),encoding='utf-8')
    return result


if __name__=='__main__':run()
