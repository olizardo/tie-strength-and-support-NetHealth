#!/usr/bin/env python3
"""
Scripts/apply_surgical_updates.py
Strictly surgical DOM-level text and figure updater.
Preserves 100% of author formatting, styles.xml, document defaults, paragraph properties (<w:pPr>),
and font properties (<w:rPr>).
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
import copy

def update_document(in_docx, out_docx):
    print(f"Applying surgical updates to: {in_docx} -> {out_docx}")
    
    with zipfile.ZipFile(in_docx, "r") as zin:
        xml_bytes = zin.read("word/document.xml")
        rels_bytes = zin.read("word/_rels/document.xml.rels")
        all_files = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    # 1. Update Figure 1 Image Bytes in word/media/image2.png
    fig1_path = "Plots/fig1_lca_support_profiles.png"
    if os.path.exists(fig1_path):
        with open(fig1_path, "rb") as f:
            all_files["word/media/image2.png"] = f.read()
        print(f"  [+] Replaced word/media/image2.png with flipped {fig1_path}")

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

    # 2. Update Figure 1 DrawingML extent dimensions
    # Native dimensions of flipped fig1: 1950 x 1440
    cx = 5943600  # 6.5 in portrait EMUs
    cy = 4389120  # round(5943600 * (1440 / 1950))
    
    body = doc_tree.find('w:body', ns)
    ps = body.findall('w:p', ns)
    
    for i, p in enumerate(ps):
        txt = ''.join(p.itertext()).strip()
        
        # A. Update Figure 1 Drawing Extents
        if txt.startswith("Figure 1."):
            for off in range(1, 4):
                if i + off < len(ps):
                    cand = ps[i + off]
                    blips = cand.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
                    if blips:
                        for wp_ext in cand.findall('.//wp:extent', ns):
                            wp_ext.set('cx', str(cx))
                            wp_ext.set('cy', str(cy))
                        for a_ext in cand.findall('.//a:ext', ns):
                            a_ext.set('cx', str(cx))
                            a_ext.set('cy', str(cy))
                        print(f"  [+] Synchronized Figure 1 DrawingML extents to {cx}x{cy} EMUs")
                        break

        # B. Replace Log-Linear Critique Paragraph in Introduction (P9)
        if "A second limitation of previous empirical work concerns the analytical strategies used" in txt:
            print(f"  [+] Surgically updating Introduction paragraph P{i} with Lizardo (2024) frame analysis")
            # Preserve existing pPr
            pPr = p.find('w:pPr', ns)
            # Find base rPr from first run
            first_r = p.find('w:r', ns)
            base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None
            
            # Clear all existing children except pPr
            p_children = list(p)
            for child in p_children:
                if child != pPr:
                    p.remove(child)
                    
            # Helper to create a run inheriting base_rPr
            def make_run(text, italic=False):
                r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
                if base_rPr is not None:
                    rPr_copy = copy.deepcopy(base_rPr)
                    if italic:
                        i_elem = rPr_copy.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
                        if i_elem is None:
                            ET.SubElement(rPr_copy, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '1'})
                        else:
                            i_elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = '1'
                    r.append(rPr_copy)
                elif italic:
                    rPr_new = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rPr')
                    ET.SubElement(rPr_new, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '1'})
                t_elem = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                if text.startswith(' ') or text.endswith(' '):
                    t_elem.attrib['{http://www.w3.org/XML/1998/namespace}space'] = 'preserve'
                t_elem.text = text
                return r

            make_run("As Lizardo (2024) argues in a recent theoretical formulation, this persistent conflation stems from a deeper failure to recognize that the concept of a social tie is organized across multiple distinct cognitive and relational frames. Specifically, tie conceptualizations routinely collapse four autonomous dimensions: ")
            make_run("role frames", italic=True)
            make_run(" denoting categorical social positions (such as kin, friend, or coworker), ")
            make_run("sentiment frames", italic=True)
            make_run(" capturing affective evaluations (such as closeness, liking, or trust), ")
            make_run("behavioral interaction frames", italic=True)
            make_run(" indexing contact and communication patterns (such as daily or weekly activation), and ")
            make_run("exchange frames", italic=True)
            make_run(" encompassing the functional transmission of resources (such as companionship, advice, comfort, or financial assistance). When researchers treat one frame as an automatic index of another—such as assuming that role relations define tie strength, that high interaction frequency entails emotional intimacy, or that strong ties universally provide all forms of social support—they commit a category mistake that obscures the underlying division of relational labor in personal networks. Role relations may carry institutional expectations of solidarity, yet actual sentiments and behavioral activations vary substantially within every role category (Marsden & Campbell, 1984). Similarly, frequent interaction is often driven by situational co-presence in shared organizational foci rather than affective depth (Feld, 1982; Kitts, 2014), while the provision of specialized support is bounded by domain-specific norms and resource affordances rather than a generalized gradient of strength.")

        # C. Update Transition Sentence in P10
        if "To overcome these analytical limitations, this study presents an empirical investigation" in txt:
            print(f"  [+] Surgically updating transition phrasing in P{i}")
            for r in p.findall('w:r', ns):
                for t in r.findall('w:t', ns):
                    if t.text and "To overcome these analytical limitations" in t.text:
                        t.text = t.text.replace("To overcome these analytical limitations", "To address this pervasive conceptual confounding")

        # D. Replace Log-Linear Discussion Opening (P225)
        if "This study set out to recreate and empirically advance the investigation of tie strength, role relations, and social support presented in Lizardo’s 2018 Manchester Seminar." in txt:
            print(f"  [+] Surgically updating Discussion opening in P{i}")
            pPr = p.find('w:pPr', ns)
            first_r = p.find('w:r', ns)
            base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None
            
            p_children = list(p)
            for child in p_children:
                if child != pPr:
                    p.remove(child)
                    
            r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
            if base_rPr is not None:
                r.append(copy.deepcopy(base_rPr))
            t_elem = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
            t_elem.text = "This study set out to investigate the empirical links between tie strength, social role relations, and social support exchanges across personal networks, moving beyond the conceptual confounding that has long characterized research on social capital. Building on Lizardo’s (2024) frame-analytic model and Marsden and Campbell’s (1984) measurement framework, our analytical strategy decoupled role categories, affective sentiments, interaction frequencies, and functional support provisions. By combining Latent Class Analysis with Multilevel Generalized Linear Mixed Models, we eliminated the need for arbitrary heuristic groupings of support exchanges, properly accounted for the clustering of multiple dyadic ties within respondents, and evaluated the independent predictive contributions of distinct tie-strength dimensions net of role relations and demographic contexts."

        # E. Replace Agresti (2013) Reference with Lizardo (2024)
        if "Agresti, A. (2013). Categorical Data Analysis" in txt:
            print(f"  [+] Surgically updating reference entry in P{i}")
            pPr = p.find('w:pPr', ns)
            first_r = p.find('w:r', ns)
            base_rPr = first_r.find('w:rPr', ns) if first_r is not None else None
            
            p_children = list(p)
            for child in p_children:
                if child != pPr:
                    p.remove(child)
                    
            def make_ref_run(text, italic=False):
                r = ET.SubElement(p, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r')
                if base_rPr is not None:
                    rPr_copy = copy.deepcopy(base_rPr)
                    i_elem = rPr_copy.find('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i')
                    if italic:
                        if i_elem is None:
                            ET.SubElement(rPr_copy, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i', {'{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val': '1'})
                        else:
                            i_elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = '1'
                    else:
                        if i_elem is not None:
                            i_elem.attrib['{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val'] = '0'
                    r.append(rPr_copy)
                t_elem = ET.SubElement(r, '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')
                if text.startswith(' ') or text.endswith(' '):
                    t_elem.attrib['{http://www.w3.org/XML/1998/namespace}space'] = 'preserve'
                t_elem.text = text
                return r

            make_ref_run("Lizardo, O. (2024). Theorizing the concept of social tie using frames. ")
            make_ref_run("Social Networks", italic=True)
            make_ref_run(", ")
            make_ref_run("78", italic=True)
            make_ref_run(", 80–91. https://doi.org/10.1016/j.socnet.2024.01.001")

    all_files["word/document.xml"] = ET.tostring(doc_tree, encoding="utf-8", xml_declaration=True)

    with zipfile.ZipFile(out_docx, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, data in all_files.items():
            zout.writestr(fname, data)
    print(f"Successfully generated surgical update: {out_docx}")

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        update_document(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python3 apply_surgical_updates.py <in_docx> <out_docx>")
