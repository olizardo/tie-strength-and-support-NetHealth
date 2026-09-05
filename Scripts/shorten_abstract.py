#!/usr/bin/env python3
"""
Scripts/shorten_abstract.py
Surgically replaces the abstract in draft_live.docx with a concise ~190-200 word version,
preserving paragraph properties, styles, and typographic quotation marks,
and eliminating alien math markup.
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
import copy

def shorten_abstract(in_docx, out_docx):
    print(f"Opening {in_docx} to update abstract...")
    with zipfile.ZipFile(in_docx, 'r') as zin:
        xml_bytes = zin.read('word/document.xml')
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    ET.register_namespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
    ET.register_namespace('a', 'http://schemas.openxmlformats.org/drawingml/2006/main')
    ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
    ET.register_namespace('wp', 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing')
    ET.register_namespace('pic', 'http://schemas.openxmlformats.org/drawingml/2006/picture')

    doc_tree = ET.fromstring(xml_bytes)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    body = doc_tree.find('w:body', ns)
    ps = list(body.findall('w:p', ns))

    # Find Abstract heading
    abs_heading_idx = None
    for i, p in enumerate(ps):
        txt = ''.join(p.itertext()).strip()
        if txt == "Abstract":
            abs_heading_idx = i
            break

    if abs_heading_idx is None:
        raise ValueError("Could not find 'Abstract' heading in document!")

    target_p = ps[abs_heading_idx + 1]
    print(f"  [+] Found Abstract paragraph at P{abs_heading_idx + 1}")

    pPr = target_p.find('w:pPr', ns)
    first_r = target_p.find('w:r', ns)
    base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None

    # Clear old runs / math markup
    p_children = list(target_p)
    for child in p_children:
        if child != pPr:
            target_p.remove(child)

    new_abstract_text = (
        "Theories of social networks often treat tie strength as a single continuum or conflate it with role relations "
        "and resource provision. Drawing on multi-wave panel data from the NetHealth Study (N = 22,739 ego-alter tie observations "
        "across N = 626 undergraduate participants), we untangle the multidimensional structure of tie strength, social roles, "
        "and social support. First, using Latent Class Analysis across four support exchanges (companionship, advice, emotional "
        "comfort, and financial aid), we identify four distinct relational configurations: “Casual Companionship,” “Comprehensive "
        "Support,” “Instrumental / Kin Support,” and “Low / Peripheral Support.” Second, using multilevel generalized linear mixed "
        "models with random ego intercepts, we estimate the independent effects of emotional closeness, contact frequency, "
        "cognitive salience, and duration on support provision while accounting for dyadic clustering. Results show that emotional "
        "closeness and contact frequency represent distinct relational dimensions: emotional closeness strongly predicts expressive "
        "comfort and advice, whereas interaction frequency primarily drives everyday companionship. Furthermore, role relations "
        "condition support provision independently of tie strength, with family ties providing nearly all financial assistance. "
        "These findings show that personal communities are organized through a functional division of relational labor rather "
        "than an undifferentiated gradient of tie strength."
    )

    r = ET.SubElement(target_p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
    if base_rPr is not None:
        r.append(copy.deepcopy(base_rPr))
    else:
        rPr = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vertAlign', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': 'baseline'})
        ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rtl', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '0'})

    t = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
    t.attrib['{http://www.w3.org/XML/1998/namespace}space'] = 'preserve'
    t.text = new_abstract_text

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)

    print(f"[+] Successfully wrote updated manuscript with shortened abstract to {out_docx}")

if __name__ == '__main__':
    in_file = sys.argv[1] if len(sys.argv) > 1 else 'draft_live.docx'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'draft_updated.docx'
    shorten_abstract(in_file, out_file)
