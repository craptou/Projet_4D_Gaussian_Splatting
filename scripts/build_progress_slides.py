"""Build matching bilingual PDF/PPTX slides and speaker-note outlines from deck.json."""
import argparse
import json
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab

ROOT=Path(__file__).resolve().parents[1]
W,H=960,540
INK='18343F'; TEAL='007C78'; MUTED='546B74'; PAPER='F4F7F8'; WHITE='FFFFFF'; AMBER='A45B1C'


def register_fonts():
    candidates=[(Path('C:/Windows/Fonts/arial.ttf'),Path('C:/Windows/Fonts/arialbd.ttf')),
        (Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')),
        (Path(reportlab.__file__).parent/'fonts/Vera.ttf',Path(reportlab.__file__).parent/'fonts/VeraBd.ttf')]
    for regular,bold in candidates:
        if regular.is_file() and bold.is_file():
            pdfmetrics.registerFont(TTFont('Review',str(regular)))
            pdfmetrics.registerFont(TTFont('ReviewBold',str(bold)))
            return
    raise ValueError('No usable presentation fonts found')


def wrap(text,width,size,bold=False):
    font='ReviewBold' if bold else 'Review'
    lines=[]
    for paragraph in text.split('\n'):
        current=''
        for word in paragraph.split():
            trial=(current+' '+word).strip()
            if current and pdfmetrics.stringWidth(trial,font,size)>width:
                lines.append(current);current=word
            else:
                current=trial
        lines.append(current)
    return lines


class Page:
    def __init__(self,pdf,slide):
        self.pdf=pdf;self.slide=slide;self.elements=[]

    def rect(self,x,y,w,h,color):
        self.pdf.setFillColor('#'+color);self.pdf.rect(x,H-y-h,w,h,fill=1,stroke=0)
        s=self.slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Pt(x),Pt(y),Pt(w),Pt(h))
        s.fill.solid();s.fill.fore_color.rgb=RGBColor.from_string(color);s.line.fill.background()

    def text(self,text,x,y,width,size=22,color=INK,bold=False):
        lines=wrap(text,width,size,bold)
        for i,line in enumerate(lines):
            top=y+i*size*1.25
            if top+size>H-8:
                raise ValueError(f'Text runs off slide: {text}')
            if pdfmetrics.stringWidth(line,'ReviewBold' if bold else 'Review',size)>width+1:
                raise ValueError(f'Unbreakable text is too wide: {line}')
            self.pdf.setFillColor('#'+color);self.pdf.setFont('ReviewBold' if bold else 'Review',size)
            self.pdf.drawString(x,H-top-size,line)
            shape=self.slide.shapes.add_textbox(Pt(x),Pt(top),Pt(width+3),Pt(size*1.4))
            tf=shape.text_frame;tf.clear();tf.word_wrap=False
            tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
            p=tf.paragraphs[0];p.text=line;p.font.name='Arial';p.font.size=Pt(size)
            p.font.bold=bold;p.font.color.rgb=RGBColor.from_string(color)
            p.space_before=p.space_after=Pt(0)
            self.elements.append(dict(text=line,x=x,y=top,w=width,h=size*1.25))
        return len(lines)*size*1.25

    def image(self,path,x,y,w,h):
        with Image.open(path) as im:
            iw,ih=im.size
        scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale
        xx,yy=x+(w-ww)/2,y+(h-hh)/2
        self.pdf.drawImage(str(path),xx,H-yy-hh,width=ww,height=hh)
        self.slide.shapes.add_picture(str(path),Pt(xx),Pt(yy),width=Pt(ww),height=Pt(hh))


def bullets(page,items,x,y,width,size=23,gap=17):
    for i,text in enumerate(items,1):
        page.text(f'{i:02d}',x,y+3,40,12,TEAL,True)
        height=page.text(text,x+48,y,width-48,size)
        y+=height+gap
    if y-gap>499:
        raise ValueError(f'Body overlaps footer at y={y-gap}')


