"""Render reports/FINAL_RESEARCH_REPORT.md to PDF. Optional dependency: reportlab."""
from pathlib import Path
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"reports/SENTINEL-X-Research-Report.pdf"
W,H=A4
ink="#142E34"
green="#087C72"
styles={
    "title":ParagraphStyle("title",fontName="Helvetica-Bold",fontSize=35,leading=40,textColor=colors.HexColor(ink),spaceAfter=9),
    "subtitle":ParagraphStyle("subtitle",fontName="Helvetica",fontSize=17,leading=21,textColor=colors.HexColor(green),spaceAfter=12),
    "h":ParagraphStyle("h",fontName="Helvetica-Bold",fontSize=14,leading=17,textColor=colors.HexColor(ink),spaceBefore=12,spaceAfter=5,keepWithNext=True),
    "p":ParagraphStyle("p",fontName="Helvetica",fontSize=10.6,leading=15.4,textColor=colors.HexColor(ink),spaceAfter=7),
    "small":ParagraphStyle("small",fontName="Helvetica",fontSize=8.8,leading=12,textColor=colors.HexColor(green),spaceAfter=8),
}
def header(canvas,doc):
    canvas.setFillColor(colors.HexColor(green))
    canvas.rect(0,H-8,W,8,stroke=0,fill=1)
    canvas.setFont("Helvetica-Bold",9)
    canvas.drawString(44,H-36,"SENTINEL-X   /   RESEARCH RELEASE")
    canvas.setFont("Helvetica",9)
    canvas.drawRightString(W-44,H-36,"20 NOVEMBER 2026")
    canvas.setStrokeColor(colors.HexColor("#C3D5D1"))
    canvas.line(44,40,W-44,40)
    canvas.drawString(44,25,"Detection, calibration and evidence-grounded investigation")
    canvas.drawRightString(W-44,25,str(doc.page))

def paragraph(text,style):
    text=re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",text)
    return Paragraph(escape(text.replace("**","")),styles[style])

def write_table(lines):
    rows=[[x.strip() for x in row.strip("|").split("|")] for row in lines if not row.startswith("|---")]
    table=Table(rows,hAlign="LEFT",colWidths=([210,82,82,130] if len(rows[0])==4 else [210,145,149]),repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#D9ECE7")),
        ("TEXTCOLOR",(0,0),(-1,-1),colors.HexColor(ink)),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9.5),
        ("ALIGN",(1,0),(-1,-1),"RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F3F7F6")]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    return table

def main():
    content=(ROOT/"reports/FINAL_RESEARCH_REPORT.md").read_text()
    flow=[]
    for block in content.strip().split("\n\n"):
        if block.startswith("# SENTINEL"):
            title,subtitle=block.splitlines()
            flow.extend([paragraph(title[2:],"title"),paragraph(subtitle[3:],"subtitle")])
        elif block.startswith("###"):
            if block.startswith(("### H1","### H4","### H6")):
                flow.append(PageBreak())
            flow.append(paragraph(block[4:],"h"))
        elif block.startswith("|"):
            flow.extend([write_table(block.splitlines()),Spacer(1,8)])
        else:
            flow.append(paragraph(block,"small" if block.startswith("**") else "p"))
        if block.startswith("For native detection"):
            flow.extend([Spacer(1,10), Image(str(ROOT/"reports/generated/research-full/model_comparison.png"),width=450,height=225)])
        if block.startswith("Logistic regression with Platt"):
            flow.extend([Spacer(1,4),Image(str(ROOT/"reports/generated/research-full/calibration.png"),width=285,height=190)])
    flow.append(paragraph("Selected sources","h"))
    for ref in ["Moustafa & Slay (2015), UNSW-NB15. doi:10.1109/MilCIS.2015.7348942.",
                "Sarhan et al. (2022), Towards a Standard Feature Set for Network Intrusion Detection System Datasets. doi:10.1007/s11036-021-01843-0.",
                "Verwer & Hammerschmidt (2025), FlexFringe. doi:10.46298/lmcs-21(3:31)2025.",
                "Guo et al. (2017), On Calibration of Modern Neural Networks. ICML, PMLR 70.",
                "Gao et al. (2023), Enabling Large Language Models to Generate Text with Citations. EMNLP. doi:10.18653/v1/2023.emnlp-main.398."]:
        flow.append(paragraph(ref,"small"))
    doc=BaseDocTemplate(str(OUT),pagesize=A4,title="SENTINEL-X research report")
    doc.addPageTemplates([PageTemplate("research",[Frame(44,49,W-88,H-99,leftPadding=0,rightPadding=0)],onPage=header)])
    doc.build(flow)

if __name__=="__main__":
    main()
