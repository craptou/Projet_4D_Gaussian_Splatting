"""Build the English presentation with contextual function links and a separate oral-script PDF."""
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
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4
from xml.sax.saxutils import escape
from build_progress_slides import Page,register_fonts,W,H,INK,TEAL,MUTED,PAPER,WHITE
from presentation_functions import resolve

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
    with Image.open(ROOT/'docs/assets/foreground-trial-training.jpg') as image:image.crop((0,150,900,345)).save(ASSETS/'mask-trial.jpg',quality=95)


def lines(page,items,x,y,width,size=22,gap=16):
    for item in items:
        height=page.text('- '+item,x,y,width,size)
        y+=height+gap
    if y-gap>500:raise ValueError('Body collides with slide footer')


def ellipse(page,x,y,w,h,angle):
    """Editable schematic of overlapping Gaussian footprints; not reconstructed data."""
    for layer in range(8):
        fraction=1-layer*.09;ww=w*fraction;hh=h*fraction
        page.pdf.saveState();page.pdf.setFillColor('#'+TEAL);page.pdf.setFillAlpha(.065)
        page.pdf.translate(x+w/2,H-y-h/2);page.pdf.rotate(-angle)
        page.pdf.ellipse(-ww/2,-hh/2,ww/2,hh/2,fill=1,stroke=0);page.pdf.restoreState()
        shape=page.slide.shapes.add_shape(MSO_SHAPE.OVAL,Pt(x+(w-ww)/2),Pt(y+(h-hh)/2),Pt(ww),Pt(hh));shape.rotation=angle
        shape.fill.solid();shape.fill.fore_color.rgb=RGBColor.from_string(TEAL);shape.line.fill.background()
        alpha=OxmlElement('a:alpha');alpha.set('val','6500');shape._element.xpath('.//a:srgbClr')[0].append(alpha)


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
            y=197+row*61;p.text(label,65,y+12,130,20)
            for col,time in enumerate(['t0','t1','t2']):
                x=230+col*220;color=TEAL if col==1 else WHITE
                p.rect(x,y,185,46,color);p.text(time,x+69,y+9,80,22,WHITE if col==1 else INK,True)
        p.text('One training instant = matching scene states across views',52,386,856,20)
    elif key=='step-cameras':
        flow(p,['Match background details','Estimate camera poses','Triangulate 3D points'],y=137)
        lines(p,['Use static background features to estimate the cameras.','Jointly refine camera poses and sparse 3D points.','Check that reconstructed points return to observed pixels.'],52,230,850,21,17)
    elif key=='step-projection':
        flow(p,['World coordinates','Camera coordinates','Image pixels'],y=137)
        p.text('Xcamera = R × Xworld + t',74,239,800,27,TEAL,True)
        p.text('u = f × x / z + cx        v = f × y / z + cy',74,296,800,25,INK,True)
        p.text('Points must also be visible: our near-plane check catches clipped seeds.',52,366,856,19)
    elif key=='step-gaussians':
        ellipse(p,91,212,192,69,-25);ellipse(p,179,184,83,149,20);ellipse(p,220,245,162,58,25)
        p.text('Projected soft footprints',65,355,360,18,MUTED)
        p.text('(schematic, not reconstructed data)',65,384,360,13,MUTED)
        lines(p,['Center = location in 3D','Size + rotation = ellipsoid shape','Opacity + appearance = pixel contribution'],463,167,445,21,24)
    elif key=='step-learning':
        flow(p,['Project Gaussians','Blend by depth','Compare target','Update parameters'],y=137)
        p.text('Rendering',52,235,200,22,TEAL,True)
        p.text('A camera turns the current scene into pixels.',270,235,625,22)
        p.text('Training',52,297,200,22,TEAL,True)
        p.text('Image error → gradients → improved scene parameters.',270,297,625,22)
        p.text('Each pixel combines several contributions using depth and opacity.',52,369,856,18)
    elif key=='step-time':
        for x,title,body in [(52,'4DGaussians','One reference scene + a network predicting changes with time.'),
            (490,'Dynamic 3D Gaussians','Successive scene states + constraints on local motion.')]:
            p.rect(x,145,418,184,WHITE);p.text(title,x+18,165,382,23,TEAL,True);p.text(body,x+18,218,382,21)
        p.text('Both methods need calibrated cameras as inputs.',52,363,856,22,INK,True)
    elif key=='step-evaluation':
        for x,title,body in [(52,'Training views','Optimize the scene from the selected input cameras.'),(490,'Reserved view20','Compare against images excluded from scene optimization.')]:
            p.rect(x,145,418,161,WHITE);p.text(title,x+18,166,382,23,TEAL,True);p.text(body,x+18,214,382,21)
        p.text('Evaluate the whole image AND the board region.',52,336,856,23,INK,True)
        p.text('All ten times in the latest comparison are supervised; this is not an unseen-time test.',52,383,856,17,MUTED)
    elif key=='acquisition':
        for x,title,asset,items in [(52,'Downloaded: kitchen scene','kitchen-input.jpg',['Synchronized multi-camera videos','Supplied camera calibration']),
            (490,'Recorded: True Skate','view04.jpg',['Following cameras → fixed views','Estimated poses; approximate alignment'])]:
            p.rect(x,143,418,260,WHITE);p.text(title,x+16,158,386,22,TEAL,True)
            p.image(ASSETS/asset,x+16,199,386,121);lines(p,items,x+16,339,386,16,8)
        p.text('Reference: controlled capture. Own data: repeated replay recordings.',52,410,856,15,MUTED)
    elif key=='kitchen-result':
        for x,label,asset in [(52,'Input image','kitchen-input.jpg'),(490,'Actual trained model','kitchen-model.jpg')]:
            p.text(label,x,134,418,22,TEAL,True);p.image(ASSETS/asset,x,170,418,225)
        p.slide.shapes.add_movie(str(ROOT/'docs/assets/4d-demo-time.mp4'),Pt(549),Pt(170),Pt(300),Pt(225),
            poster_frame_image=str(ASSETS/'kitchen-model.jpg'),mime_type='video/mp4')
        p.text('Recognizable scene and motion; residual blur and color errors.',52,400,856,18,INK,True)
        p.text('DyNeRF / Li et al., CVPR 2022 / CC BY-NC 4.0 · Small pilot (~1 s scene time)',52,422,710,10,MUTED)
    elif key=='skate-result':
        p.text('Recorded frame',121,135,340,22,TEAL,True);p.text('4DGS reconstruction',510,135,370,22,TEAL,True)
        p.image(ASSETS/'skate-result.jpg',52,174,856,205)
        p.text('Board motion remains unreliable. Mask-based training WAS tested.',52,390,856,19,INK,True)
        p.text('Different scenes and training settings: this comparison does not isolate data quality alone.',52,417,856,10,MUTED)
    elif key=='masks-tested':
        for x,label in [(52,'Recording'),(342,'Baseline'),(632,'Foreground weighting')]:p.text(label,x,136,280,18,TEAL,True)
        p.image(ASSETS/'mask-trial.jpg',52,174,856,185)
        p.text('Earlier view19 control: masked training PSNR 11.79 → 25.18 dB.',52,369,856,18,INK,True)
        p.text('Better training fit, but a dark smear. Later trials used multi-view masks too.',52,397,856,17)
        p.text('Next: refine existing masks, timing and initially visible surfaces.',52,420,856,13,TEAL)
    else:raise ValueError('Unknown slide kind: '+key)


