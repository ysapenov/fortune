"""
Resume Parser Service

Parses PDF and DOCX resume files into structured JSON representation.
Supports extraction of: contact info, summary, experience, education, skills, certifications.
"""

import re
import io
from typing import Dict, List, Optional, Any


def parse_resume(file_content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse a resume file into structured JSON.
    
    Args:
        file_content: Raw bytes of the file
        filename: Original filename (used to detect format)
    
    Returns:
        Structured resume data dict
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        raw_text = _extract_text_from_pdf(file_content)
    elif ext in ("docx",):
        raw_text = _extract_text_from_docx(file_content)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Only PDF and DOCX are supported.")

    return _parse_text_to_structured(raw_text)


def _extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(file_content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    from docx import Document

    doc = Document(io.BytesIO(file_content))
    text_parts = []

    # Extract from paragraphs
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())

    # Extract from tables
    for table in doc.tables:
        for row in table.rows:
            row_text = []
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    row_text.append(cell_text)
            if row_text:
                text_parts.append(" | ".join(row_text))

    return "\n".join(text_parts)


def _parse_text_to_structured(text: str) -> Dict[str, Any]:
    """
    Parse raw text into structured resume JSON.
    
    Identifies sections and extracts structured fields.
    """
    result = {
        "name": "",
        "email": "",
        "phone": "",
        "location": "",
        "summary": "",
        "experience": [],
        "education": [],
        "skills": [],
        "certifications": [],
    }

    # Extract contact information
    result["email"] = _extract_email(text)
    result["phone"] = _extract_phone(text)
    result["name"] = _extract_name(text)
    result["location"] = _extract_location(text)

    # Split text into sections
    sections = _identify_sections(text)

    # Process each section
    if "summary" in sections:
        result["summary"] = sections["summary"].strip()
    elif "objective" in sections:
        result["summary"] = sections["objective"].strip()
    elif "profile" in sections:
        result["summary"] = sections["profile"].strip()

    if "experience" in sections:
        result["experience"] = _parse_experience(sections["experience"])
    elif "work experience" in sections:
        result["experience"] = _parse_experience(sections["work experience"])
    elif "professional experience" in sections:
        result["experience"] = _parse_experience(sections["professional experience"])
    elif "employment" in sections:
        result["experience"] = _parse_experience(sections["employment"])

    if "education" in sections:
        result["education"] = _parse_education(sections["education"])
    elif "academic" in sections:
        result["education"] = _parse_education(sections["academic"])

    if "skills" in sections:
        result["skills"] = _parse_skills(sections["skills"])
    elif "technical skills" in sections:
        result["skills"] = _parse_skills(sections["technical skills"])
    elif "core competencies" in sections:
        result["skills"] = _parse_skills(sections["core competencies"])

    if "certifications" in sections:
        result["certifications"] = _parse_certifications(sections["certifications"])
    elif "certificates" in sections:
        result["certifications"] = _parse_certifications(sections["certificates"])
    elif "licenses" in sections:
        result["certifications"] = _parse_certifications(sections["licenses"])

    return result


def _extract_email(text: str) -> str:
    """Extract email address from text."""
    # Match standard email pattern
    match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    """Extract phone number from text."""
    # Match various phone formats: (123) 456-7890, 123-456-7890, +1 123 456 7890, etc.
    patterns = [
        r'\+?1?\s*\(?\d{3}\)?\s*[-.\s]?\d{3}\s*[-.\s]?\d{4}',
        r'\(\d{3}\)\s*\d{3}[-.\s]\d{4}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
    return ""


def _extract_name(text: str) -> str:
    """
    Extract the candidate's name from the resume text.
    
    Heuristic: The name is typically the first non-empty line that is not
    an email, phone number, URL, or section header.
    """
    lines = text.strip().split("\n")
    for line in lines[:5]:  # Check first 5 lines
        line = line.strip()
        if not line:
            continue
        # Skip if it looks like email, phone, URL, or section header
        if re.search(r'@', line):
            continue
        if re.search(r'\d{3}[-.\s(]\d{3}', line):
            continue
        if re.search(r'https?://', line):
            continue
        if _is_section_header(line):
            continue
        # Name should be relatively short and contain mostly letters
        if len(line) < 60 and re.match(r'^[A-Za-z\s.\-,]+$', line):
            return line.strip()
    return ""


def _extract_location(text: str) -> str:
    """
    Extract location from text.
    
    Looks for city/state patterns near the top of the document.
    """
    lines = text.strip().split("\n")
    # Common US state abbreviations
    state_abbr = (
        r'AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|'
        r'MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|'
        r'SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC'
    )
    location_pattern = re.compile(
        rf'([A-Z][a-zA-Z\s]+,\s*(?:{state_abbr})(?:\s+\d{{5}})?)'
    )

    for line in lines[:10]:
        match = location_pattern.search(line)
        if match:
            return match.group(1).strip()

    # Also try "City, State" patterns
    for line in lines[:10]:
        match = re.search(r'([A-Z][a-z]+(?:\s[A-Z][a-z]+)?,\s*[A-Z]{2})', line)
        if match:
            return match.group(1).strip()

    return ""


# Section header patterns
SECTION_PATTERNS = {
    "summary": re.compile(
        r'^(?:professional\s+)?summary|^profile|^about\s+me|^objective',
        re.IGNORECASE
    ),
    "experience": re.compile(
        r'^(?:professional\s+|work\s+)?experience|^employment(?:\s+history)?|^work\s+history',
        re.IGNORECASE
    ),
    "education": re.compile(
        r'^education(?:al\s+background)?|^academic',
        re.IGNORECASE
    ),
    "skills": re.compile(
        r'^(?:technical\s+|core\s+)?skills|^core\s+competencies|^technologies|^proficiencies',
        re.IGNORECASE
    ),
    "certifications": re.compile(
        r'^certifications?|^certificates?|^licenses?\s*(?:&|and)?\s*certifications?',
        re.IGNORECASE
    ),
}


def _is_section_header(line: str) -> bool:
    """Check if a line looks like a section header."""
    clean = line.strip().rstrip(":")
    for pattern in SECTION_PATTERNS.values():
        if pattern.match(clean):
            return True
    # Also check for common non-resume section headers
    if re.match(r'^(references|projects|publications|volunteer|awards|interests|hobbies)', clean, re.IGNORECASE):
        return True
    return False


def _identify_sections(text: str) -> Dict[str, str]:
    """
    Split text into identified sections.
    
    Returns a dict mapping section name (lowercase) to its content text.
    """
    lines = text.split("\n")
    sections: Dict[str, str] = {}
    current_section: Optional[str] = None
    current_lines: List[str] = []

    # All possible section header keywords (broader set for matching)
    all_section_keywords = re.compile(
        r'^(?:professional\s+)?summary|^profile|^about\s+me|^objective|'
        r'^(?:professional\s+|work\s+)?experience|^employment|^work\s+history|'
        r'^education|^academic|'
        r'^(?:technical\s+|core\s+)?skills|^core\s+competencies|^technologies|^proficiencies|'
        r'^certifications?|^certificates?|^licenses?|'
        r'^references|^projects|^publications|^volunteer|^awards|^interests|^hobbies|'
        r'^contact(?:\s+info(?:rmation)?)?|^personal\s+info(?:rmation)?',
        re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip().rstrip(":")
        if stripped and all_section_keywords.match(stripped):
            # Save previous section
            if current_section is not None:
                sections[current_section] = "\n".join(current_lines)
            current_section = stripped.lower()
            current_lines = []
        elif current_section is not None:
            current_lines.append(line)

    # Save last section
    if current_section is not None:
        sections[current_section] = "\n".join(current_lines)

    return sections


def _parse_experience(text: str) -> List[Dict[str, str]]:
    """
    Parse experience section into structured entries.
    
    Tries to identify company, title, dates, and description for each entry.
    """
    entries = []
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    if not lines:
        return entries

    # Date pattern for matching date ranges
    date_pattern = re.compile(
        r'(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
        r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
        r'\s+\d{4}\s*[-–—to]+\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|'
        r'May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
        r'Dec(?:ember)?)\s+\d{4}|Present|Current)\b)',
        re.IGNORECASE
    )
    # Also match year-only ranges: 2020 - 2023, 2020 - Present
    year_range_pattern = re.compile(
        r'(\b\d{4}\s*[-–—to]+\s*(?:\d{4}|Present|Current)\b)',
        re.IGNORECASE
    )

    current_entry: Optional[Dict[str, str]] = None
    description_lines: List[str] = []

    for line in lines:
        # Check if this line contains a date range (signals a new entry)
        date_match = date_pattern.search(line) or year_range_pattern.search(line)

        if date_match:
            # Save previous entry
            if current_entry is not None:
                current_entry["description"] = "\n".join(description_lines).strip()
                entries.append(current_entry)

            dates = date_match.group(1).strip()
            # Remove the date from the line to get company/title
            remaining = (line[:date_match.start()] + line[date_match.end():]).strip()
            remaining = remaining.strip(" |,–—-")

            company, title = _split_company_title(remaining)

            current_entry = {
                "company": company,
                "title": title,
                "dates": dates,
                "description": "",
            }
            description_lines = []
        elif current_entry is not None:
            # If this looks like a title/company line (follows a date line)
            if not description_lines and not line.startswith(("•", "-", "*", "–", "►", "▪")):
                # Might be a second line for company/title
                if not current_entry["company"] and not current_entry["title"]:
                    company, title = _split_company_title(line)
                    current_entry["company"] = company
                    current_entry["title"] = title
                elif not current_entry["title"]:
                    current_entry["title"] = line
                else:
                    description_lines.append(line)
            else:
                # Clean bullet point prefixes
                cleaned = re.sub(r'^[•\-*–►▪]\s*', '', line)
                description_lines.append(cleaned)
        else:
            # No current entry and no date found — could be first entry without dates
            # Try to start a new entry if it looks like company/title
            if _looks_like_company_or_title(line):
                current_entry = {
                    "company": line,
                    "title": "",
                    "dates": "",
                    "description": "",
                }
                description_lines = []

    # Save last entry
    if current_entry is not None:
        current_entry["description"] = "\n".join(description_lines).strip()
        entries.append(current_entry)

    return entries


def _split_company_title(text: str) -> tuple:
    """
    Split a line into company and title components.
    Uses common separators like | , - or at/as keywords.
    """
    if not text:
        return ("", "")

    # Try splitting by common separators
    for sep in [" | ", " - ", " — ", " – ", ", "]:
        if sep in text:
            parts = text.split(sep, 1)
            return (parts[0].strip(), parts[1].strip())

    # Try "at" or "as" keywords
    match = re.match(r'(.+?)\s+(?:at|@)\s+(.+)', text, re.IGNORECASE)
    if match:
        return (match.group(2).strip(), match.group(1).strip())

    # If no separator found, treat the whole thing as company
    return (text.strip(), "")


def _looks_like_company_or_title(line: str) -> bool:
    """Heuristic to detect if a line looks like a company or job title."""
    if len(line) > 80:
        return False
    if line.startswith(("•", "-", "*", "–", "►", "▪")):
        return False
    # Contains mostly letters, possibly with some punctuation
    if re.match(r'^[A-Z]', line) and len(line.split()) <= 8:
        return True
    return False


def _parse_education(text: str) -> List[Dict[str, str]]:
    """Parse education section into structured entries."""
    entries = []
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    if not lines:
        return entries

    # Date patterns
    date_pattern = re.compile(r'(\b\d{4}\s*[-–—to]*\s*(?:\d{4}|Present|Current)?)\b', re.IGNORECASE)
    # GPA pattern
    gpa_pattern = re.compile(r'GPA[:\s]*(\d+\.?\d*(?:/\d+\.?\d*)?)', re.IGNORECASE)
    # Degree patterns
    degree_pattern = re.compile(
        r'\b(Bachelor|Master|Doctor|Ph\.?D|M\.?S\.?|B\.?S\.?|B\.?A\.?|M\.?A\.?|'
        r'M\.?B\.?A\.?|Associate|Diploma|Certificate)(?:\'?s?)?\b'
        r'(?:\s+(?:of|in)\s+[A-Za-z\s]+)?',
        re.IGNORECASE
    )

    current_entry: Optional[Dict[str, str]] = None
    extra_lines: List[str] = []

    for line in lines:
        degree_match = degree_pattern.search(line)
        has_institution_indicators = bool(re.search(
            r'\b(?:University|College|Institute|School|Academy)\b', line, re.IGNORECASE
        ))

        if degree_match or has_institution_indicators:
            # Save previous entry
            if current_entry is not None:
                if extra_lines:
                    for el in extra_lines:
                        gpa_m = gpa_pattern.search(el)
                        if gpa_m:
                            current_entry["gpa"] = gpa_m.group(1)
                entries.append(current_entry)

            # Extract date
            date_match = date_pattern.search(line)
            dates = date_match.group(1).strip() if date_match else ""

            # Extract GPA
            gpa_match = gpa_pattern.search(line)
            gpa = gpa_match.group(1) if gpa_match else ""

            # Extract degree
            degree = degree_match.group(0).strip() if degree_match else ""

            # Extract institution
            institution = ""
            if has_institution_indicators:
                # Try to get the institution name
                inst_match = re.search(
                    r'((?:[A-Z][a-zA-Z]*\s+)*(?:University|College|Institute|School|Academy)'
                    r'(?:\s+of\s+[A-Za-z\s]+)?)',
                    line
                )
                if inst_match:
                    institution = inst_match.group(1).strip()

            if not institution and not degree:
                institution = line.strip()

            current_entry = {
                "institution": institution,
                "degree": degree,
                "dates": dates,
                "gpa": gpa,
            }
            extra_lines = []
        elif current_entry is not None:
            # Additional info for current entry
            gpa_match = gpa_pattern.search(line)
            if gpa_match and not current_entry["gpa"]:
                current_entry["gpa"] = gpa_match.group(1)
            date_match = date_pattern.search(line)
            if date_match and not current_entry["dates"]:
                current_entry["dates"] = date_match.group(1).strip()
            degree_match_extra = degree_pattern.search(line)
            if degree_match_extra and not current_entry["degree"]:
                current_entry["degree"] = degree_match_extra.group(0).strip()
            if not current_entry["institution"]:
                current_entry["institution"] = line.strip()
            extra_lines.append(line)

    # Save last entry
    if current_entry is not None:
        entries.append(current_entry)

    return entries


def _parse_skills(text: str) -> List[str]:
    """Parse skills section into a list of individual skills."""
    skills = []
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    for line in lines:
        # Remove bullet prefixes
        line = re.sub(r'^[•\-*–►▪]\s*', '', line)

        # Try splitting by common delimiters
        if "," in line or ";" in line or "|" in line or "·" in line:
            # Split by comma, semicolon, pipe, or middle dot
            parts = re.split(r'[,;|·]', line)
            for part in parts:
                cleaned = part.strip()
                if cleaned and len(cleaned) < 60:
                    skills.append(cleaned)
        elif ":" in line:
            # Category: skill1, skill2, skill3
            _, _, rest = line.partition(":")
            parts = re.split(r'[,;|·]', rest)
            for part in parts:
                cleaned = part.strip()
                if cleaned and len(cleaned) < 60:
                    skills.append(cleaned)
        else:
            # Single skill per line
            if line and len(line) < 60:
                skills.append(line)

    return skills


def _parse_certifications(text: str) -> List[str]:
    """Parse certifications section into a list."""
    certs = []
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

    for line in lines:
        # Remove bullet prefixes
        line = re.sub(r'^[•\-*–►▪]\s*', '', line).strip()
        if line:
            certs.append(line)

    return certs
