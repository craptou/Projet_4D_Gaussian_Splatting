"""Validate short-deck content, code examples, speaker notes and exported page structure."""
import json
from pathlib import Path
import sys
import hashlib
from zipfile import ZipFile
import numpy as np
from PIL import Image,ImageDraw
import pypdfium2 as pdfium
from pptx import Presentation
from static_board_geometry import project

ROOT=Path(__file__).resolve().parents[1]
NAME='progress-2026-11-26.en'


def validate():
    data=json.loads((ROOT/'presentations'/f'{NAME}.json').read_text(encoding='utf-8'))
    assert data['main_slides']==8 and len(data['slides'])==10
    assert [s['id'] for s in data['slides'][:8]]==['goal','step-images','step-cameras','step-gaussians','step-time','acquisition','kitchen-result','skate-result']
    assert 300<=sum(s['seconds'] for s in data['slides'])<=420
    namespace={};exec('\n'.join(data['slides'][8]['code']),namespace)
    points=np.array([[1.,2.,4.],[-2.,1.,3.]])
    pose=np.c_[np.eye(3),[.1,.2,1.]];intrinsics=[400.,281.5,609.]
    actual=project(points,pose,intrinsics);shown=namespace['project'](points,pose,intrinsics)
    for a,b in zip(actual,shown):np.testing.assert_array_equal(a,b)
    guard='def check(record):\n'+'\n'.join('    '+line for line in data['slides'][9]['code'])
    exec(guard,namespace)
    namespace['check'](dict(split='train',foreground_mask_path='mask.png'))
    try:namespace['check'](dict(split='test',foreground_mask_path='mask.png'))
    except ValueError:pass
    else:raise AssertionError('Shown guard allows validation leakage')
    prs=Presentation(ROOT/'presentations'/f'{NAME}.pptx');doc=pdfium.PdfDocument(ROOT/'presentations'/f'{NAME}.pdf')
    assert len(prs.slides)==len(doc)==10
    with ZipFile(ROOT/'presentations'/f'{NAME}.pptx') as package:
        media=[name for name in package.namelist() if name.startswith('ppt/media/') and name.endswith('.mp4')]
        expected=hashlib.sha256((ROOT/'docs/assets/4d-demo-time.mp4').read_bytes()).digest()
        assert any(hashlib.sha256(package.read(name)).digest()==expected for name in media),'Reference video missing from PowerPoint'
    out=ROOT/'outputs/presentation-review-2026-11-26';out.mkdir(parents=True,exist_ok=True)
    montage=Image.new('RGB',(3*480,4*270),'#dce4e8');draw=ImageDraw.Draw(montage)
    for i,(slide,page,spec) in enumerate(zip(prs.slides,doc,data['slides'])):
        assert spec['notes'] in slide.notes_slide.notes_text_frame.text
        text=page.get_textpage().get_text_range()
        assert len(text)>100 and spec['title'][:20] in text
        for source in spec['sources']:
            if not source.startswith('https:'):assert (ROOT/source).exists(),source
        for shape in slide.shapes:
            assert min(shape.left,shape.top)>=0 and shape.left+shape.width<=prs.slide_width+100 and shape.top+shape.height<=prs.slide_height+100
        bitmap=page.render(scale=1.5);im=bitmap.to_pil();im.save(out/f'slide-{i+1:02d}.png');bitmap.close()
        thumb=im.resize((480,270));montage.paste(thumb,((i%3)*480,(i//3)*270))
    montage.save(out/'overview.jpg',quality=94)
    report=dict(main_slides=8,code_appendix_slides=2,nominal_speaking_seconds=sum(s['seconds'] for s in data['slides']),
        two_part_structure_verified=True,kitchen_reference_video_embedded_and_hash_verified=True,
        main_speaker_note_words=sum(len(s['notes'].split()) for s in data['slides'][:8]),
        pages_rendered=10,pptx_shape_bounds_checked=True,speaker_notes_verified=True,code_examples_checked=True,
        caveat='PDF pages rendered for visual review. Native PowerPoint rendering and rehearsal by the presenter remain outside this automated check.')
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':validate()
