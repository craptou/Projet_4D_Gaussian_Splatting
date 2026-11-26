"""Build the simple English 5-7 minute presentation and two optional code slides."""
import json
from pathlib import Path
import re
from PIL import Image
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from build_progress_slides import Page,register_fonts,W,H,INK,TEAL,MUTED,PAPER,WHITE,AMBER

ROOT=Path(__file__).resolve().parents[1]
NAME='progress-2026-11-26.en'
ASSETS=ROOT/'docs/assets/talk-2026-11-26'


def make_assets():
    ASSETS.mkdir(parents=True,exist_ok=True)
    source=ROOT/'data/processed/true-skate-dense-comparison'
    polygons=json.loads((ROOT/'data/annotations/static-deck-2026-11-24.json').read_text())['polygons']
    for name in ['view03','view04','view19']:
        xs,ys=zip(*polygons[name]);cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
        left=max(0,min(563-450,round(cx-225)));top=round(cy-180)
        with Image.open(source/f'images/{name}/008.png') as image:image.crop((left,top,left+450,top+360)).save(ASSETS/f'{name}.jpg',quality=94)
    with Image.open(source/'images/view20/003.png') as image:image.crop((0,400,563,1200)).save(ASSETS/'cover.jpg',quality=94)
    with Image.open(ROOT/'docs/assets/near-clip-board.jpg') as image:image.crop((0,810,900,1080)).save(ASSETS/'visibility.jpg',quality=95)
    with Image.open(ROOT/'docs/assets/dynerf-quality-progression.jpg') as image:
        pair=Image.new('RGB',(800,300),'white')
        pair.paste(image.crop((0,26,400,326)),(0,0));pair.paste(image.crop((1200,26,1600,326)),(400,0))
        pair.save(ASSETS/'reference.jpg',quality=94)
    with Image.open(ROOT/'docs/assets/multi-instant-validation.jpg') as image:image.crop((0,300,600,520)).save(ASSETS/'static-board.jpg',quality=94)
    with Image.open(ROOT/'outputs/dynamic-comparison/review/view20-board.jpg') as image:image.crop((0,270,900,540)).save(ASSETS/'comparison.jpg',quality=95)


def lines(page,items,x,y,width,size=22,gap=16):
    for item in items:
        height=page.text('- '+item,x,y,width,size)
        y+=height+gap
    if y-gap>500:raise ValueError('Body collides with slide footer')


def code(page,items,x=65,y=166,size=18):
    page.rect(52,145,856,175,INK)
    for row,line in enumerate(items):
        if pdfmetrics.stringWidth(line,'Courier',size)>824:raise ValueError('Code line too wide')
        top=y+row*size*1.4
        page.pdf.setFillColor('#FFFFFF');page.pdf.setFont('Courier',size);page.pdf.drawString(x,H-top-size,line)
        shape=page.slide.shapes.add_textbox(Pt(x),Pt(top),Pt(824),Pt(size*1.4));tf=shape.text_frame
        tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
        p=tf.paragraphs[0];p.text=line;p.font.name='Consolas';p.font.size=Pt(size);p.font.color.rgb=RGBColor(255,255,255)
        page.elements.append(dict(text=line,x=x,y=top,w=824,h=size*1.4))


