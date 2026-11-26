"""Build the simple English 5-7 minute presentation and two optional code slides."""
import json
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.util import Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.xmlchemy import OxmlElement
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from build_progress_slides import Page,register_fonts,W,H,INK,TEAL,MUTED,PAPER,WHITE

ROOT=Path(__file__).resolve().parents[1]
NAME='progress-2026-11-26.en'
ASSETS=ROOT/'docs/assets/talk-2026-11-26'


def make_assets():
    ASSETS.mkdir(parents=True,exist_ok=True)
    for name in ['cover.jpg','view04.jpg']:
        if not (ASSETS/name).is_file():raise ValueError('Missing tracked presentation image: '+name)
    with Image.open(ROOT/'docs/assets/dynerf-quality-progression.jpg') as image:
        image.crop((0,26,400,326)).save(ASSETS/'kitchen-input.jpg',quality=94)
    with Image.open(ROOT/'docs/assets/4d-demo-time.gif') as image:image.convert('RGB').save(ASSETS/'kitchen-model.jpg',quality=94)
    with Image.open(ROOT/'docs/assets/dynamic-comparison-validation.jpg') as image:image.crop((0,326,600,535)).save(ASSETS/'skate-result.jpg',quality=95)


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


def ellipse(page,x,y,w,h,angle):
    """Editable schematic of overlapping Gaussian footprints; not reconstructed data."""
    page.pdf.saveState();page.pdf.setFillColor('#'+TEAL);page.pdf.setFillAlpha(.35)
    page.pdf.translate(x+w/2,H-y-h/2);page.pdf.rotate(-angle)
    page.pdf.ellipse(-w/2,-h/2,w/2,h/2,fill=1,stroke=0);page.pdf.restoreState()
    shape=page.slide.shapes.add_shape(MSO_SHAPE.OVAL,Pt(x),Pt(y),Pt(w),Pt(h));shape.rotation=angle
    shape.fill.solid();shape.fill.fore_color.rgb=RGBColor.from_string(TEAL);shape.line.fill.background()
    alpha=OxmlElement('a:alpha');alpha.set('val','35000');shape._element.xpath('.//a:srgbClr')[0].append(alpha)


def flow(page,labels,y=145):
    width=(856-28*(len(labels)-1))/len(labels)
    for i,label in enumerate(labels):
        x=52+i*(width+28);page.rect(x,y,width,65,WHITE);page.text(label,x+12,y+19,width-24,18,TEAL,True)
        if i<len(labels)-1:page.text('→',x+width+5,y+19,24,20,TEAL)


