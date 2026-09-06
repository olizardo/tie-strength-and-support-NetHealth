#!/usr/bin/env python3
"""
Scripts/add_methodological_clarifications.py

Surgically adds methodological clarifications regarding dyadic clustering,
LCA unit of analysis, and multilevel GLMM random intercepts into draft_live.docx,
preserving all remote styles, document defaults, paragraph formatting (<w:pPr>),
and run properties (<w:rPr>).
"""

import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
import copy

def create_styled_paragraph(text, base_pPr, base_rPr=None):
    p = ET.Element('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')
    if base_pPr is not None:
        p.append(copy.deepcopy(base_pPr))
        
    parts = re.split(r'(\*[^*]+\*)', text)
    for part in parts:
        if not part:
            continue
        r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
        is_italic = part.startswith('*') and part.endswith('*')
        clean_text = part[1:-1] if is_italic else part
        
        if base_rPr is not None:
            rPr = copy.deepcopy(base_rPr)
            i_elem = rPr.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
            if is_italic:
                if i_elem is None:
                    ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '1'})
                else:
                    i_elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = '1'
            else:
                if i_elem is not None:
                    i_elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = '0'
            r.append(rPr)
        else:
            rPr = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
            ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}vertAlign', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': 'baseline'})
            ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rtl', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '0'})
            if is_italic:
                ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
                ET.SubElement(rPr, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}iCs')
                
        t = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
        if clean_text.startswith(' ') or clean_text.endswith(' '):
            t.attrib['{http://www.w3.org/XML/1998/namespace}space'] = 'preserve'
        t.text = clean_text
        
    return p

def update_document(in_docx, out_docx):
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
    ps = list(body.findall('w:p', ns))

    # 1. Check if Section 4 clarification already exists
    all_text = "".join(body.itertext())
    clarification_text = (
        "From a methodological standpoint, the unit of analysis in this latent class model is the dyadic "
        "ego–alter tie observation (N = 22,739). Because ties are nested within respondents (N = 626), reports "
        "of social support exhibit moderate-to-substantial clustering at the ego level. Unconditional mixed-effects "
        "logistic models indicate that latent intraclass correlation coefficients (ICCs) range from 0.17 for "
        "financial aid to 0.29 for advice, 0.33 for emotional comfort, and 0.34 for companionship, showing that "
        "between 17% and 34% of the variance in support reporting is attributable to unobserved respondent-level factors. "
        "With four binary indicators, however, there are only 2^4 = 16 observable response profiles (15 degrees of freedom "
        "in the saturated multinomial table). Estimating complex multilevel mixture models with continuous random "
        "effects across this compact discrete space introduces severe empirical identification constraints. In our analytical "
        "design, we therefore use the single-level LCA strictly as an inductive, taxonomical tool to map population-averaged "
        "support configurations across dyads—substituting empirical clustering for arbitrary manual groupings. Crucially, "
        "we do not rely on the LCA for hypothesis testing or covariate evaluation; all confirmatory inference, standard "
        "errors, and predictor effects are reserved for the subsequent multilevel regression framework, where clustering "
        "within egos is explicitly modeled."
    )

    if "From a methodological standpoint, the unit of analysis in this latent class model is the dyadic ego–alter tie observation" in all_text:
        print("  [*] Section 4 methodological clarification already present.")
    else:
        # Locate paragraph P29 (four-class selection)
        target_idx = None
        for i, p in enumerate(body):
            txt = ''.join(p.itertext()).strip()
            if "Consequently, the four-class solution was selected as the optimal empirical representation" in txt:
                target_idx = i
                break

        if target_idx is not None:
            print(f"  [+] Found Section 4 target insertion anchor at body index {target_idx}")
            base_p = body[target_idx]
            base_pPr = base_p.find('w:pPr', ns)
            first_r = base_p.find('w:r', ns)
            base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None
            
            new_p = create_styled_paragraph(clarification_text, base_pPr, base_rPr)
            body.insert(target_idx + 1, new_p)
            print("  [+] Successfully inserted Section 4 methodological clarification paragraph.")
        else:
            print("  [!] Warning: Could not locate Section 4 target anchor paragraph.")

    # 2. Update Section 5 paragraph regarding random ego intercepts
    for p in body.findall('w:p', ns):
        txt = ''.join(p.itertext()).strip()
        if "Where Xij represents the vector of tie-level strength indicators" in txt or "where Xij represents the vector of tie-level strength indicators" in txt:
            if "By capturing the unobserved respondent-level variance identified above" not in txt:
                print("  [+] Surgically updating Section 5 random intercept explanation.")
                pPr = p.find('w:pPr', ns)
                first_r = p.find('w:r', ns)
                base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None
                
                # Replace text runs while preserving pPr
                p_children = list(p)
                for c in p_children:
                    if c != pPr:
                        p.remove(c)
                        
                updated_glmm_text = (
                    "Where Xij represents the vector of tie-level strength indicators (closeness, frequency, salience, "
                    "duration), role relations, and dyadic controls, β is the vector of fixed-effect coefficients, and "
                    "uj ~ N(0, σu^2) represents the ego-specific random intercept. By capturing the unobserved respondent-level "
                    "variance identified above—such as individual baseline sociability, reporting thresholds, or generalized "
                    "optimism regarding support availability—the inclusion of uj prevents standard error deflation and "
                    "ensures that hypothesis tests for tie-strength indicators and role relations properly account for the "
                    "dyadic clustering of personal networks. Table 3 presents the estimated odds ratios (ORs) and 95% confidence "
                    "intervals from these multilevel models across the four specific support exchanges."
                )
                
                # Split and add runs
                r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
                if base_rPr is not None:
                    r.append(copy.deepcopy(base_rPr))
                t_elem = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                t_elem.text = updated_glmm_text
                print("  [+] Section 5 random intercept paragraph updated successfully.")
            break

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)

    print(f"[+] Successfully wrote updated manuscript to {out_docx}")

if __name__ == '__main__':
    in_file = sys.argv[1] if len(sys.argv) > 1 else 'draft_live.docx'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'draft_updated.docx'
    update_document(in_file, out_file)