def build():
    register_fonts();make_assets()
    spec=json.loads((ROOT/'presentations'/f'{NAME}.json').read_text(encoding='utf-8'))
    pdf=canvas.Canvas(str(ROOT/'presentations'/f'{NAME}.pdf'),pagesize=(W,H),invariant=1)
    pdf.setTitle('Computer Vision final project - progress, 26 November 2026');pdf.setAuthor(spec['author'])
    prs=Presentation();prs.slide_width=Pt(W);prs.slide_height=Pt(H)
    prs.core_properties.title='Free-viewpoint skate replay - project progress'
    prs.core_properties.author=spec['author'];prs.core_properties.subject='5-7 minute English presentation, 26 November 2026'
    outline=['# Project progress — 26 November 2026',
        'English · 8 main slides (about 6 minutes) + 2 optional code slides.',
        f'[PDF]({NAME}.pdf) · [PowerPoint with speaker notes]({NAME}.pptx) · [Editable content]({NAME}.json)',
        'Course page numbers refer to the supplied 46-page notes, including the title page. No course PDF is redistributed.']
    layouts=[]
    for index,item in enumerate(spec['slides'],1):
        slide=prs.slides.add_slide(prs.slide_layouts[6]);p=Page(pdf,slide)
        p.rect(0,0,W,H,PAPER);p.rect(0,0,12,H,TEAL)
        p.text(item['section'].upper(),52,26,700,11,TEAL,True)
        p.text('26 NOV 2026 / EN',780,26,150,10,MUTED)
        if item['id']=='goal':
            p.text(item['title'],52,104,550,40,INK,True)
            lines(p,item['bullets'],52,270,535,21,18)
            p.image(ASSETS/'cover.jpg',650,95,255,365)
            p.text('Raphael Landry · Computer Vision final project',52,475,850,15,MUTED)
        else:
            if p.text(item['title'],52,65,860,30,INK,True)>76:raise ValueError('Title too tall')
            key=item['id']
            if key=='data':
                for i,label in enumerate(['Replay clips','Camera poses','Gaussian scene','Validation']):
                    x=52+i*218;p.rect(x,132,200,57,WHITE);p.text(label,x+12,149,182,18,TEAL,True)
                p.text('One replay · fixed viewpoints · approximate event alignment',52,205,856,18)
                for i,name in enumerate(['view03','view04','view19']):
                    p.image(ASSETS/f'{name}.jpg',52+i*290,246,276,220)
                    p.text(name+' / same nominal instant',56+i*290,477,272,13,MUTED)
            elif key=='course':
                cards=[('Coordinates','World points → camera coordinates','3–4, 13–15'),('Projection + visibility','Perspective and near-plane clipping','12–18'),
                    ('Sampling','Video frames and temporal alignment','21–22'),('Rasterization','Gaussian elements → image pixels','15–18')]
                for i,(title,body,pages) in enumerate(cards):
                    x=52+(i%2)*438;y=140+(i//2)*176
                    p.rect(x,y,418,151,WHITE);p.rect(x,y,5,151,TEAL)
                    p.text(title,x+20,y+16,374,23,TEAL,True)
                    p.text(body,x+20,y+56,374,20)
                    p.text('Course notes, PDF pp. '+pages,x+20,y+124,374,12,MUTED)
            elif key=='geometry':
                p.image(ASSETS/'visibility.jpg',52,139,856,257)
                p.text('Same image projections. Corrected point visibility.',52,416,856,23,TEAL,True)
                p.text('Reserved view20 · one static instant · course: camera transforms and clipping, pp. 12–18',52,474,856,12,MUTED)
            elif key=='progress':
                for x,title,asset,caption in [(52,'Calibrated reference','reference.jpg','DyNeRF: original / trained model'),(490,'Our skate replay','static-board.jpg','True Skate: original / independent static fit')]:
                    p.rect(x,142,418,296,WHITE);p.text(title,x+16,158,386,22,TEAL,True)
                    p.image(ASSETS/asset,x+12,208,394,171);p.text(caption,x+16,397,386,14,MUTED)
                p.text('Three static instants work; a faithful flip is still the challenge.',52,459,856,21,INK,True)
                p.text('DyNeRF imagery: Li et al., CVPR 2022 / CC BY-NC 4.0. True Skate: project recording.',52,490,856,10,MUTED)
            elif key=='comparison':
                p.text('Same inputs: 11 training views × 10 instants; view20 reserved',52,132,856,19,TEAL,True)
                p.image(ASSETS/'comparison.jpg',52,182,856,257)
                p.text('Middle of the flip · actual saved models · adapted, short-budget trials',52,453,856,16,MUTED)
                p.text('Neither method reconstructs the airborne board reliably.',52,483,856,17,INK,True)
            elif key=='contribution':
                for x,title,items in [(52,'Project scripts',['Clip extraction and frame alignment','Dataset conversion and GPU launchers','Projection checks and evaluation']),
                    (490,'Reused implementations',['COLMAP: camera estimation','4DGaussians: temporal rendering','Dynamic3DGaussians: sequential fitting'])]:
                    p.rect(x,145,418,272,WHITE);p.text(title,x+18,165,382,24,TEAL,True);lines(p,items,x+18,220,382,21,19)
                p.text('AI-assisted development; existing algorithms are credited.',52,455,856,19,MUTED)
                p.text('Two short code examples follow the main talk.',52,483,856,18,TEAL,True)
            elif key=='next':
                lines(p,item['bullets'],52,160,850,25,28)
                p.rect(52,419,856,70,TEAL);p.text('Reliable geometry first. Reliable motion next.',72,438,815,25,WHITE,True)
            else:
                code(p,item['code'],size=17)
                lines(p,item['bullets'],52,347,856,19,13)
                path=item['sources'][0]
                p.text('Source: '+path,52,480,856,12,TEAL)
        p.rect(52,510,856,1,'D7E1E4')
        p.text('Computer Vision / final project progress',52,520,700,9,MUTED)
        p.text(f'{index:02d} / 08' if index<=8 else 'CODE '+str(index-8),838,520,90,9,MUTED)
        sources='\n'.join(item['sources'])
        slide.notes_slide.notes_text_frame.text=item['notes']+'\n\nSources / evidence:\n'+sources
        layouts.append(dict(index=index,id=item['id'],elements=p.elements))
        outline.extend([f'## {index}. {item["title"]}',('Suggested time: '+str(item['seconds'])+' seconds.') if item['seconds'] else 'Optional code discussion; outside the 5–7 minute talk.',
            '\n'.join('- '+text for text in item['bullets']),'### Speaker notes',item['notes']])
        if item.get('code'):outline.append('```python\n'+'\n'.join(item['code'])+'\n```')
        links=[]
        for source in item['sources']:
            links.append('['+source+']('+('' if source.startswith('https:') else '../')+source+')')
        outline.append('Sources: '+' · '.join(links));pdf.showPage()
    pdf.save();prs.save(ROOT/'presentations'/f'{NAME}.pptx')
    (ROOT/'presentations'/f'{NAME}.md').write_text('\n\n'.join(outline)+'\n',encoding='utf-8')
    out=ROOT/'outputs/presentation-review-2026-11-26';out.mkdir(parents=True,exist_ok=True)
    (out/'layout.json').write_text(json.dumps(layouts,indent=2)+'\n',encoding='utf-8')
    print('Built 8 main slides +2 code slides in English; PDF, editable PPTX and speaker notes.')


if __name__=='__main__':build()