def render_body(p,item):
    key=item['id']
    if key=='step-images':
        p.text('Videos → extract frames → align time → consistent image size',52,137,856,21,TEAL,True)
        for row,label in enumerate(['View A','View B','View C']):
            y=210+row*78;p.text(label,65,y+19,130,21)
            for col,time in enumerate(['t0','t1','t2']):
                x=230+col*220;color=TEAL if col==1 else WHITE
                p.rect(x,y,185,60,color);p.text(time,x+69,y+17,80,23,WHITE if col==1 else INK,True)
        p.text('One training instant = matching scene states across views',52,458,856,21)
        p.text('Course: image coordinates and sampling · PDF pp. 5–6, 21–22',52,490,856,11,MUTED)
    elif key=='step-cameras':
        flow(p,['Match background details','Estimate camera poses','Triangulate 3D points'])
        lines(p,['COLMAP jointly refines cameras and sparse points.','Camera pose: position and orientation.','Check: do 3D points return to the observed pixels?'],52,252,850,22,22)
        p.rect(52,425,856,50,TEAL);p.text('World coordinates → camera coordinates → image pixels',70,438,820,21,WHITE,True)
        p.text('Course: transformations and perspective · PDF pp. 3–4, 12–15',52,490,856,11,MUTED)
    elif key=='step-gaussians':
        flow(p,['3D Gaussians','Render an image','Compare target','Update parameters'])
        ellipse(p,104,286,170,60,-25);ellipse(p,187,264,80,130,20);ellipse(p,226,306,150,55,25)
        p.text('Soft projected contributions',65,405,350,17,MUTED)
        p.text('(schematic)',65,432,350,14,MUTED)
        lines(p,['Position, size and rotation','Opacity and appearance','Gradients improve the rendered image'],470,260,438,21,20)
        p.text('Course: perspective, visibility and rasterization · PDF pp. 12–18',52,490,856,11,MUTED)
    elif key=='step-time':
        for x,title,body in [(52,'4DGaussians','One reference scene + a network predicting changes with time.'),
            (490,'Dynamic 3D Gaussians','Successive scene states + constraints on local motion.')]:
            p.rect(x,150,418,202,WHITE);p.text(title,x+18,171,382,23,TEAL,True);p.text(body,x+18,228,382,22)
        p.text('Choose time + camera → render → compare with a reserved view',52,389,856,23,INK,True)
        p.text('A rendered animation does not by itself prove physical tracking.',52,463,856,18,MUTED)
        p.text('Course: rotation, time sampling and rendering · PDF pp. 4, 15–18, 21–22',52,490,856,11,MUTED)
    elif key=='acquisition':
        for x,title,asset,items in [(52,'Downloaded: kitchen scene','kitchen-input.jpg',['Synchronized multi-camera videos','Supplied camera calibration']),
            (490,'Recorded: True Skate','view04.jpg',['Following cameras → fixed views','Estimated poses; approximate alignment'])]:
            p.rect(x,145,418,305,WHITE);p.text(title,x+16,161,386,22,TEAL,True)
            p.image(ASSETS/asset,x+16,203,386,151);lines(p,items,x+16,374,386,17,9)
        p.text('Reference: controlled capture. Own data: repeated replay recordings.',52,474,856,18,INK,True)
    elif key=='kitchen-result':
        for x,label,asset in [(52,'Input image','kitchen-input.jpg'),(490,'Actual trained model','kitchen-model.jpg')]:
            p.text(label,x,137,418,22,TEAL,True);p.image(ASSETS/asset,x,177,418,285)
        # Embed the existing 3-second render directly; PDF retains the same poster.
        p.slide.shapes.add_movie(str(ROOT/'docs/assets/4d-demo-time.mp4'),Pt(509),Pt(177),Pt(380),Pt(285),
            poster_frame_image=str(ASSETS/'kitchen-model.jpg'),mime_type='video/mp4')
        p.text('Recognizable scene and motion; residual blur and color errors.',52,465,856,19,INK,True)
        p.text('DyNeRF / Li et al., CVPR 2022 / CC BY-NC 4.0 · Small pilot (~1 s of scene time)',52,491,710,10,MUTED)
        p.text('3-second model clip',753,491,170,10,TEAL)
        url='https://github.com/craptou/Projet_4D_Gaussian_Splatting/raw/refs/heads/main/docs/assets/4d-demo-time.mp4'
        p.pdf.linkURL(url,(753,H-506,925,H-488),relative=0,thickness=0)
        p.slide.shapes[-1].click_action.hyperlink.address=url
    elif key=='skate-result':
        p.text('Recorded frame',121,139,340,22,TEAL,True);p.text('4DGS reconstruction',510,139,370,22,TEAL,True)
        p.image(ASSETS/'skate-result.jpg',52,175,856,250)
        p.text('The background is recognizable; board motion is unreliable.',52,439,856,21,INK,True)
        p.text('Next: check timing, masks and initially visible surfaces.',52,471,856,19,TEAL)
        p.text('Different scenes and training settings: this comparison does not isolate data quality alone.',52,494,856,10,MUTED)
    else:
        code(p,item['code'],size=17);lines(p,item['bullets'],52,347,856,19,13)
        p.text('Source: '+item['sources'][0],52,480,856,12,TEAL)


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
            render_body(p,item)
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