def function_band(page,item):
    references=[resolve(reference) for reference in item.get('functions',[])]
    if not references:return
    page.rect(52,436,856,63,WHITE)
    for i,reference in enumerate(references):
        text=reference['label']+' — '+reference['role'];y=443+i*27
        if pdfmetrics.stringWidth(text,'Review',14)>830:raise ValueError('Function label too wide: '+text)
        page.text(text,65,y,830,14,TEAL)
        page.pdf.linkURL(reference['url'],(65,H-y-19,895,H-y),relative=0,thickness=0)
        page.slide.shapes[-1].click_action.hyperlink.address=reference['url']


def oral_script(spec):
    """One portrait page per slide: spoken text separated from optional code locations."""
    output=ROOT/'presentations'/'progress-2026-11-26.script.en.pdf'
    styles={
        'title':ParagraphStyle('ScriptTitle',fontName='ReviewBold',fontSize=20,leading=26,textColor='#'+TEAL,spaceAfter=14),
        'meta':ParagraphStyle('ScriptMeta',fontName='Review',fontSize=11,leading=16,textColor='#'+MUTED,spaceAfter=16),
        'label':ParagraphStyle('ScriptLabel',fontName='ReviewBold',fontSize=12,leading=17,textColor='#'+TEAL,spaceAfter=8),
        'message':ParagraphStyle('ScriptMessage',fontName='ReviewBold',fontSize=13,leading=19,textColor='#'+INK,spaceAfter=18),
        'spoken':ParagraphStyle('ScriptSpoken',fontName='Review',fontSize=14,leading=23,textColor='#'+INK,spaceAfter=18),
        'function':ParagraphStyle('ScriptFunction',fontName='Review',fontSize=11,leading=16,textColor='#'+INK,spaceAfter=10)
    }
    story=[]
    for i,item in enumerate(spec['slides'],1):
        story.extend([Paragraph(f'Slide {i} — '+escape(item['title']),styles['title']),
            Paragraph(escape(item['section'])+f' · Suggested time: {item["seconds"]} seconds',styles['meta']),
            Paragraph('Main message',styles['label']),Paragraph(escape(item['bullets'][0]),styles['message']),
            Paragraph('What to say',styles['label'])])
        for paragraph in item['notes'].split('\n\n'):story.append(Paragraph(escape(paragraph),styles['spoken']))
        references=[resolve(reference) for reference in item.get('functions',[])]
        if references:
            story.extend([Spacer(1,10),Paragraph('Functions to open — optional, not part of the spoken text',styles['label'])])
            for reference in references:
                body=f'<link href="{reference["url"]}" color="#{TEAL}">{escape(reference["label"])}</link><br/>'+escape(reference['role'])
                story.append(Paragraph(body,styles['function']))
        if i<len(spec['slides']):story.append(PageBreak())
    def furniture(canvas,doc):
        width,height=A4;canvas.setFont('Review',10);canvas.setFillColor('#'+MUTED)
        canvas.drawString(48,height-30,'Oral script · English · 26 November 2026')
        canvas.drawString(48,25,'Speak the “What to say” section; use function links for code discussion.')
        canvas.drawRightString(width-48,25,str(doc.page))
    SimpleDocTemplate(str(output),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=56,bottomMargin=48,
        title='English oral script — project progress',author=spec['author']).build(story,onFirstPage=furniture,onLaterPages=furniture)


