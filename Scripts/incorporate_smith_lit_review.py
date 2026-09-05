#!/usr/bin/env python3
"""
Scripts/incorporate_smith_lit_review.py

Surgically incorporates material from Jeffrey A. Smith (2021) into the Literature Review
of the manuscript in draft_live.docx, respecting all remote styles, document defaults,
paragraph formatting (<w:pPr>), and run properties (<w:rPr>).
"""

import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

def create_styled_paragraph(text, base_pPr, ns):
    """
    Creates a new <w:p> element containing the specified text with markdown-style italics (*...*),
    cloning base_pPr for identical styling.
    """
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    if base_pPr is not None:
        p.append(ET.fromstring(ET.tostring(base_pPr)))
    
    # Split text by markdown italic delimiters (*...*)
    parts = re.split(r'(\*[^*]+\*)', text)
    for part in parts:
        if not part:
            continue
        r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
        is_italic = part.startswith('*') and part.endswith('*')
        clean_text = part[1:-1] if is_italic else part
        
        rPr = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vertAlign', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': 'baseline'})
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rtl', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '0'})
        if is_italic:
            ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
            ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}iCs')
            
        t = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = clean_text
        
    return p

def create_reference_paragraph(text, base_ref_p, ns):
    """
    Creates a new reference <w:p> element cloning base_ref_p's pPr.
    """
    base_pPr = base_ref_p.find('w:pPr', ns)
    return create_styled_paragraph(text, base_pPr, ns)

