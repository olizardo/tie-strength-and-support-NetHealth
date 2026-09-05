#!/usr/bin/env python3
"""
Scripts/sync_manuscript.py
DOM-based OpenXML table & figure injector adhering strictly to AGENTS.md:
- In-place XML injection preserving live styles, paragraph hierarchies, and page breaks
- 6.5-inch full printable text width scaling (9360 dxa / 5,943,600 EMUs)
- Dual DrawingML extent synchronization (cx, cy)
- Mandatory XML escaping and strict ECMA-376 tag ordering
- Universal APA 7th table standards (no vertical borders, 1pt top/bottom, 0.5pt header-bottom)
"""

import os
import re
import sys
import glob
import zipfile
import struct
import xml.etree.ElementTree as ET

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
                escaped_val = xml_escape(clean_val.strip())
                xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{col_widths[w_idx]}" w:type="dxa"/><w:noWrap/></w:tcPr><w:p><w:pPr><w:suppressAutoHyphens/><w:spacing w:before="0" w:after="0"/><w:ind w:left="{indent_dxa}" w:right="0" w:firstLine="0" w:hanging="0"/><w:jc w:val="{align}"/></w:pPr><w:r><w:t>{escaped_val}</w:t></w:r></w:p></w:tc>')
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
    ns_rels = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
    rid_to_target = {e.get('Id'): e.get('Target') for e in root_rels if e.get('Id')}

    figure_map = {
        "Figure 1.": "Plots/fig1_lca_support_profiles.png",
        "Figure 2.": "Plots/fig2_glmm_odds_ratios.png"
    }

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

    # 1. Update Figures in-place & synchronize DrawingML extents to 6.5 in
    body_list = list(body)
    for i, elem in enumerate(body_list):
        text = ''.join(elem.itertext()).strip()
        for fig_caption, img_path in figure_map.items():
            if text.startswith(fig_caption):
                pw, ph = get_png_dimensions(img_path)
                cx = 5943600  # 6.5 inches portrait width in EMUs
                cy = int(round(5943600 * (ph / pw)))
                
                # Search up to 3 paragraphs before/after for the drawing
                for offset in range(-2, 4):
                    idx = i + offset
                    if 0 <= idx < len(body_list):
                        cand = body_list[idx]
                        blips = cand.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                        if blips:
                            for blip in blips:
                                rid = blip.attrib.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                if rid and rid in rid_to_target:
                                    target_media = "word/" + rid_to_target[rid]
                                    with open(img_path, "rb") as f_img:
                                        all_files[target_media] = f_img.read()
                                    
                                    for wp_ext in cand.findall('.//wp:extent', ns):
                                        wp_ext.set('cx', str(cx))
                                        wp_ext.set('cy', str(cy))
                                    for a_ext in cand.findall('.//a:ext', ns):
                                        a_ext.set('cx', str(cx))
                                        a_ext.set('cy', str(cy))
                                    print(f"  [+] Injected {img_path} for '{fig_caption}' ({cx}x{cy} EMUs)")
                            break

    # 2. Update/Inject Tables in-place (Replace {{TABLE_X}} or adjacent table)
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
                
        # Also check caption-anchored replacement if table sibling exists
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

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        sync_docx(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python3 sync_manuscript.py <in_docx> <out_docx>")
