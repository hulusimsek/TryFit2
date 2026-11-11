"""Download manually verified public Trendyol gallery URLs for research QA."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("tshirt", "Tişört", "tops", "dilvin/3683-basic-t-shirt-siyah-p-87044322", "ty1855/prod/QC_ENRICHMENT/20260415/00/17dfe667-93b1-34a0-abed-5abcb1d04754/1_org_zoom.jpg"),
    ("patterned-blouse", "Desenli bluz", "tops", "mango/cicek-desenli-bluz-p-305224017", "ty706/product/media/images/20230129/20/269357371/487657681/1/1_org_zoom.jpg"),
    ("trench-coat", "Trençkot", "tops", "sateen/kusakli-uzun-trenckot-bej-p-866952143", "ty1827/prod/QC_ENRICHMENT/20260221/15/06b1ca09-5b3f-37e8-9949-eac29de89b05/1_org_zoom.jpg"),
    ("denim-jacket", "Kot ceket", "tops", "ekim-store/crop-denim-kot-ceket-p-286763026", "ty443/product/media/images/20220530/17/118366940/456275267/1/1_org_zoom.jpg"),
    ("long-dress", "Uzun elbise", "one-pieces", "grimelange/pani-kadin-maxi-boy-etek-kismi-dokuma-poplin-klos-ust-kismi-esnek-viskon-elastan-sik-siyah-elbise-p-879988342", "ty1638/prod/QC/20250219/12/b11ec61a-ef96-3e1b-8a2e-f1931a872fcd/1_org_zoom.jpg"),
    ("fitted-dress", "Dar elbise", "one-pieces", "dilvin/91097-vucuda-oturan-elbise-siyah-p-815123427", "ty1550/prod/QC/20240916/21/75e707eb-7958-3dd0-a242-1347c935e72c/1_org_zoom.jpg"),
    ("wide-trousers", "Geniş pantolon", "bottoms", "bikelife/kadin-siyah-likrali-palazzo-salas-genis-paca-pantolon-p-800599725", "ty1962/prod/QC_ENRICHMENT/20260923/10/f909ec70-42b2-3324-8b61-f97f8d72b845/1_org_zoom.jpg"),
    ("skirt", "Etek", "bottoms", "swist/siyah-full-pileli-kemerli-astar-sortlu-kadin-mini-etek-p-811422352", "ty1602/prod/QC/20241118/13/410bf519-8e77-3379-86aa-7d7f7b8f57c7/1_org_zoom.jpg"),
    ("hooded-sweatshirt", "Kapüşonlu sweatshirt", "tops", "koton/fermuarli-kapsonlu-baskili-sardonlu-sweatshirt-p-851793530", "ty1574/prod/QC/20240927/21/36f39c6d-ecb0-394a-9307-5b32fb49caa1/1_org_zoom.jpg"),
]


def main():
    from PIL import Image, ImageDraw, ImageOps
    directory = ROOT / "data/benchmark-10"
    directory.mkdir(exist_ok=True)
    manifest = {"schema_version": 1, "person": {"image": "data/first-outfit/avatar-baseline.png", "consent_confirmed": True,
                "source": "synthetic baseline, not a measured 175/65 body"}, "cases": []}
    original = json.loads((ROOT / "evaluation/manifests/first-outfit.selection.json").read_text(encoding="utf-8"))
    hoodie = original["items"][0]
    source = next(s for s in json.loads((ROOT / "data/first-outfit/gallery/sources.json").read_text()) if Path(s["image"]).name == "gallery-4.jpg")
    manifest["cases"].append({"id": "oversize-hoodie", "label": "Oversize hoodie", "category": "tops",
        "garment_photo_type": "model", "image": source["image"], "source_image_url": source["source_url"],
        "product_url": hoodie["product_url"], "source_notes": "One arm raised, hand inside pocket, hair occlusion; inspected earlier."})
    for identifier, label, category, product, image_url in CASES:
        path = directory / f"{identifier}.jpg"
        url = "https://cdn.dsmcdn.com/mnresize/620/920/" + image_url
        if identifier == "tshirt":
            url = "https://cdn.dsmcdn.com/" + image_url
        if not path.exists():
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = response.read()
            path.write_bytes(payload)
        with Image.open(path) as image:
            image.verify()
        manifest["cases"].append({"id": identifier, "label": label, "category": category,
            "garment_photo_type": "pending_visual_inspection", "image": path.relative_to(ROOT).as_posix(),
            "product_url": "https://www.trendyol.com/" + product, "source_image_url": url,
            "source_notes": "Pending source inspection", "image_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        print(identifier, path.stat().st_size, flush=True)
    (ROOT / "evaluation/manifests/trendyol-10.downloaded.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    board = Image.new("RGB", (1200, 1500), "white")
    draw = ImageDraw.Draw(board)
    for index, case in enumerate(manifest["cases"]):
        column, row = index % 4, index // 4
        with Image.open(ROOT / case["image"]) as original:
            preview = ImageOps.contain(original.convert("RGB"), (290, 465))
        board.paste(preview, (column*300+(300-preview.width)//2, row*500+25))
        draw.text((column*300+5, row*500+5), case["id"], fill="black")
    board.save(directory / "source-contact-sheet.jpg")


if __name__ == "__main__":
    main()
