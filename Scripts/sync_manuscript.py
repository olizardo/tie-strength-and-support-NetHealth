#!/usr/bin/env python3
"""
Scripts/sync_manuscript.py
DOM-based OpenXML table, figure, and style injector adhering strictly to AGENTS.md:
- In-place XML injection preserving live styles, paragraph hierarchies, and page breaks
- 6.5-inch full printable text width scaling (9360 dxa / 5,943,600 EMUs)
- Dual DrawingML extent synchronization (cx, cy)
- Mandatory XML escaping and strict ECMA-376 tag ordering
- Universal APA 7th table standards (no vertical borders, 1pt top/bottom, 0.5pt header-bottom)
- Elimination of slashes in support type names (single terms: Companionship, Advice, Comfort, Financial)
- Elimination of office math (<m:oMath>) format, rendering variables/equations in native normal text
- Harmonization of NetHealth Study description and references with sibling projects
- Bolded, unindented table and figure captions following local normal text font
- Bolded preferred model row in Table 1 (4 Classes)
"""

import os
import re
import sys
import glob
import zipfile
import struct
import xml.etree.ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

ET.register_namespace('w', W_NS)
ET.register_namespace('m', M_NS)
ET.register_namespace('r', R_NS)
ET.register_namespace('wp', WP_NS)
ET.register_namespace('a', A_NS)

def xml_escape(s):
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def get_png_dimensions(image_path):
    with open(image_path, "rb") as f:
        data = f.read(24)
        if len(data) >= 24 and data.startswith(b'\x89PNG\r\n\x1a\n'):
            return struct.unpack('>II', data[16:24])
    return 1950, 1200

def parse_markdown_table(file_path):
    if not os.path.exists(file_path):
        return [], []
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]
    if len(table_lines) < 3: return [], []
    headers = [c.strip() for c in table_lines[0].strip("|").split("|")]
    rows = []
    for line in table_lines[2:]:
        row = [c.strip() for c in line.strip("|").split("|")]
        rows.append(row)
    return headers, rows

def create_apa_table_xml(headers, rows_data, col_widths=None):
    total_w = 9360  # 6.5 in portrait width in dxa
    num_cols = len(headers)
    if col_widths is None:
        col1_w = int(total_w * 0.38)
        rem_w = total_w - col1_w
        sub_w = int(rem_w / (num_cols - 1)) if num_cols > 1 else rem_w
        col_widths = [col1_w] + [sub_w] * (num_cols - 2)
        if num_cols > 1:
            col_widths.append(total_w - sum(col_widths))
        else:
            col_widths = [total_w]

    xml = [f'<w:tbl xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:tblPr><w:tblW w:w="{total_w}" w:type="dxa"/><w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="000000"/><w:left w:val="none"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="000000"/><w:right w:val="none"/><w:insideH w:val="none"/><w:insideV w:val="none"/></w:tblBorders><w:tblCellMar><w:top w:w="120" w:type="dxa"/><w:bottom w:w="120" w:type="dxa"/><w:left w:w="160" w:type="dxa"/><w:right w:w="160" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>']
    for w in col_widths: xml.append(f'<w:gridCol w:w="{w}"/>')
    xml.append('</w:tblGrid>')
    
    # Header Row
    xml.append('<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>')
    for i, h in enumerate(headers):
        align = "left" if i == 0 else "center"
        escaped_h = xml_escape(h)
        xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_widths[i]}" w:type="dxa"/><w:tcBorders><w:bottom w:val="single" w:sz="4" w:space="0" w:color="000000"/></w:tcBorders><w:noWrap/></w:tcPr><w:p><w:pPr><w:suppressAutoHyphens/><w:spacing w:before="0" w:after="0"/><w:ind w:left="0" w:right="0" w:firstLine="0" w:hanging="0"/><w:jc w:val="{align}"/></w:pPr><w:r><w:rPr><w:b/></w:rPr><w:t>{escaped_h}</w:t></w:r></w:p></w:tc>')
    xml.append('</w:tr>')
    
    # Data Rows
    for row in rows_data:
        is_panel = len(row) > 0 and row[0].startswith("**Panel")
        xml.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>')
        if is_panel:
            raw_text = row[0].replace("**", "").strip()
            escaped_text = xml_escape(raw_text)
            xml.append(f'<w:tc><w:tcPr><w:gridSpan w:val="{num_cols}"/><w:tcW w:w="{total_w}" w:type="dxa"/><w:noWrap/></w:tcPr><w:p><w:pPr><w:suppressAutoHyphens/><w:spacing w:before="60" w:after="20"/><w:ind w:left="0" w:right="0" w:firstLine="0" w:hanging="0"/><w:jc w:val="left"/></w:pPr><w:r><w:rPr><w:b/><w:i/></w:rPr><w:t>{escaped_text}</w:t></w:r></w:p></w:tc>')
        else:
            for i, val in enumerate(row):
                w_idx = min(i, len(col_widths) - 1)
                align = "left" if i == 0 else "center"
                clean_val = val.replace("&nbsp;", " ")
                indent_dxa = 140 if clean_val.startswith("  ") or clean_val.startswith(" ") else 0
                clean_val = clean_val.strip()
                is_bold = clean_val.startswith("**") and clean_val.endswith("**")
                if is_bold:
                    clean_val = clean_val[2:-2].strip()
                escaped_val = xml_escape(clean_val)
                bold_tag = "<w:rPr><w:b/></w:rPr>" if is_bold else ""
                xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_widths[w_idx]}" w:type="dxa"/><w:noWrap/></w:tcPr><w:p><w:pPr><w:suppressAutoHyphens/><w:spacing w:before="0" w:after="0"/><w:ind w:left="{indent_dxa}" w:right="0" w:firstLine="0" w:hanging="0"/><w:jc w:val="{align}"/></w:pPr><w:r>{bold_tag}<w:t>{escaped_val}</w:t></w:r></w:p></w:tc>')
        xml.append('</w:tr>')
    xml.append('</w:tbl>')
    return "".join(xml)

