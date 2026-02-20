"""
PDF Invoice Generator — produces an invoice PDF matching the Excel (.xlsm)
Bill Format sheet exactly.

Layout (top → bottom):
  1. Title bar  (doc-type name, centred, bold, bordered)
  2. Company header  (name, address, phone, email, website)  |  Copy type list
  3. Info grid  (GSTIN / PAN / CIN / State / State-Code  |  DSR / Vehicle /
     GR-LR / Place-of-Supply  |  Doc-No / Dates / PO / Vendor)
  4. Buyer (left)  |  Bank details (right)
  5. Line-items table  (S.No, Description, HSN, Qty, Rate, Dis., Taxable,
     SGST%, SGST Amt, CGST%, CGST Amt, IGST%, IGST Amt)
  6. Total-amount row
  7. Remarks  |  Totals breakdown (right)
  8. GST in words (left)  |  Totals cont'd (right)
  9. Grand Total in words
 10. E. & O.E.
 11. T&C (left)  |  Authorised Signatory (right)
 12. Computer-generated footer note
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from models.company import CompanyProfile
from models.document import Document
from services.calculator import format_currency, paise_to_rupees
from services.num_to_words import paise_to_words


# ── Colour palette ─────────────────────────────────────────────
_BLACK = colors.black
_GREY = colors.Color(0.4, 0.4, 0.4)
_LIGHT = colors.Color(0.92, 0.92, 0.92)

# ── Common border helpers ──────────────────────────────────────
_OUTER = ("BOX", (0, 0), (-1, -1), 1.0, _BLACK)

# Page constants
_PAGE_W, _PAGE_H = A4  # 595.27 × 841.89 pt
_LM = 14 * mm
_RM = 14 * mm
_CONTENT_W = _PAGE_W - _LM - _RM  # ≈ 567 pt


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    """Shortcut to create a Paragraph."""
    return Paragraph(str(text), style)


def _fmt(paise: int) -> str:
    """Convert integer paise to formatted rupee string without symbol."""
    return format_currency(paise, symbol="")


def generate_invoice_pdf(
    doc: Document,
    company: CompanyProfile,
    output_path: str,
    *,
    bank_details: bool = True,
    terms_text: str = "",
    copy_label: str = "",
) -> str:
    """Generate a PDF invoice matching the Excel Bill-Format sheet.

    Returns the absolute path of the generated PDF.
    """

    pdf = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=_LM,
        rightMargin=_RM,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )

    styles = getSampleStyleSheet()

    # ── Custom paragraph styles ────────────────────────────────
    s_title = ParagraphStyle(
        "T", parent=styles["Normal"],
        fontName="Helvetica-Bold", fontSize=16,
        alignment=TA_CENTER, leading=20,
    )
    s_addr = ParagraphStyle(
        "AD", parent=styles["Normal"],
        fontSize=8.5, alignment=TA_CENTER, leading=11,
    )
    s_n = ParagraphStyle(
        "N", parent=styles["Normal"], fontSize=8, leading=10,
    )
    s_nr = ParagraphStyle(
        "NR", parent=s_n, alignment=TA_RIGHT,
    )
    s_sm = ParagraphStyle(
        "SM", parent=s_n, fontSize=7, leading=9,
    )
    s_smr = ParagraphStyle(
        "SMR", parent=s_sm, alignment=TA_RIGHT,
    )
    s_smc = ParagraphStyle(
        "SMC", parent=s_sm, alignment=TA_CENTER,
    )
    s_smcb = ParagraphStyle(
        "SMCB", parent=s_smc, fontName="Helvetica-Bold",
    )
    s_foot = ParagraphStyle(
        "FT", parent=styles["Normal"],
        fontSize=7, alignment=TA_CENTER,
        textColor=_GREY, fontName="Helvetica-Oblique",
    )

    elements: list = []

    # ==================================================================
    #  1.  TITLE BAR
    # ==================================================================
    _type_map = {
        "IN": "TAX INVOICE", "QT": "QUOTATION", "PI": "PROFORMA INVOICE",
        "DC": "DELIVERY CHALLAN", "PO": "PURCHASE ORDER",
    }
    doc_type_display = _type_map.get(
        doc.document_type,
        doc.document_type.replace("_", " ").upper(),
    )

    title_data = [[_p(doc_type_display, s_title)]]
    title_tbl = Table(title_data, colWidths=[_CONTENT_W])
    title_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(title_tbl)

    # ==================================================================
    #  2.  COMPANY HEADER  +  COPY-TYPE LIST
    # ==================================================================
    copy_types = [
        "ORIGINAL FOR RECIPIENT",
        "DUPLICATE FOR TRANSPORTER",
        "TRIPLICATE FOR SUPPLIER",
        "EXTRA COPY",
    ]
    chosen = (copy_label or "").upper().strip()
    copy_lines = []
    for ct in copy_types:
        mark = "☑" if ct in chosen or chosen in ct else "☐"
        copy_lines.append(f"{mark}  {ct}")
    copy_block = "<br/>".join(copy_lines)

    comp_lines = [f"<b>{company.name or ''}</b>"]
    addr_parts = [p for p in [company.address_line1, company.address_line2] if p]
    if addr_parts:
        comp_lines.append(", ".join(addr_parts))
    if company.phone:
        comp_lines.append(f"Phone No :  {company.phone}")
    if company.email:
        comp_lines.append(f"E-mail : {company.email}")
    if company.website:
        comp_lines.append(company.website)

    header_data = [[
        _p("<br/>".join(comp_lines), s_addr),
        _p(copy_block, s_sm),
    ]]
    header_tbl = Table(
        header_data,
        colWidths=[_CONTENT_W * 0.72, _CONTENT_W * 0.28],
    )
    header_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 4),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _BLACK),
    ]))
    elements.append(header_tbl)

    # ==================================================================
    #  3.  INFO GRID  (3 cols × 5 rows)
    # ==================================================================
    info_data = [
        [
            _p(f"GSTIN :  {company.gstin or '—'}", s_sm),
            _p("GST Dealer :", s_sm),
            _p(f"<b>Invoice No. :</b>  {doc.document_number}", s_sm),
        ],
        [
            _p(f"PAN No:  {company.pan or '—'}", s_sm),
            _p(f"DSR Name :  {doc.dsr_number or ''}", s_sm),
            _p(f"Date of Invoice :  {doc.document_date or ''}", s_sm),
        ],
        [
            _p(f"CIN :  {company.cin or '—'}", s_sm),
            _p(f"Vehicle No :  {doc.vehicle_no or ''}", s_sm),
            _p(f"Date of Supply :  {doc.supply_date or ''}", s_sm),
        ],
        [
            _p(f"STATE : {company.state_name or ''}", s_sm),
            _p(f"GR/LR No:  {doc.gr_lr_no or ''}", s_sm),
            _p(f"P.O. No &amp; Date:  {doc.po_no_date or ''}", s_sm),
        ],
        [
            _p(f"STATE CODE : {company.state_code or ''}", s_sm),
            _p(f"Place of Supply:  {doc.place_of_supply or ''}", s_sm),
            _p(f"Vendor Code:  {doc.vendor_code or ''}", s_sm),
        ],
    ]
    cw3 = [_CONTENT_W * 0.35, _CONTENT_W * 0.30, _CONTENT_W * 0.35]
    info_tbl = Table(info_data, colWidths=cw3)
    info_tbl.setStyle(TableStyle([
        _OUTER,
        ("INNERGRID", (0, 0), (-1, -1), 0.25, _GREY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _BLACK),
        ("LINEAFTER", (1, 0), (1, -1), 0.4, _BLACK),
    ]))
    elements.append(info_tbl)

    # ==================================================================
    #  4.  BUYER  (left)  +  BANK DETAILS  (right)
    # ==================================================================
    buyer_lines = [
        "<b>Bill To (Buyer):</b>",
        f"&nbsp;&nbsp;&nbsp;<b>{doc.customer_name or '(Walk-in)'}</b>",
    ]
    for a in [doc.buyer_address1, doc.buyer_address2, doc.buyer_address3]:
        if a:
            buyer_lines.append(f"&nbsp;&nbsp;&nbsp;{a}")
    if doc.buyer_state_name:
        buyer_lines.append(
            f"&nbsp;&nbsp;&nbsp;State : {doc.buyer_state_name}"
            f"&nbsp;&nbsp; State Code : {doc.buyer_state_code}"
        )
    if doc.customer_gstin:
        buyer_lines.append(f"&nbsp;&nbsp;&nbsp;GST No.  {doc.customer_gstin}")
    if doc.buyer_pan:
        buyer_lines.append(f"&nbsp;&nbsp;&nbsp;PAN No:  {doc.buyer_pan}")

    bank_lines = ["<b>Our Bank Details :</b>"]
    if bank_details and company.bank_name:
        bank_lines.append(f"Pay Name : {company.name or ''}")
        branch_info = f"Bank : {company.bank_name}"
        if company.bank_branch:
            branch_info += f", Branch : {company.bank_branch}"
        bank_lines.append(branch_info)
        acc_info = f"Account No : {company.account_no or ''}"
        if company.account_type:
            acc_info += f" ({company.account_type} Type)"
        bank_lines.append(acc_info)
        bank_lines.append(f"IFSC Code : {company.ifsc_code or ''}")
    else:
        bank_lines.append("—")

    bb_data = [[
        _p("<br/>".join(buyer_lines), s_sm),
        _p("<br/>".join(bank_lines), s_sm),
    ]]
    bb_tbl = Table(
        bb_data,
        colWidths=[_CONTENT_W * 0.55, _CONTENT_W * 0.45],
    )
    bb_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _BLACK),
    ]))
    elements.append(bb_tbl)

    # ==================================================================
    #  5.  LINE-ITEMS TABLE  (13 columns, matching Excel)
    # ==================================================================
    #  S.No | Description | HSN | Qty | Rate | Dis.% |
    #  Taxable Amt | SGST% | SGST Amt | CGST% | CGST Amt | IGST% | IGST Amt
    #  Header spans two rows.

    cw = [
        _CONTENT_W * 0.038,   # 0  S.No
        _CONTENT_W * 0.193,   # 1  Description
        _CONTENT_W * 0.072,   # 2  HSN
        _CONTENT_W * 0.042,   # 3  Qty
        _CONTENT_W * 0.078,   # 4  Rate
        _CONTENT_W * 0.038,   # 5  Dis.
        _CONTENT_W * 0.098,   # 6  Taxable Amt
        _CONTENT_W * 0.038,   # 7  SGST %
        _CONTENT_W * 0.078,   # 8  SGST Amt
        _CONTENT_W * 0.038,   # 9  CGST %
        _CONTENT_W * 0.078,   # 10 CGST Amt
        _CONTENT_W * 0.038,   # 11 IGST %
        _CONTENT_W * 0.078,   # 12 IGST Amt
    ]
    # Fix rounding drift on last column
    cw[-1] = _CONTENT_W - sum(cw[:-1])

    # Header row 1 (main labels — GST groups span 2 cols each)
    h1 = [
        _p("<b>S.No</b>", s_smcb),
        _p("<b>Description</b>", s_smcb),
        _p("<b>HSN<br/>Code</b>", s_smcb),
        _p("<b>Qty</b>", s_smcb),
        _p("<b>Rate</b>", s_smcb),
        _p("<b>Dis.</b>", s_smcb),
        _p("<b>Taxable<br/>Amount</b>", s_smcb),
        _p("<b>SGST</b>", s_smcb), "",       # span 7-8
        _p("<b>CGST</b>", s_smcb), "",       # span 9-10
        _p("<b>IGST</b>", s_smcb), "",       # span 11-12
    ]
    # Header row 2 (sub-headers: % | Amt.)
    h2 = [
        "", "", "", "", "", "", "",
        _p("<b>%</b>", s_smcb),
        _p("<b>Amt.</b>", s_smcb),
        _p("<b>%</b>", s_smcb),
        _p("<b>Amt.</b>", s_smcb),
        _p("<b>%</b>", s_smcb),
        _p("<b>Amt.</b>", s_smcb),
    ]

    item_rows = [h1, h2]

    for idx, item in enumerate(doc.items, 1):
        # Build description (category + item_name on second line)
        desc = item.category_name or item.item_name or ""
        if (
            item.item_name
            and item.category_name
            and item.item_name != item.category_name
        ):
            desc = (
                f"{item.category_name}<br/>"
                f"<font size='6'>{item.item_name}</font>"
            )

        rate_r = paise_to_rupees(item.rate)
        disc_str = (
            f"{item.discount_pct * 100:.0f}" if item.discount_pct else ""
        )
        taxable_str = _fmt(item.taxable_amount)

        sgst_pct = (
            f"{item.sgst_rate * 100:.0f}" if item.sgst_rate else ""
        )
        sgst_amt = _fmt(item.sgst_amount) if item.sgst_amount else ""
        cgst_pct = (
            f"{item.cgst_rate * 100:.0f}" if item.cgst_rate else ""
        )
        cgst_amt = _fmt(item.cgst_amount) if item.cgst_amount else ""
        igst_pct = (
            f"{item.igst_rate * 100:.0f}" if item.igst_rate else ""
        )
        igst_amt = _fmt(item.igst_amount) if item.igst_amount else ""

        row = [
            _p(str(idx), s_smc),
            _p(desc, s_sm),
            _p(item.hsn_code or "", s_smc),
            _p(str(item.quantity), s_smc),
            _p(f"{rate_r:,.2f}", s_smr),
            _p(disc_str, s_smc),
            _p(taxable_str, s_smr),
            _p(sgst_pct, s_smc),
            _p(sgst_amt, s_smr),
            _p(cgst_pct, s_smc),
            _p(cgst_amt, s_smr),
            _p(igst_pct, s_smc),
            _p(igst_amt, s_smr),
        ]
        item_rows.append(row)

    # ── Total-amount row ──
    total_row = [
        "",
        _p("<b>Total Amount =</b>", s_smr),
        "", "", "", "",
        _p(f"<b>{_fmt(doc.total_taxable)}</b>", s_smr),
        "",
        _p(f"<b>{_fmt(doc.total_sgst)}</b>", s_smr),
        "",
        _p(f"<b>{_fmt(doc.total_cgst)}</b>", s_smr),
        "",
        _p(f"<b>{_fmt(doc.total_igst)}</b>", s_smr),
    ]
    item_rows.append(total_row)

    n_rows = len(item_rows)

    items_tbl = Table(item_rows, colWidths=cw, repeatRows=2)
    items_tbl.setStyle(TableStyle([
        _OUTER,
        ("INNERGRID", (0, 0), (-1, -1), 0.3, _BLACK),
        # ── Header row 1: GST group spans ──
        ("SPAN", (7, 0), (8, 0)),    # SGST
        ("SPAN", (9, 0), (10, 0)),   # CGST
        ("SPAN", (11, 0), (12, 0)),  # IGST
        # ── Header row 1: vertical span for first 7 cols ──
        ("SPAN", (0, 0), (0, 1)),    # S.No
        ("SPAN", (1, 0), (1, 1)),    # Description
        ("SPAN", (2, 0), (2, 1)),    # HSN
        ("SPAN", (3, 0), (3, 1)),    # Qty
        ("SPAN", (4, 0), (4, 1)),    # Rate
        ("SPAN", (5, 0), (5, 1)),    # Dis.
        ("SPAN", (6, 0), (6, 1)),    # Taxable
        # Header look
        ("BACKGROUND", (0, 0), (-1, 1), _LIGHT),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 1), 7),
        ("ALIGN", (0, 0), (-1, 1), "CENTER"),
        ("VALIGN", (0, 0), (-1, 1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, 1), 3),
        # Data rows
        ("FONTSIZE", (0, 2), (-1, -1), 7),
        ("VALIGN", (0, 2), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 2), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 2), (-1, -1), 2),
        # Total row
        ("BACKGROUND", (0, n_rows - 1), (-1, n_rows - 1), _LIGHT),
        ("FONTNAME", (0, n_rows - 1), (-1, n_rows - 1), "Helvetica-Bold"),
        ("LINEABOVE", (0, n_rows - 1), (-1, n_rows - 1), 0.8, _BLACK),
        ("SPAN", (0, n_rows - 1), (1, n_rows - 1)),
    ]))
    elements.append(items_tbl)

    # ==================================================================
    #  6.  REMARKS  +  TOTALS BREAKDOWN
    # ==================================================================
    currency = company.currency_symbol or "₹"

    # Determine GST % labels from first item that has a rate
    sgst_rate_lbl = cgst_rate_lbl = igst_rate_lbl = ""
    for it in (doc.items or []):
        if it.sgst_rate and not sgst_rate_lbl:
            sgst_rate_lbl = f"{it.sgst_rate * 100:.0f}"
        if it.cgst_rate and not cgst_rate_lbl:
            cgst_rate_lbl = f"{it.cgst_rate * 100:.0f}"
        if it.igst_rate and not igst_rate_lbl:
            igst_rate_lbl = f"{it.igst_rate * 100:.0f}"

    sgst_label = f"Add SGST @{sgst_rate_lbl}% =" if sgst_rate_lbl else "Add SGST ="
    cgst_label = f"Add CGST @{cgst_rate_lbl}% =" if cgst_rate_lbl else "Add CGST ="
    igst_label = f"Add IGST @{igst_rate_lbl}% =" if igst_rate_lbl else "Add IGST ="

    sgst_words = paise_to_words(doc.total_sgst) if doc.total_sgst else ""
    cgst_words = paise_to_words(doc.total_cgst) if doc.total_cgst else ""
    igst_words = paise_to_words(doc.total_igst) if doc.total_igst else ""

    left_w = _CONTENT_W * 0.48
    mid_w = _CONTENT_W * 0.27
    val_w = _CONTENT_W * 0.25

    totals_data = [
        [
            _p(f"<b>Remarks:</b> {doc.remarks or ''}", s_sm),
            "", "",
        ],
        [
            "",
            _p("Total Taxable Value =", s_smr),
            _p(f"{currency} {_fmt(doc.total_taxable)}", s_smr),
        ],
        [
            _p("<b>Total GST Amount in words:</b>", s_sm),
            _p(sgst_label, s_smr),
            _p(f"{currency} {_fmt(doc.total_sgst)}", s_smr),
        ],
        [
            _p(f"SGST : {sgst_words}", s_sm),
            _p(cgst_label, s_smr),
            _p(f"{currency} {_fmt(doc.total_cgst)}", s_smr),
        ],
        [
            _p(f"CGST : {cgst_words}", s_sm),
            _p(igst_label, s_smr),
            _p(f"{currency} {_fmt(doc.total_igst)}", s_smr),
        ],
        [
            _p(f"IGST : {igst_words}", s_sm),
            _p("<b>Grand Total  =</b>", s_smr),
            _p(f"<b>{currency} {_fmt(doc.grand_total)}</b>", s_smr),
        ],
    ]
    totals_tbl = Table(totals_data, colWidths=[left_w, mid_w, val_w])
    totals_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 4),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _BLACK),
        ("LINEBELOW", (1, 0), (-1, 0), 0.25, _GREY),
        ("LINEBELOW", (1, 1), (-1, 1), 0.25, _GREY),
        ("LINEBELOW", (1, 2), (-1, 2), 0.25, _GREY),
        ("LINEBELOW", (1, 3), (-1, 3), 0.25, _GREY),
        ("LINEBELOW", (1, 4), (-1, 4), 0.25, _GREY),
        ("LINEABOVE", (1, -1), (-1, -1), 0.6, _BLACK),
        ("FONTNAME", (1, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(totals_tbl)

    # ==================================================================
    #  7.  GRAND TOTAL IN WORDS
    # ==================================================================
    words_data = [[
        _p("<b>Grand Total in words :</b>", s_sm),
        _p(doc.amount_in_words or "", s_sm),
    ]]
    words_tbl = Table(
        words_data,
        colWidths=[_CONTENT_W * 0.25, _CONTENT_W * 0.75],
    )
    words_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(words_tbl)

    # ==================================================================
    #  8.  E. & O.E.
    # ==================================================================
    eoe_data = [[_p("E. &amp; O.E.", s_sm)]]
    eoe_tbl = Table(eoe_data, colWidths=[_CONTENT_W])
    eoe_tbl.setStyle(TableStyle([
        _OUTER,
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(eoe_tbl)

    # ==================================================================
    #  9.  T&C  (left)  +  AUTHORISED SIGNATORY  (right)
    # ==================================================================
    tc_block = "<b>Terms &amp; Condition :</b>"
    if terms_text:
        safe_tc = terms_text.replace("&", "&amp;").replace(
            "\n", "<br/>"
        )
        tc_block += f"<br/>{safe_tc}"

    sig_name = company.name or ""
    sig_label = company.signature_label or "Authorised Signatory"
    sig_block = (
        f"<b>For {sig_name}</b>"
        f"<br/><br/><br/><br/>"
        f"{sig_label}"
    )

    s_sig = ParagraphStyle("SIG", parent=s_sm, alignment=TA_RIGHT)

    tc_sig_data = [[
        _p(tc_block, s_sm),
        _p(sig_block, s_sig),
    ]]
    tc_sig_tbl = Table(
        tc_sig_data,
        colWidths=[_CONTENT_W * 0.60, _CONTENT_W * 0.40],
    )
    tc_sig_tbl.setStyle(TableStyle([
        _OUTER,
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 6),
        ("LINEAFTER", (0, 0), (0, -1), 0.4, _BLACK),
    ]))
    elements.append(tc_sig_tbl)

    # ==================================================================
    # 10.  FOOTER NOTE
    # ==================================================================
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        _p(
            " **This document is computer generated signature not required",
            s_foot,
        )
    )

    # ── BUILD ──
    pdf.build(elements)
    return output_path
