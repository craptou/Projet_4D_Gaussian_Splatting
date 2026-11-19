"""Validate review links, bilingual slide parity and exported PDF/PPTX structure."""
import json
from pathlib import Path
import re
from urllib.parse import unquote
import pypdfium2 as pdfium
from pptx import Presentation

ROOT=Path(__file__).resolve().parents[1]


def validate():
    files=[ROOT/'README.md',ROOT/'README.es.md',ROOT/'docs/development.en.md']
    for folder in ['docs/progress','docs/templates','presentations']:
        files.extend((ROOT/folder).glob('*.md'))
    missing=[]
    for file in files:
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text(encoding='utf-8')):
            target=link.split('#')[0].strip('<>')
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):
                continue
            target=unquote(target)
            if not (file.parent/target).exists():
                missing.append(f'{file.relative_to(ROOT)} -> {target}')
    if missing:
        raise ValueError('Broken review links:\n'+'\n'.join(missing))
    data=json.loads((ROOT/'presentations/deck.json').read_text(encoding='utf-8'))
    if len(data['slides'])!=12 or len({s['id'] for s in data['slides']})!=12:
        raise ValueError('Expected twelve uniquely identified slides')
    for lang in ['en','es']:
        doc=pdfium.PdfDocument(ROOT/f'presentations/progress.{lang}.pdf')
        prs=Presentation(ROOT/f'presentations/progress.{lang}.pptx')
        if len(doc)!=12 or len(prs.slides)!=12:
            raise ValueError('PDF and PPTX slide counts differ')
        all_text=[]
        for i,(page,slide,spec) in enumerate(zip(doc,prs.slides,data['slides']),1):
            if not spec[lang]['notes'] or not spec[lang]['title']:
                raise ValueError(f'{lang} slide {i}: missing source translation')
            if slide.notes_slide.notes_text_frame.text.strip()!=spec[lang]['notes'].strip():
                raise ValueError(f'{lang} slide {i}: notes differ from source')
            text=page.get_textpage().get_text_range()
            if len(text)<100:
                raise ValueError(f'{lang} slide {i}: missing PDF text')
            all_text.append(text)
            for shape in slide.shapes:
                if min(shape.left,shape.top)<0 or shape.left+shape.width>prs.slide_width+100 or shape.top+shape.height>prs.slide_height+100:
                    raise ValueError(f'{lang} slide {i}: shape outside page')
        combined=' '.join(all_text)
        for token in ['175 / 175','33 / 42','26/26','cam07']:
            if token not in combined:
                raise ValueError(f'{lang}: expected evidence absent: {token}')
        # Render every page so validation exercises actual PDF decoding.
        for page in doc:
            bitmap=page.render(scale=.25)
            bitmap.close()
        print(f'{lang}: 12 PDF pages rendered; PPTX bounds, notes and evidence checked')
    evidence=json.loads((ROOT/'docs/evidence/checkpoint-2026-11-18.json').read_text())
    if evidence['sparse_expanded']['holdout_used_for_sfm'] or evidence['sparse_expanded']['model']['registered_images']!=175:
        raise ValueError('Unexpected checkpoint split or registration result')
    print(f'{len(files)} Markdown files: all relative review links resolve')
    print('Review artifacts validated. Native PowerPoint rendering remains untested.')


if __name__=='__main__':
    validate()