def generate_table_xmls():
    tables = {}
    h1, r1 = parse_markdown_table("cache/table1_lca_fit.md")
    if h1:
        tables["Table 1"] = create_apa_table_xml(h1, r1, [2200, 1600, 1000, 1500, 1500, 1560])
        
    h2, r2 = parse_markdown_table("cache/table2_lca_crosstabs.md")
    if h2:
        tables["Table 2"] = create_apa_table_xml(h2, r2, [2960, 1600, 1600, 1600, 1600])
        
    h3, r3 = parse_markdown_table("cache/table3_glmm_models.md")
    if h3:
        tables["Table 3"] = create_apa_table_xml(h3, r3, [3360, 1500, 1500, 1500, 1500])
        
    return tables

def format_math_text(text):
    t = text.strip()
    if "logitPYij=1=β0+Xijβ+uj" in t or "logit" in t and "uj" in t:
        return "logit(P(Y_ij = 1)) = β_0 + X_ij β + u_j"
    
    t = re.sub(r'95%\s*CI\s*([0-9\.]+),([0-9\.]+)', r'95% CI [\1, \2]', t)
    t = re.sub(r'\bN=([0-9,]+)', r'N = \1', t)
    t = re.sub(r'\bK=([0-9]+)', r'K = \1', t)
    t = re.sub(r'\bOR=([0-9\.]+)', r'OR = \1', t)
    t = re.sub(r'\bp<([0-9\.]+)', r'p < \1', t)
    t = re.sub(r'\bp=([0-9\.]+)', r'p = \1', t)
    t = re.sub(r'ΔAIC=−?([0-9,\.]+)', r'ΔAIC = −\1', t)
    t = re.sub(r'ΔBIC=−?([0-9,\.]+)', r'ΔBIC = −\1', t)
    t = re.sub(r'\bAIC=([0-9,\.]+)', r'AIC = \1', t)
    t = re.sub(r'\bBIC=([0-9,\.]+)', r'BIC = \1', t)
    if t == "Yij": return "Y_ij"
    return t

def convert_omath_to_text_runs(parent):
    for omathpara in list(parent.findall(f".//{{{M_NS}}}oMathPara")):
        raw_text = "".join(omathpara.itertext())
        clean_text = format_math_text(raw_text)
        r_elem = ET.Element(f"{{{W_NS}}}r")
        t_elem = ET.SubElement(r_elem, f"{{{W_NS}}}t")
        t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t_elem.text = clean_text
        
        for p in parent.findall(f".//{{{W_NS}}}p"):
            for child in list(p):
                if child == omathpara:
                    idx = list(p).index(child)
                    p.remove(child)
                    p.insert(idx, r_elem)
                    break

    for p in parent.findall(f".//{{{W_NS}}}p"):
        for child in list(p):
            if child.tag == f"{{{M_NS}}}oMath":
                raw_text = "".join(child.itertext())
                clean_text = format_math_text(raw_text)
                r_elem = ET.Element(f"{{{W_NS}}}r")
                t_elem = ET.SubElement(r_elem, f"{{{W_NS}}}t")
                t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                t_elem.text = clean_text
                idx = list(p).index(child)
                p.remove(child)
                p.insert(idx, r_elem)

