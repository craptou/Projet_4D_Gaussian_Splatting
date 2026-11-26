"""Validate contextual function references, mask evidence, slides and the separate oral-script PDF."""
import json
from pathlib import Path
import hashlib
from zipfile import ZipFile
from PIL import Image
import pypdfium2 as pdfium
from pptx import Presentation

ROOT=Path(__file__).resolve().parents[1]
NAME='progress-2026-11-26.en'


def validate():
    from presentation_functions import resolve
    import re
    data=json.loads((ROOT/'presentations'/f'{NAME}.json').read_text(encoding='utf-8'))
    count=len(data['slides'])
    assert data['main_slides']==count==12 and data['code_appendix_slides']==0
    expected_ids=['goal','step-images','step-cameras','step-projection','step-gaussians','step-learning','step-time','step-evaluation','acquisition','kitchen-result','skate-result','masks-tested']
    assert [s['id'] for s in data['slides']]==expected_ids
    assert 540<=sum(s['seconds'] for s in data['slides'])<=660
    references=[resolve(r) for s in data['slides'] for r in s.get('functions',[])]
    assert len(references)==22 and all('code' not in s for s in data['slides'])
    assert '11.79' in data['slides'][-1]['notes'] and '25.18' in data['slides'][-1]['notes']
    prs=Presentation(ROOT/'presentations'/f'{NAME}.pptx');doc=pdfium.PdfDocument(ROOT/'presentations'/f'{NAME}.pdf')
    script=pdfium.PdfDocument(ROOT/'presentations/progress-2026-11-26.script.en.pdf')
    assert len(prs.slides)==len(doc)==len(script)==count
    with ZipFile(ROOT/'presentations'/f'{NAME}.pptx') as package:
        media=[name for name in package.namelist() if name.startswith('ppt/media/') and name.endswith('.mp4')]
        expected=hashlib.sha256((ROOT/'docs/assets/4d-demo-time.mp4').read_bytes()).digest()
        assert any(hashlib.sha256(package.read(name)).digest()==expected for name in media)
    out=ROOT/'outputs/presentation-review-2026-11-26';out.mkdir(parents=True,exist_ok=True)
    montage=Image.new('RGB',(3*480,4*270),'#dce4e8')
    for i,(slide,page,spec,spoken) in enumerate(zip(prs.slides,doc,data['slides'],script)):
        assert spec['notes'] in slide.notes_slide.notes_text_frame.text
        text=page.get_textpage().get_text_range()
        assert len(text)>100 and spec['title'][:20] in text
        assert not re.search(r'\bpp\.|PDF pp|code appendix',text,re.I)
        spoken_text=' '.join(spoken.get_textpage().get_text_range().split())
        assert ' '.join(spec['notes'].split()) in spoken_text,'Oral-script text mismatch'
        for reference in spec.get('functions',[]):assert reference['label'] in text
        for source in spec['sources']:
            if not source.startswith('https:'):assert (ROOT/source).exists(),source
        for shape in slide.shapes:
            assert min(shape.left,shape.top)>=0 and shape.left+shape.width<=prs.slide_width+100 and shape.top+shape.height<=prs.slide_height+100
        bitmap=page.render(scale=1.5);im=bitmap.to_pil();im.save(out/f'slide-{i+1:02d}.png');bitmap.close()
        montage.paste(im.resize((480,270)),((i%3)*480,(i//3)*270))
        bitmap=spoken.render(scale=1);bitmap.to_pil().save(out/f'script-{i+1:02d}.png');bitmap.close()
    montage.save(out/'overview.jpg',quality=94)
    report=dict(main_slides=count,code_appendix_slides=0,nominal_speaking_seconds=sum(s['seconds'] for s in data['slides']),
        two_part_structure_verified=True,kitchen_reference_video_embedded_and_hash_verified=True,
        main_speaker_note_words=sum(len(s['notes'].split()) for s in data['slides']),
        pages_rendered=count,oral_script_pdf_pages=count,oral_script_text_verified=True,
        function_reference_occurrences_verified=len(references),function_links_checked_against_source=True,
        mask_experiments_explicitly_documented=True,pptx_shape_bounds_checked=True,speaker_notes_verified=True,
        caveat='PDF slides and script pages rendered for visual review. Native PowerPoint rendering and presenter rehearsal remain outside this automated check.')
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':validate()