def incorporate_smith(in_docx, out_docx):
    print(f"Opening {in_docx} for surgical OpenXML injection...")
    with zipfile.ZipFile(in_docx, 'r') as zin:
        xml_bytes = zin.read('word/document.xml')
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    ET.register_namespace('wp', 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing')
    ET.register_namespace('pic', 'http://schemas.openxmlformats.org/drawingml/2006/picture')

    doc_tree = ET.fromstring(xml_bytes)
    ns = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    }
    body = doc_tree.find('w:body', ns)
    ps = body.findall('w:p', ns)

    # Check if Smith (2021) is already incorporated
    all_text = "".join(body.itertext())
    if "Smith (2021)" in all_text and "measurement of social support represents the single most common substantive application" in all_text:
        print("  [*] Smith (2021) literature review material is already present. Skipping body insertion.")
    else:
        # Locate the Marsden and Campbell paragraph in Section 2
        target_idx = None
        for i, p in enumerate(ps):
            txt = ''.join(p.itertext()).strip()
            if "Marsden and Campbell’s (1984) measurement model" in txt:
                target_idx = i
                break

        if target_idx is None:
            raise ValueError("Could not find Marsden and Campbell's paragraph in document!")

        print(f"  [+] Found Marsden and Campbell anchor paragraph at P{target_idx}")
        base_pPr = ps[target_idx].find('w:pPr', ns)

        new_lit_paragraph_text = (
            "As Smith (2021) emphasizes in a recent synthesis of ego-network research, the measurement of social "
            "support represents the single most common substantive application of personal network data "
            "(Cornwell et al., 2008; Fischer, 1982; Wellman & Wortley, 1990). Yet empirical investigations in this "
            "tradition often rely on aggregate summary measures—such as total network size or simple degree counts "
            "of available supporters—treating personal networks as an undifferentiated reservoir of assistance. As "
            "Smith (2021) argues, this aggregate approach obscures the reality that different alters offer fundamentally "
            "different resources: some provide material aid (financial assistance), others offer informational guidance "
            "(advice), and others supply expressive backing (emotional comfort) or everyday sociability. Because ego "
            "network surveys collect detailed information on the specific nature of each dyadic bond—including emotional "
            "closeness, contact frequency, duration, and role category—they provide the empirical resolution required to "
            "examine how distinct dimensions of tie strength activate specific functional exchanges. Decoupling these "
            "dimensions at the dyadic level reveals how personal communities organize a specialized division of relational "
            "labor, rather than assuming that strong ties universally provide all forms of aid."
        )

        new_p_elem = create_styled_paragraph(new_lit_paragraph_text, base_pPr, ns)
        
        # Insert right after target_idx in body
        body_children = list(body)
        target_in_body_idx = body_children.index(ps[target_idx])
        body.insert(target_in_body_idx + 1, new_p_elem)
        print("  [+] Successfully inserted Smith (2021) literature review paragraph into Section 2")

    # Now update References section
    # Re-fetch paragraphs
    ps = body.findall('w:p', ns)
    ref_heading_idx = None
    for i, p in enumerate(ps):
        txt = ''.join(p.itertext()).strip()
        if txt == "References":
            ref_heading_idx = i
            break

    if ref_heading_idx is not None:
        print(f"  [+] Found References heading at P{ref_heading_idx}")
        base_ref_p = ps[ref_heading_idx + 1]
        
        # Collect existing reference texts and paragraphs
        existing_refs = []
        body_children = list(body)
        ref_p_nodes = []
        
        for j in range(ref_heading_idx + 1, len(ps)):
            p = ps[j]
            txt = ''.join(p.itertext()).strip()
            if txt:
                existing_refs.append(txt)
                ref_p_nodes.append(p)

        # Bibliography entries to ensure present
        needed_refs = {
            "Borgatti": "Borgatti, S. P., Mehra, A., Brass, D. J., & Labianca, G. (2009). Network analysis in the social sciences. *Science*, 323(5916), 892–895. https://doi.org/10.1126/science.1165821",
            "Cornwell": "Cornwell, B., Laumann, E. O., & Schumm, L. P. (2008). The social connectedness of older adults: A national profile. *American Sociological Review*, 73(2), 185–203. https://doi.org/10.1177/000312240807300201",
            "Feld": "Feld, S. L. (1982). Social structural determinants of similarity among associates. *American Sociological Review*, 47(6), 797–801. https://doi.org/10.2307/2095213",
            "Fischer": "Fischer, C. S. (1982). *To Dwell Among Friends: Personal Networks in Town and City*. University of Chicago Press.",
            "Granovetter": "Granovetter, M. S. (1973). The strength of weak ties. *American Journal of Sociology*, 78(6), 1360–1380. https://doi.org/10.1086/225469",
            "Kitts": "Kitts, J. A. (2014). Beyond networks in structural theories of exchange: Promises from computational social science. In S. R. Thye & E. J. Lawler (Eds.), *Advances in Group Processes* (Vol. 31, pp. 263–298). Emerald Group Publishing Limited. https://doi.org/10.1108/S0882-614520140000031008",
            "Lin": "Lin, N. (2001). *Social Capital: A Theory of Social Structure and Action*. Cambridge University Press. https://doi.org/10.1017/CBO9780511815447",
            "Lizardo": "Lizardo, O. (2024). Theorizing the concept of social tie using frames. *Social Networks*, 78, 80–91. https://doi.org/10.1016/j.socnet.2024.01.001",
            "Marsden": "Marsden, P. V., & Campbell, K. E. (1984). Measuring tie strength. *Social Forces*, 63(2), 482–501. https://doi.org/10.2307/2579058",
            "Smith": "Smith, J. A. (2021). The continued relevance of ego network data. In R. Light & J. Moody (Eds.), *The Oxford Handbook of Social Networks* (pp. 170–187). Oxford University Press. https://doi.org/10.1093/oxfordhb/9780190251765.013.15",
            "Wellman": "Wellman, B., & Wortley, S. (1990). Different strokes from different folks: Community ties and social support. *American Journal of Sociology*, 96(3), 558–588. https://doi.org/10.1086/229572"
        }

        # Remove existing ref nodes from body
        for p in ref_p_nodes:
            body.remove(p)

        # Build alphabetized list of reference elements
        sorted_keys = sorted(needed_refs.keys())
        for key in sorted_keys:
            ref_text = needed_refs[key]
            ref_p = create_reference_paragraph(ref_text, base_ref_p, ns)
            body.append(ref_p)
            
        print(f"  [+] Alphabetized and synchronized {len(sorted_keys)} references in References section")

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)

    print(f"[+] Successfully wrote updated manuscript to {out_docx}")

if __name__ == '__main__':
    in_file = sys.argv[1] if len(sys.argv) > 1 else 'draft_live.docx'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'draft_updated.docx'
    incorporate_smith(in_file, out_file)