def strip_alien_rfonts(p):
    for r in p.findall(f".//{{{W_NS}}}r"):
        rPr = r.find(f"{{{W_NS}}}rPr")
        if rPr is not None:
            rFonts = rPr.find(f"{{{W_NS}}}rFonts")
            if rFonts is not None:
                rPr.remove(rFonts)

def clean_paragraph_text_slashes(p):
    runs = p.findall(f".//{{{W_NS}}}r")
    for r in runs:
        t = r.find(f"{{{W_NS}}}t")
        if t is not None and t.text:
            text = t.text
            text = text.replace("Instrumental / Kin Support", "Instrumental Support")
            text = text.replace("Instrumental / Kin", "Instrumental")
            text = text.replace("Low / Peripheral Support", "Peripheral Support")
            text = text.replace("Low / Peripheral", "Peripheral")
            text = text.replace("hanging out/companionship", "companionship")
            text = text.replace("hanging out / companionship", "companionship")
            text = text.replace("companionship / hanging out", "companionship")
            text = text.replace("advice / informational support", "advice")
            text = text.replace("advice / information", "advice")
            text = text.replace("emotional comfort / support", "comfort")
            text = text.replace("comfort / emotional support", "comfort")
            text = text.replace("comfort or emotional support", "comfort")
            text = text.replace("advice or informational support", "advice")
            text = text.replace("companionship or hanging out", "companionship")
            t.text = text

