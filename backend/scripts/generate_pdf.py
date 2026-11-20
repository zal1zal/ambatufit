import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

def md_to_pdf(md_file: str, pdf_file: str):
    with open(md_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    doc = SimpleDocTemplate(
        pdf_file,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#147D75'),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#08685F'),
        spaceBefore=14,
        spaceAfter=6,
    )
    h3_style = ParagraphStyle(
        'Heading3Custom',
        parent=styles['Heading3'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#15263B'),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=4,
    )
    code_style = ParagraphStyle(
        'CodeCustom',
        parent=styles['Code'],
        fontSize=7.5,
        leading=9.5,
        fontName='Courier',
        textColor=colors.HexColor('#1A202C'),
        backColor=colors.HexColor('#EDF2F7'),
        spaceBefore=4,
        spaceAfter=6,
    )

    story = []
    in_code_block = False
    code_buffer = []

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                block_text = "".join(code_buffer)
                story.append(Preformatted(block_text, code_style))
                story.append(Spacer(1, 4))
                code_buffer = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_buffer.append(line)
            continue

        if not stripped:
            story.append(Spacer(1, 3))
            continue

        # Headers
        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], title_style))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], h2_style))
        elif stripped.startswith("### "):
            story.append(Paragraph(stripped[4:], h3_style))
        elif stripped.startswith("---"):
            story.append(Spacer(1, 6))
        elif stripped.startswith("|"):
            # Table line
            # Simple handling for markdown tables
            story.append(Paragraph(stripped.replace("|", " | "), body_style))
        elif stripped.startswith("- "):
            story.append(Paragraph(f"&bull; {stripped[2:]}", body_style))
        else:
            # Clean strong / bold tags for reportlab
            clean_line = stripped.replace("**", "<b>", 1)
            while "**" in clean_line:
                clean_line = clean_line.replace("**", "</b>", 1)
                if "**" in clean_line:
                    clean_line = clean_line.replace("**", "<b>", 1)
            story.append(Paragraph(clean_line, body_style))

    doc.build(story)
    print(f"PDF generated successfully at {pdf_file}")

if __name__ == "__main__":
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(backend_dir, "README.md")
    pdf_path = os.path.join(backend_dir, "README.pdf")
    md_to_pdf(md_path, pdf_path)