def build():
    register_fonts();make_assets()
    spec=json.loads((ROOT/'presentations'/f'{NAME}.json').read_text(encoding='utf-8'))
    pdf=canvas.Canvas(str(ROOT/'presentations'/f'{NAME}.pdf'),pagesize=(W,H),invariant=1)
    pdf.setTitle('Computer Vision final project - progress, 26 November 2026');pdf.setAuthor(spec['author'])
    prs=Presentation();prs.slide_width=Pt(W);prs.slide_height=Pt(H)
    prs.core_properties.title='Free-viewpoint skate replay - project progress'
    prs.core_properties.author=spec['author'];prs.core_properties.subject='English presentation, about 10 minutes, 26 November 2026'
    outline=['# Project progress — 26 November 2026',
        f'English · {len(spec["slides"])} slides (about 10 minutes). Function references appear alongside the relevant concepts; no code appendix.',
        f'[Slide PDF]({NAME}.pdf) · [PowerPoint with speaker notes]({NAME}.pptx) · [Oral-script PDF](progress-2026-11-26.script.en.pdf) · [Editable content]({NAME}.json)',
        'Project concepts are explained step by step, with function links.']
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
            function_band(p,item)
        p.rect(52,510,856,1,'D7E1E4')
        p.text('Computer Vision / final project progress',52,520,700,9,MUTED)
        p.text(f'{index:02d} / {len(spec["slides"]):02d}',838,520,90,9,MUTED)
        sources='\n'.join(item['sources'])
        references=[resolve(reference) for reference in item.get('functions',[])]
        function_notes='\n'.join(f'{r["label"]}: {r["role"]}\n{r["file"]}:{r["line"]}\n{r["url"]}' for r in references)
        slide.notes_slide.notes_text_frame.text=item['notes']+'\n\nFunctions to open:\n'+function_notes+'\n\nSources / evidence:\n'+sources
        layouts.append(dict(index=index,id=item['id'],elements=p.elements))
        outline.extend([f'## {index}. {item["title"]}','Suggested time: '+str(item['seconds'])+' seconds.',
            '\n'.join('- '+text for text in item['bullets']),'### Speaker notes',item['notes']])
        if references:
            outline.extend(['### Functions to open','\n'.join(f'- [{r["label"]}]({r["url"]}) — {r["role"]}; `{r["file"]}:{r["line"]}`' for r in references)])
        links=[]
        for source in item['sources']:
            links.append('['+source+']('+('' if source.startswith('https:') else '../')+source+')')
        outline.append('Sources: '+' · '.join(links));pdf.showPage()
    pdf.save();prs.save(ROOT/'presentations'/f'{NAME}.pptx')
    (ROOT/'presentations'/f'{NAME}.md').write_text('\n\n'.join(outline)+'\n',encoding='utf-8')
    oral_script(spec)
    out=ROOT/'outputs/presentation-review-2026-11-26';out.mkdir(parents=True,exist_ok=True)
    (out/'layout.json').write_text(json.dumps(layouts,indent=2)+'\n',encoding='utf-8')
    print(f'Built {len(spec["slides"])} English slides with function links, PPTX, PDF and a separate oral-script PDF.')


if __name__=='__main__':build()