def make_page(page,spec,lang,index,total):
    item=spec[lang];kind=spec['kind']
    page.rect(0,0,W,H,PAPER)
    page.rect(0,0,12,H,TEAL)
    page.text(item['section'].upper(),52,24,820,11,TEAL,True)
    page.text('18 NOV 2026  /  '+lang.upper(),765,25,165,10,MUTED)
    if kind=='cover':
        page.text(item['title'],52,96,850,44,INK,True)
        bullets(page,item['bullets'],52,310,850,18,18)
    else:
        height=page.text(item['title'],52,61,865,30,INK,True)
        if height>78:
            raise ValueError('Title takes more than two lines')
        if kind=='pipeline':
            for i,text in enumerate(item['bullets']):
                x=52+(i%2)*448;y=155+(i//2)*160
                page.rect(x,y,420,134,WHITE)
                page.rect(x,y,6,134,TEAL if i<3 else AMBER)
                page.text(f'{i+1:02d}',x+22,y+16,350,14,TEAL if i<3 else AMBER,True)
                page.text(text,x+22,y+48,372,22)
        elif kind=='image':
            bullets(page,item['bullets'],52,155,345,18,17)
            page.image(ROOT/item.get('image',spec['image']),430,160,480,270)
            page.text(item['caption'],435,441,465,12,MUTED)
        elif kind=='figure':
            page.image(ROOT/item.get('image',spec['image']),40,112,880,350)
            page.text(item['caption'],52,472,855,12,MUTED)
        elif kind=='metrics':
            for i,metric in enumerate(spec['metrics']):
                x=52+i*296
                page.rect(x,148,270,100,WHITE)
                page.text(metric['value'],x+18,157,238,34,TEAL,True)
                page.text(metric[lang],x+18,211,238,14,MUTED)
            bullets(page,item['bullets'],52,277,850,20,14)
        elif kind=='table':
            widths=[295,215,150,180];x0=52;y=156
            page.rect(x0,y,sum(widths),42,INK)
            x=x0
            for text,width in zip(item['headers'],widths):
                page.text(text,x+14,y+11,width-20,14,WHITE,True);x+=width
            for row,values in enumerate(item['rows']):
                yy=y+42+row*61;page.rect(x0,yy,sum(widths),59,WHITE);x=x0
                for text,width in zip(values,widths):
                    page.text(text,x+14,yy+19,width-20,18,TEAL if row else INK,row==1);x+=width
            bullets(page,item['bullets'],52,345,850,18,14)
        else:
            bullets(page,item['bullets'],52,157,850,23,19)
    page.rect(52,510,856,1,'D7E1E4')
    page.text('skate-trick-4dgs  /  '+('Progress checkpoint' if lang=='en' else 'Seguimiento del proyecto'),52,520,790,9,MUTED)
    page.text(f'{index:02d} / {total:02d}',854,520,70,9,MUTED)


def build(language):
    data=json.loads((ROOT/'presentations/deck.json').read_text(encoding='utf-8'))
    output=ROOT/'presentations';output.mkdir(exist_ok=True)
    pdf=canvas.Canvas(str(output/f'progress.{language}.pdf'),pagesize=(W,H),invariant=1)
    pdf.setTitle('skate-trick-4dgs | '+('Progress review' if language=='en' else 'Informe de avance'))
    pdf.setAuthor('skate-trick-4dgs project')
    prs=Presentation();prs.slide_width=Pt(W);prs.slide_height=Pt(H)
    prs.core_properties.title='skate-trick-4dgs — '+('Progress review' if language=='en' else 'Seguimiento')
    prs.core_properties.subject='Checkpoint 2026-11-18: sparse moving-camera pose estimation'
    prs.core_properties.author='skate-trick-4dgs project'
    outline=['# '+('Progress presentation — English' if language=='en' else 'Presentación de avance — Español'),
        f'Checkpoint: {data["checkpoint"]} · [PDF](progress.{language}.pdf) · [PowerPoint](progress.{language}.pptx)',
        'Source / Fuente: [deck.json](deck.json).']
    layout=[]
    for index,spec in enumerate(data['slides'],1):
        slide=prs.slides.add_slide(prs.slide_layouts[6]);page=Page(pdf,slide)
        make_page(page,spec,language,index,len(data['slides']))
        slide.notes_slide.notes_text_frame.text=spec[language]['notes']
        layout.append(dict(slide=index,id=spec['id'],text=page.elements))
        item=spec[language]
        outline.extend([f'## {index:02d}. {item["title"].replace(chr(10)," ")}',*['- '+t for t in item['bullets']]])
        if 'rows' in item:
            outline.append('\n'.join(['| '+' | '.join(item['headers'])+' |','| '+' | '.join(['---']*len(item['headers']))+' |',*['| '+' | '.join(row)+' |' for row in item['rows']]]))
        if 'metrics' in spec:
            outline.extend(['- '+m['value']+' — '+m[language] for m in spec['metrics']])
        if 'image' in spec:
            image_path=item.get('image',spec['image'])
            outline.append(f'![{item.get("caption",item["title"])}](../{image_path})')
        outline.extend(['### '+('Speaker notes' if language=='en' else 'Notas para exponer'),item['notes']])
        pdf.showPage()
    pdf.save();prs.save(output/f'progress.{language}.pptx')
    (output/f'progress.{language}.md').write_text('\n\n'.join(outline)+'\n',encoding='utf-8')
    review=ROOT/'outputs/document-review';review.mkdir(parents=True,exist_ok=True)
    (review/f'layout.{language}.json').write_text(json.dumps(layout,indent=2),encoding='utf-8')
    print(f'{language}: {len(data["slides"])} slides in PDF, PPTX and Markdown')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--language',choices=['en','es','both'],default='both')
    args=parser.parse_args();register_fonts()
    for lang in (['en','es'] if args.language=='both' else [args.language]):
        build(lang)
