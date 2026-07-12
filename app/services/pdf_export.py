"""
PDF Export Service

Exports interview preparation materials as professionally formatted PDFs
using the reportlab library.

Features:
- Company name and role as header
- Research summary section with proper formatting
- Questions section with numbering and answer frameworks
- Clean, printable layout
"""

import io
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


def _build_styles():
    """Build custom paragraph styles for the PDF."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6,
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontSize=14,
        spaceAfter=20,
        textColor=colors.HexColor("#16213e"),
        alignment=TA_CENTER,
    ))

    styles.add(ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor("#0f3460"),
        borderWidth=1,
        borderColor=colors.HexColor("#0f3460"),
        borderPadding=4,
    ))

    styles.add(ParagraphStyle(
        "SubSectionHeader",
        parent=styles["Heading3"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#16213e"),
    ))

    styles.add(ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        leading=14,
        alignment=TA_JUSTIFY,
    ))

    styles.add(ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=4,
        leading=13,
        leftIndent=20,
        bulletIndent=10,
    ))

    styles.add(ParagraphStyle(
        "QuestionText",
        parent=styles["Normal"],
        fontSize=11,
        spaceAfter=4,
        leading=14,
        textColor=colors.HexColor("#1a1a2e"),
        fontName="Helvetica-Bold",
    ))

    styles.add(ParagraphStyle(
        "FrameworkText",
        parent=styles["Normal"],
        fontSize=9,
        spaceAfter=10,
        leading=12,
        leftIndent=20,
        textColor=colors.HexColor("#555555"),
        fontName="Helvetica-Oblique",
    ))

    styles.add(ParagraphStyle(
        "CategoryLabel",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#888888"),
        fontName="Helvetica",
    ))

    styles.add(ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#999999"),
        alignment=TA_CENTER,
    ))

    return styles


def _escape_xml(text: str) -> str:
    """Escape special XML characters for use in reportlab Paragraphs."""
    if not text:
        return ""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def export_interview_prep_pdf(
    company_name: str,
    job_title: str,
    research_summary: str,
    questions: list,
    research_data: Optional[dict] = None,
) -> bytes:
    """
    Export interview preparation materials as a PDF.

    Args:
        company_name: Name of the company
        job_title: Title of the role
        research_summary: Formatted research summary text
        questions: List of question dicts with: question, category, framework, number
        research_data: Optional structured research data (for richer formatting)

    Returns:
        PDF file content as bytes
    """
    buffer = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story = []

    # ─── Title Page Section ───
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        f"Interview Preparation Guide",
        styles["DocTitle"],
    ))
    story.append(Paragraph(
        f"{_escape_xml(company_name)} — {_escape_xml(job_title or 'General')}",
        styles["DocSubtitle"],
    ))
    story.append(Spacer(1, 0.3 * inch))

    # ─── Company Research Section ───
    story.append(Paragraph("Company Research Summary", styles["SectionHeader"]))

    if research_data and isinstance(research_data, dict):
        # Structured format
        # Description
        desc = research_data.get("description", "")
        if desc:
            story.append(Paragraph("Company Overview", styles["SubSectionHeader"]))
            story.append(Paragraph(_escape_xml(desc), styles["BodyText2"]))

        # Products
        products = research_data.get("products", [])
        if products:
            story.append(Paragraph("Key Products &amp; Services", styles["SubSectionHeader"]))
            for product in products:
                story.append(Paragraph(
                    f"• {_escape_xml(str(product))}",
                    styles["BulletText"],
                ))

        # Culture
        culture = research_data.get("culture", "")
        if culture:
            story.append(Paragraph("Company Culture", styles["SubSectionHeader"]))
            story.append(Paragraph(_escape_xml(culture), styles["BodyText2"]))

        # Leadership
        leadership = research_data.get("leadership", [])
        if leadership:
            story.append(Paragraph("Key Leadership", styles["SubSectionHeader"]))
            for leader in leadership:
                name = leader.get("name", "Unknown")
                title = leader.get("title", "")
                story.append(Paragraph(
                    f"• {_escape_xml(name)} — {_escape_xml(title)}",
                    styles["BulletText"],
                ))

        # Recent News
        news = research_data.get("recent_news", [])
        if news:
            story.append(Paragraph("Recent News &amp; Developments", styles["SubSectionHeader"]))
            for item in news:
                story.append(Paragraph(
                    f"• {_escape_xml(str(item))}",
                    styles["BulletText"],
                ))
    else:
        # Plain text format — parse line by line
        for line in research_summary.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
            elif line.startswith("="):
                continue  # Skip header underlines
            elif line.startswith("-"):
                continue  # Skip section underlines
            elif line.startswith("•") or line.startswith("  •"):
                story.append(Paragraph(
                    _escape_xml(line.lstrip("• ")),
                    styles["BulletText"],
                ))
            elif line.isupper():
                story.append(Paragraph(line, styles["SubSectionHeader"]))
            else:
                story.append(Paragraph(_escape_xml(line), styles["BodyText2"]))

    story.append(Spacer(1, 0.3 * inch))

    # ─── Interview Questions Section ───
    story.append(Paragraph("Interview Questions", styles["SectionHeader"]))

    # Group questions by category
    categories_order = ["technical", "behavioral", "company-specific"]
    category_labels = {
        "technical": "Technical Questions",
        "behavioral": "Behavioral Questions",
        "company-specific": "Company-Specific Questions",
    }

    for cat in categories_order:
        cat_questions = [q for q in questions if q.get("category") == cat]
        if not cat_questions:
            continue

        story.append(Paragraph(
            category_labels.get(cat, cat.title()),
            styles["SubSectionHeader"],
        ))

        for q in cat_questions:
            num = q.get("number", "")
            question_text = q.get("question", "")
            framework = q.get("framework", "")

            story.append(Paragraph(
                f"Q{num}. {_escape_xml(question_text)}",
                styles["QuestionText"],
            ))

            if framework:
                story.append(Paragraph(
                    f"Answer Framework: {_escape_xml(framework)}",
                    styles["FrameworkText"],
                ))

            story.append(Spacer(1, 4))

    # Handle any questions without a recognized category
    other_questions = [
        q for q in questions
        if q.get("category") not in categories_order
    ]
    if other_questions:
        story.append(Paragraph("Additional Questions", styles["SubSectionHeader"]))
        for q in other_questions:
            num = q.get("number", "")
            question_text = q.get("question", "")
            framework = q.get("framework", "")
            story.append(Paragraph(
                f"Q{num}. {_escape_xml(question_text)}",
                styles["QuestionText"],
            ))
            if framework:
                story.append(Paragraph(
                    f"Answer Framework: {_escape_xml(framework)}",
                    styles["FrameworkText"],
                ))

    # ─── Footer ───
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(
        "Generated by Job Hunt Helper — Good luck with your interview!",
        styles["Footer"],
    ))

    # Build PDF
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