def sync_docx(in_docx, out_docx):
    with zipfile.ZipFile(in_docx, "r") as zin:
        xml_bytes = zin.read("word/document.xml")
        rels_bytes = zin.read("word/_rels/document.xml.rels")
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    # Ensure [Content_Types].xml includes png
    if '[Content_Types].xml' in all_files:
        ct = all_files['[Content_Types].xml'].decode('utf-8')
        if 'Extension="png"' not in ct:
            ct = ct.replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')
            all_files['[Content_Types].xml'] = ct.encode('utf-8')

    root_rels = ET.fromstring(rels_bytes)
    rid_to_target = {e.get('Id'): e.get('Target') for e in root_rels if e.get('Id')}

    fig1_path = "Plots/fig1_lca_support_profiles.png"
    fig2_path = "Plots/fig2_glmm_odds_ratios.png"
    
    if os.path.exists(fig1_path) and "word/media/image2.png" in all_files:
        with open(fig1_path, "rb") as f:
            all_files["word/media/image2.png"] = f.read()
        print("  [+] Updated word/media/image2.png with latest Figure 1")
        
    if os.path.exists(fig2_path) and "word/media/image1.png" in all_files:
        with open(fig2_path, "rb") as f:
            all_files["word/media/image1.png"] = f.read()
        print("  [+] Updated word/media/image1.png with latest Figure 2")

    doc_tree = ET.fromstring(xml_bytes)
    body = doc_tree.find(f"{{{W_NS}}}body")

    print("[1/6] Converting Office Math (<m:oMath>) elements to standard text runs...")
    convert_omath_to_text_runs(body)

    print("[2/6] Stripping alien font overrides and cleaning slashes from text...")
    for p in body.findall(f".//{{{W_NS}}}p"):
        strip_alien_rfonts(p)
        clean_paragraph_text_slashes(p)

    print("[3/6] Synchronizing DrawingML extents for figures...")
    for elem in body.findall(f".//{{{W_NS}}}drawing"):
        blip = elem.find(f".//{{{A_NS}}}blip")
        if blip is not None:
            rid = blip.attrib.get(f"{{{R_NS}}}embed")
            img_path = None
            if rid == "rId6" and os.path.exists(fig1_path):
                img_path = fig1_path
            elif rid == "rId7" and os.path.exists(fig2_path):
                img_path = fig2_path
                
            if img_path:
                pw, ph = get_png_dimensions(img_path)
                cx = 5943600  # 6.5 in portrait width in EMUs
                cy = int(round(5943600 * (ph / pw)))
                for wp_ext in elem.findall(f".//{{{WP_NS}}}extent"):
                    wp_ext.set("cx", str(cx))
                    wp_ext.set("cy", str(cy))
                for a_ext in elem.findall(f".//{{{A_NS}}}ext"):
                    a_ext.set("cx", str(cx))
                    a_ext.set("cy", str(cy))
                print(f"  [+] Synchronized extents for {rid} ({img_path}): {cx}x{cy} EMUs")

    print("[4/6] Updating tables in-place (with preferred model bolding)...")
    tables = generate_table_xmls()
    body_list = list(body)
    for i, elem in enumerate(body_list):
        text = ''.join(elem.itertext()).strip()
        for t_idx, (t_key, t_xml) in enumerate(tables.items(), 1):
            tag = f"{{{{TABLE_{t_idx}}}}}"
            if tag in text:
                new_tbl = ET.fromstring(t_xml)
                idx = list(body).index(elem)
                body.remove(elem)
                body.insert(idx, new_tbl)
                print(f"  [+] Injected {t_key} at tag {tag}")
                break
                
        for caption_key, tbl_xml in tables.items():
            if text.startswith(caption_key) or f'{caption_key}:' in text or f'{caption_key}.' in text:
                for j in range(i + 1, min(len(body_list), i + 6)):
                    sibling = body_list[j]
                    if sibling.tag.endswith('tbl'):
                        new_tbl_elem = ET.fromstring(tbl_xml)
                        idx_in_body = list(body).index(sibling)
                        body.remove(sibling)
                        body.insert(idx_in_body, new_tbl_elem)
                        print(f"  [+] Updated {caption_key} sibling table")
                        break

    print("[5/6] Updating NetHealth Study description and references...")
    for p in body.findall(f".//{{{W_NS}}}p"):
        p_text = "".join(p.itertext()).strip()
        if "The empirical data for this study come from the NetHealth Study" in p_text:
            for child in list(p):
                if child.tag != f"{{{W_NS}}}pPr":
                    p.remove(child)
            new_text = (
                "The empirical data for this study come from the NetHealth Study (e.g., Liu et al., 2018; "
                "Sepulvado et al., 2020; Wang et al., 2020), a longitudinal investigation tracking an entire "
                "undergraduate cohort at the University of Notre Dame from matriculation in August 2015 through "
                "graduation in May 2019. The NetHealth study was designed to investigate the reciprocal "
                "co-evolution of social network structures, health behaviors (physical activity, sleep patterns, "
                "stress), and academic performance. Ego-network surveys were administered online via Qualtrics "
                "at the beginning and conclusion of each semester across repeated waves between Fall 2015 and Spring 2018."
            )
            r = ET.SubElement(p, f"{{{W_NS}}}r")
            t = ET.SubElement(r, f"{{{W_NS}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = new_text
            print("  [+] Updated NetHealth overview paragraph")

        elif "In each survey wave, participants completed an egocentric network module using a standardized name generator" in p_text:
            for child in list(p):
                if child.tag != f"{{{W_NS}}}pPr":
                    p.remove(child)
            new_text = (
                "The survey used a standardized open-ended name-generator approach, asking respondents to name "
                "up to 20 individuals with whom they communicated or interacted: “We would like to know who you "
                "consider to be in your social network. In the spaces below please list up to 20 people with whom "
                "you spend time communicating or interacting.” Beginning in Wave 3, respondents could additionally "
                "retain up to five alters from the preceding wave, allowing for up to 25 named alters per wave."
            )
            r = ET.SubElement(p, f"{{{W_NS}}}r")
            t = ET.SubElement(r, f"{{{W_NS}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = new_text
            print("  [+] Updated Name Generator description paragraph")

        elif "Following name generation, respondents completed detailed name interpreters" in p_text:
            for child in list(p):
                if child.tag != f"{{{W_NS}}}pPr":
                    p.remove(child)
            new_text = (
                "Following name generation, respondents completed detailed name interpreters for each listed alter, "
                "recording demographic attributes, relationship type, emotional closeness, contact frequency, "
                "relationship duration, and residential proximity. Crucially, across Waves 2, 3, 4, 5, 7, and 8, "
                "respondents were administered a dedicated social support module inquiring whether each nominated alter "
                "had provided four specific forms of assistance over the preceding months: (1) companionship, denoting "
                "time spent socializing outside formal obligations; (2) advice, representing guidance regarding personal "
                "or academic matters; (3) comfort, reflecting empathy, reassurance, or sympathetic listening during stressful "
                "periods; and (4) financial, encompassing money, loans, or emergency material aid. For participants who "
                "were administered the support battery, unendorsed items represent the documented absence of that support "
                "type. We restricted the analytical sample to egos who completed the support module in each respective wave "
                "and eliminated records with incomplete covariate data. The final analytical sample consists of N = 22,739 "
                "ego-alter tie observations nested within N = 626 unique respondents across the six support-administered waves."
            )
            r = ET.SubElement(p, f"{{{W_NS}}}r")
            t = ET.SubElement(r, f"{{{W_NS}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = new_text
            print("  [+] Updated Types of Support description paragraph")

    # References in alphabetical order
    ref_heading_idx = None
    body_list = list(body)
    for i, elem in enumerate(body_list):
        text = "".join(elem.itertext()).strip()
        if text == "References":
            ref_heading_idx = i
            break

    if ref_heading_idx is not None:
        existing_ref_elems = []
        for elem in body_list[ref_heading_idx + 1:]:
            t = "".join(elem.itertext()).strip()
            if t:
                existing_ref_elems.append(elem)

        for elem in existing_ref_elems:
            body.remove(elem)

        all_ref_texts = ["".join(e.itertext()).strip() for e in existing_ref_elems]
        new_refs = [
            ("Liu, S., Hachen, D., Lizardo, O., Poellabauer, C., Striegel, A., & Milenković, T. (2018). "
             "Network analysis of the NetHealth data: Exploring co-evolution of individuals’ social network positions "
             "and physical activities. Applied Network Science, 3(1), 45. https://doi.org/10.1007/s41109-018-0103-2"),
            ("Sepulvado, B., Wood, M., Wang, C., Fridmanski, E., Chandler, M., Lizardo, O., & Hachen, D. (2020). "
             "Predicting homophily and social network connectivity from dyadic behavioral similarity trajectory clusters. "
             "Social Science Computer Review, 40(1), 186–205. https://doi.org/10.1177/0894439320923123"),
            ("Wang, C., Lizardo, O., & Hachen, D. S. (2020). "
             "Neither influence nor selection: Examining co-evolution of political orientation and social networks in the "
             "NetSense and NetHealth studies. PLOS ONE, 15(5), e0233458. https://doi.org/10.1371/journal.pone.0233458")
        ]

        for nr in new_refs:
            key = nr.split("(")[0].strip()
            if not any(key in art for art in all_ref_texts):
                all_ref_texts.append(nr)

        all_ref_texts.sort()

        for ref_str in all_ref_texts:
            new_p = ET.Element(f"{{{W_NS}}}p")
            pPr = ET.SubElement(new_p, f"{{{W_NS}}}pPr")
            ET.SubElement(pPr, f"{{{W_NS}}}ind", {
                f"{{{W_NS}}}left": "720",
                f"{{{W_NS}}}hanging": "720"
            })
            ET.SubElement(pPr, f"{{{W_NS}}}spacing", {
                f"{{{W_NS}}}before": "60",
                f"{{{W_NS}}}after": "120"
            })
            r = ET.SubElement(new_p, f"{{{W_NS}}}r")
            t = ET.SubElement(r, f"{{{W_NS}}}t")
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            t.text = ref_str
            body.append(new_p)

    print("[6/6] Formatting captions (bolded, unindented, native normal font)...")
    for p in body.findall(f".//{{{W_NS}}}p"):
        p_text = "".join(p.itertext()).strip()
        is_caption = any(p_text.startswith(prefix) for prefix in [
            "Table 1.", "Table 2.", "Table 3.", "Figure 1.", "Figure 2."
        ])
        if is_caption:
            pPr = p.find(f"{{{W_NS}}}pPr")
            if pPr is None:
                pPr = ET.Element(f"{{{W_NS}}}pPr")
                p.insert(0, pPr)
            
            for old_ind in pPr.findall(f"{{{W_NS}}}ind"):
                pPr.remove(old_ind)
            ET.SubElement(pPr, f"{{{W_NS}}}ind", {
                f"{{{W_NS}}}left": "0",
                f"{{{W_NS}}}right": "0",
                f"{{{W_NS}}}firstLine": "0",
                f"{{{W_NS}}}hanging": "0"
            })
            
            jc = pPr.find(f"{{{W_NS}}}jc")
            if jc is None:
                jc = ET.SubElement(pPr, f"{{{W_NS}}}jc")
            jc.set(f"{{{W_NS}}}val", "left")

            spacing = pPr.find(f"{{{W_NS}}}spacing")
            if spacing is None:
                spacing = ET.SubElement(pPr, f"{{{W_NS}}}spacing")
            spacing.set(f"{{{W_NS}}}before", "120")
            spacing.set(f"{{{W_NS}}}after", "60")

            for r in p.findall(f".//{{{W_NS}}}r"):
                rPr = r.find(f"{{{W_NS}}}rPr")
                if rPr is None:
                    rPr = ET.SubElement(r, f"{{{W_NS}}}rPr")
                for rf in rPr.findall(f"{{{W_NS}}}rFonts"):
                    rPr.remove(rf)
                b = rPr.find(f"{{{W_NS}}}b")
                if b is None:
                    ET.SubElement(rPr, f"{{{W_NS}}}b")

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)

    print(f"Synchronization successfully saved to {out_docx}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        sync_docx(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python3 sync_manuscript.py <in_docx> <out_docx>")
