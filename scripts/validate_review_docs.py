"""Validate review links, bilingual slide parity and exported PDF/PPTX structure."""
import json
import hashlib
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
        for token in ['175 / 175','33 / 42','26/26','2725','cam07','Computer Vision','CVI 26-2']:
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
    fullrate=json.loads((ROOT/'docs/evidence/fullrate-2026-11-18.json').read_text())
    if fullrate['final_report']['localized_frames']!=2725 or fullrate['final_report']['holdout_used']:
        raise ValueError('Unexpected full-rate coverage or holdout use')
    if not fullrate['quality']['reference_map_unchanged'] or fullrate['quality']['anchor_max_matrix_difference']!=0:
        raise ValueError('Frozen-map/anchor guarantee changed')
    context=json.loads((ROOT/'docs/evidence/course-context.json').read_text(encoding='utf-8'))
    if context['course_name_from_owner']!='Computer Vision' or context['assignment_role_from_owner']!='final course project':
        raise ValueError('Course/final-project context differs from owner clarification')
    source=ROOT/context['local_filename']
    if source.exists():
        if hashlib.sha256(source.read_bytes()).hexdigest()!=context['sha256']:
            raise ValueError('Supplied course PDF changed; review the course map again')
        if len(pdfium.PdfDocument(source))!=context['pdf_page_count']:
            raise ValueError('Course PDF page count differs')
        print('Local course PDF fingerprint and 46-page context verified')
    print(f'{len(files)} Markdown files: all relative review links resolve')
    print('Review artifacts validated. Native PowerPoint rendering remains untested.')


if __name__=='__main__':
    validate()
