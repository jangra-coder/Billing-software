"""
GSTR-1 Report Generator v3.3 - LOCKED UI & MAPPING FIX
================================================================================
CHANGES IN THIS VERSION:
1. 🔒 UI Fields (GSTIN/Business) are now READ-ONLY.
2. ✅ GSTIN Mapping: Now reads from Column Z (Index 25) instead of Y.
   (No other changes made to Excel output format).

Updated for MKRD Billing
Date: February 2026
================================================================================
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
import os
import sys
import traceback

class GSTR1Generator(tk.Tk):
    """Main application class for GSTR-1 Report Generator"""
    
    def __init__(self):
        super().__init__()
        
        self.title("GSTR-1 Report Generator v3.3 (Locked & Fixed)")
        self.geometry("750x750")
        self.resizable(False, False)
        
        try:
            self.tk.call('set', '::tk::mac::useCompatibilityMetrics', '0')
        except:
            pass
        
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
        
        self.input_file = tk.StringVar()
        self.output_folder = tk.StringVar(value=self.get_default_output())
        self.from_date = tk.StringVar()
        self.to_date = tk.StringVar()
        self.gstin = tk.StringVar(value="06AHXPJ4596L1ZD")
        self.business_name = tk.StringVar(value="MKRD ENGINEERS PVT. LTD.")
        
        self.create_widgets()
        self.center_window()
    
    def get_default_output(self):
        try:
            return os.path.join(os.path.expanduser("~"), "Desktop")
        except:
            return os.path.expanduser("~")
    
    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="25")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        title = ttk.Label(header_frame, text="GSTR-1 Report Generator", 
                          font=('Arial', 20, 'bold'))
        title.pack()
        
        subtitle = ttk.Label(header_frame, text="v3.3 (Locked UI + Col Z Fix)", 
                           font=('Arial', 10, 'italic'), foreground='blue')
        subtitle.pack(pady=(5, 0))
        
        row = 1
        ttk.Label(main_frame, text="📁 Input File:", 
                  font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        
        ttk.Entry(file_frame, textvariable=self.input_file, width=45).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(file_frame, text="Browse...", command=self.browse_input, width=10).pack(side=tk.LEFT)
        
        row += 1
        ttk.Label(main_frame, text="📂 Output Folder:", 
                  font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        
        ttk.Entry(output_frame, textvariable=self.output_folder, width=45).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output, width=10).pack(side=tk.LEFT)
        
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, 
                                                            sticky=(tk.W, tk.E), pady=15)
        
        row += 1
        ttk.Label(main_frame, text="📅 Period:", 
                  font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        date_frame = ttk.Frame(main_frame)
        date_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W, pady=8)
        
        ttk.Label(date_frame, text="From:").pack(side=tk.LEFT, padx=(0, 5))
        from_entry = ttk.Entry(date_frame, textvariable=self.from_date, width=13)
        from_entry.pack(side=tk.LEFT, padx=(0, 20))
        from_entry.insert(0, "01/01/2026")
        
        ttk.Label(date_frame, text="To:").pack(side=tk.LEFT, padx=(0, 5))
        to_entry = ttk.Entry(date_frame, textvariable=self.to_date, width=13)
        to_entry.pack(side=tk.LEFT)
        to_entry.insert(0, "31/01/2026")
        
        row += 1
        ttk.Label(main_frame, text="(DD/MM/YYYY)", 
                  font=('Arial', 8, 'italic'), foreground='gray').grid(row=row, column=1, sticky=tk.W)
        
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, 
                                                            sticky=(tk.W, tk.E), pady=15)
        
        row += 1
        ttk.Label(main_frame, text="📊 GSTIN:", 
                  font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        # --- LOCKED (Read Only) ---
        ttk.Entry(main_frame, textvariable=self.gstin, width=25, state='readonly').grid(row=row, column=1, 
                                                                     sticky=tk.W, pady=8)
        
        row += 1
        ttk.Label(main_frame, text="🏢 Business:", 
                  font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, pady=8)
        
        # --- LOCKED (Read Only) ---
        ttk.Entry(main_frame, textvariable=self.business_name, width=45, state='readonly').grid(row=row, column=1, 
                                                                             columnspan=2, sticky=tk.W, pady=8)
        
        row += 1
        ttk.Separator(main_frame, orient='horizontal').grid(row=row, column=0, columnspan=3, 
                                                            sticky=(tk.W, tk.E), pady=15)
        
        row += 1
        ttk.Label(main_frame, text="📋 Status:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W)
        
        row += 1
        status_container = ttk.Frame(main_frame)
        status_container.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.status_text = tk.Text(status_container, height=10, width=80, wrap=tk.WORD,
                                   bg='#fafafa', font=('Consolas', 9), relief=tk.SOLID, bd=1)
        scrollbar = ttk.Scrollbar(status_container, orient="vertical", command=self.status_text.yview)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_text.insert('1.0', '✨ GSTR-1 Generator v3.3 Ready\n')
        self.status_text.insert('2.0', '━' * 70 + '\n')
        self.status_text.insert('3.0', '📌 Mapped to Col Z for GSTIN\n')
        self.status_text.config(state=tk.DISABLED)
        
        row += 1
        self.progress = ttk.Progressbar(main_frame, length=680, mode='determinate')
        self.progress.grid(row=row, column=0, columnspan=3, pady=(15, 5))
        
        row += 1
        self.progress_label = ttk.Label(main_frame, text="", font=('Arial', 9, 'italic'), 
                                      foreground='#666')
        self.progress_label.grid(row=row, column=0, columnspan=3)
        
        row += 1
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)
        
        self.generate_btn = ttk.Button(button_frame, text="🚀 Generate GSTR-1 Report",
                                     command=self.generate_report)
        self.generate_btn.pack(ipadx=30, ipady=12)
        
        style = ttk.Style()
        style.configure('TButton', font=('Arial', 12, 'bold'))
    
    def browse_input(self):
        try:
            self.lift()
            self.focus_force()
            filename = filedialog.askopenfilename(
                parent=self, title="Select Billing File (.xlsm)",
                filetypes=[("Excel Macro Files", "*.xlsm"), ("Excel Files", "*.xlsx"), ("All Files", "*.*")]
            )
            if filename:
                self.input_file.set(filename)
                self.log_status(f"Selected: {os.path.basename(filename)}")
        except Exception as e:
            self.log_status(f"Error selecting file: {str(e)}", 'error')
            print(f"File dialog error: {e}")
            traceback.print_exc()
    
    def browse_output(self):
        try:
            self.lift()
            self.focus_force()
            folder = filedialog.askdirectory(parent=self, title="Select Output Folder", initialdir=self.output_folder.get())
            if folder:
                self.output_folder.set(folder)
                self.log_status(f"Output: {folder}")
        except Exception as e:
            self.log_status(f"Error selecting folder: {str(e)}", 'error')
            print(f"Folder dialog error: {e}")
            traceback.print_exc()
    
    def log_status(self, message, level='info'):
        self.status_text.config(state=tk.NORMAL)
        icons = {'info': '📌', 'success': '✅', 'warning': '⚠️', 'error': '❌', 'process': '⚙️'}
        icon = icons.get(level, '•')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {icon} {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
        self.update()
    
    def update_progress(self, value, label=""):
        self.progress['value'] = value
        if label:
            self.progress_label.config(text=label)
        self.update()
    
    def parse_comma_separated(self, value):
        if pd.isna(value) or not str(value).strip():
            return []
        return [x.strip() for x in str(value).split(',') if x.strip()]
    
    def safe_float(self, value, default=0.0):
        try:
            if pd.isna(value) or str(value).strip() == '':
                return default
            return float(value)
        except:
            return default
    
    def safe_str(self, value, default=''):
        if pd.isna(value) or value is None:
            return default
        return str(value).strip()
    
    def load_data(self, filepath, from_date, to_date):
        """
        UPDATED LOADING LOGIC FOR NEW EXCEL FORMAT (Cols A to AE)
        Sheet Name: 'Tax Invoice Details'
        """
        # NEW COLUMN MAPPING - FIXED FOR GSTIN IN Z (Index 25)
        col_map = {
            0: 'Invoice_No',       # A
            1: 'Buyer_Name',       # B
            2: 'Mobile',           # C
            3: 'Buyer_Name_Rep',   # D
            4: 'Invoice_Date',     # E
            5: 'Supply_Date',      # F
            6: 'Category',         # G
            7: 'Items_Name',       # H
            8: 'HSN_CODE',         # I
            9: 'Quantity',         # J
            10: 'Rate',            # K
            11: 'Discount',        # L
            12: 'Taxable_Amount',  # M
            13: 'CGST',            # N
            14: 'SGST',            # O
            15: 'IGST',            # P
            16: 'Grand_Total',     # Q
            17: 'Address_Buyer',   # R
            18: 'Address_Seller',  # S
            19: 'PAN_Seller',      # T
            20: 'PAN_Buyer',       # U
            21: 'State_Code',      # V
            22: 'Vendor_Code',     # W
            23: 'CIN',             # X
            24: 'DSR_Number',      # Y (Old GSTIN spot - now DSR)
            25: 'GSTIN',           # Z (FIXED: GSTIN is here now)
            26: 'Vehicle_No',      # AA
            27: 'GR_LR_No',        # AB
            28: 'Place_Of_Supply', # AC 
            29: 'PO_No_Date',      # AD
            30: 'POS_Exact'        # AE
        }
        
        sheet_name = 'Tax Invoice Details'
        
        try:
            self.log_status(f"Reading '{sheet_name}'...", 'process')
            self.update_progress(10, f"Reading {sheet_name}...")
            
            # Using data_only=True to get Calculated Values not formulas
            wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
            
            if sheet_name not in wb.sheetnames:
                self.log_status(f"ERROR: Sheet '{sheet_name}' not found!", 'error')
                self.log_status(f"Available sheets: {wb.sheetnames}", 'info')
                return pd.DataFrame()
            
            ws = wb[sheet_name]
            if ws.max_row < 3:
                return pd.DataFrame()
            
            sheet_data = []
            # Assuming headers are in Row 1 or 2, and data starts Row 3
            # We scan from Row 3 downwards
            for row_idx in range(3, ws.max_row + 1):
                # We iterate 0 to 30 (Cols A to AE)
                row_dict = {col_map.get(i, f'Col_{i}'): ws.cell(row_idx, i+1).value for i in range(31)}
                
                # Check validity based on Invoice No
                if row_dict.get('Invoice_No'):
                    sheet_data.append(row_dict)
            
            wb.close()
            
            if not sheet_data:
                self.log_status("No invoices found in the sheet.", 'error')
                return pd.DataFrame()
            
            df = pd.DataFrame(sheet_data)
            df['Invoice_Date'] = pd.to_datetime(df['Invoice_Date'], errors='coerce')
            
            if df['Invoice_Date'].notna().sum() > 0:
                df = df[(df['Invoice_Date'] >= from_date) & (df['Invoice_Date'] <= to_date)]
                self.log_status(f"Loaded {len(df)} invoices in date range.", 'success')
            else:
                self.log_status("Warning: No valid dates found, using all.", 'warning')
            
            return df
            
        except Exception as e:
            self.log_status(f"ERROR: {str(e)}", 'error')
            traceback.print_exc()
            return pd.DataFrame()

    def generate_report(self):
        try:
            if not self.validate_inputs(): return
            
            self.status_text.config(state=tk.NORMAL)
            self.status_text.delete('1.0', tk.END)
            self.status_text.config(state=tk.DISABLED)
            self.generate_btn.config(state=tk.DISABLED)
            
            self.log_status("="*70)
            self.log_status("GSTR-1 GENERATION STARTED (v3.3)", 'success')
            self.log_status("="*70)
            self.update_progress(0)
            
            try:
                from_date = datetime.strptime(self.from_date.get(), "%d/%m/%Y")
                to_date = datetime.strptime(self.to_date.get(), "%d/%m/%Y")
            except:
                messagebox.showerror("Error", "Invalid date! Use DD/MM/YYYY")
                self.generate_btn.config(state=tk.NORMAL)
                return

            self.update_progress(5)
            data = self.load_data(self.input_file.get(), from_date, to_date)
            
            if data.empty:
                messagebox.showwarning("Warning", "No data found or sheet missing!")
                self.generate_btn.config(state=tk.NORMAL)
                return
            
            self.log_status(f"Total TAX INVOICES: {len(data)}", 'success')
            self.update_progress(20)
            
            output_file = os.path.join(self.output_folder.get(), "GSTR_report.xlsx")
            self.create_gstr1_report(data, output_file, from_date, to_date)
            
            self.update_progress(100)
            self.log_status("="*70, 'success')
            self.log_status("SUCCESS! Report generated.", 'success')
            self.generate_btn.config(state=tk.NORMAL)
            
            if messagebox.askyesno("Success", f"Report saved at:\n{output_file}\n\nOpen now?"):
                self.open_file(output_file)
        except Exception as e:
            self.log_status(f"Error: {e}", 'error')
            print(traceback.format_exc())
            self.generate_btn.config(state=tk.NORMAL)

    def validate_inputs(self):
        if not self.input_file.get() or not os.path.exists(self.input_file.get()): return False
        if not self.output_folder.get(): return False
        if not self.from_date.get(): return False
        if not self.to_date.get(): return False
        return True
        
    def open_file(self, filepath):
        try:
            if sys.platform == 'darwin': os.system(f'open "{filepath}"')
            elif sys.platform == 'win32': os.startfile(filepath)
            else: os.system(f'xdg-open "{filepath}"')
        except: pass

    def create_gstr1_report(self, data, output_file, from_date, to_date):
        self.log_status("Creating workbook...", 'process')
        wb = openpyxl.Workbook()
        wb.remove(wb.active)
        
        self.update_progress(30, "GSTR1 Report...")
        self.create_gstr1_summary_sheet(wb, data, from_date, to_date)
        
        self.update_progress(40, "B2B...")
        self.create_b2b_sheet(wb, data)
        
        self.update_progress(50, "Templates...")
        self.create_template_sheets(wb)
        
        self.update_progress(60, "HSN(b2b)...")
        self.create_hsn_b2b_sheet(wb, data)
        self.create_hsn_b2c_template(wb)
        
        self.update_progress(70, "itemSummary...")
        self.create_item_summary_sheet(wb, data)
        
        self.update_progress(80, "docs...")
        self.create_docs_sheet(wb, data, from_date, to_date)
        
        self.update_progress(90, "Saving...")
        wb.save(output_file)
        self.log_status("Saved!", 'success')

    def create_gstr1_summary_sheet(self, wb, data, from_date, to_date):
        ws = wb.create_sheet("GSTR1 Report", 0)
        
        ws['A1'] = "Period"
        ws['B1'] = f"{from_date.strftime('%B %Y')} - {to_date.strftime('%B %Y')}"
        ws['B1'].font = Font(bold=False)
        
        ws['A3'] = "1. GSTIN"
        ws['B3'] = self.gstin.get()
        ws['A4'] = "2.a Legal name of the registered person."
        ws['B4'] = self.business_name.get()
        ws['A5'] = "2.b Trade name, if any"
        ws['B5'] = ""
        ws['A6'] = "3.a Aggregate turnover of the preceeding Financial Year"
        ws['B6'] = ""
        ws['A7'] = "3.b Aggregate turnover, April to June 2017"
        ws['B7'] = ""
        
        headers = [
            'GSTIN/UIN', 'Party Name', 'Transaction Type', 'Invoice No.', 'Invoice Date',
            'Invoice Value', 'Rate', 'Cess Rate', 'Taxable value', 'Reverse Charge',
            'Integrated Tax Amount', 'Central Tax Amount', 'State/UT Tax Amount',
            'Cess Amount', 'Place of Supply(Name of state)'
        ]
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(9, col_idx, header)
            cell.font = Font(bold=False, size=10)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Accumulators
        t_inv, t_tax, t_igst, t_cgst, t_sgst, t_cess = 0, 0, 0, 0, 0, 0
        
        row_idx = 10
        for _, invoice in data.iterrows():
            ws.cell(row_idx, 1, self.safe_str(invoice['GSTIN']))
            ws.cell(row_idx, 2, self.safe_str(invoice['Buyer_Name']))
            ws.cell(row_idx, 3, 'Regular')
            ws.cell(row_idx, 4, self.safe_str(invoice['Invoice_No']))
            
            if pd.notna(invoice['Invoice_Date']):
                val = invoice['Invoice_Date'].strftime('%d-%b-%Y') if isinstance(invoice['Invoice_Date'], datetime) else str(invoice['Invoice_Date'])
                ws.cell(row_idx, 5, val)
            
            inv_vals = self.parse_comma_separated(invoice['Grand_Total'])
            inv_value = sum(self.safe_float(v) for v in inv_vals)
            t_inv += inv_value
            
            ws.cell(row_idx, 6, inv_value).number_format = '#,##0.00'
            
            taxable_vals = self.parse_comma_separated(invoice['Taxable_Amount'])
            taxable = sum(self.safe_float(v) for v in taxable_vals)
            t_tax += taxable
            
            cgst_vals = self.parse_comma_separated(invoice['CGST'])
            cgst = sum(self.safe_float(v) for v in cgst_vals)
            t_cgst += cgst
            
            sgst_vals = self.parse_comma_separated(invoice['SGST'])
            sgst = sum(self.safe_float(v) for v in sgst_vals)
            t_sgst += sgst
            
            igst_vals = self.parse_comma_separated(invoice['IGST'])
            igst = sum(self.safe_float(v) for v in igst_vals)
            t_igst += igst
            
            if taxable > 0:
                if igst > 0:
                    rate = (igst / taxable) * 100
                elif cgst > 0 or sgst > 0:
                    rate = ((cgst + sgst) / taxable) * 100
                else:
                    rate = 0
            else:
                rate = 0
            
            ws.cell(row_idx, 7, rate).number_format = '0.00'
            ws.cell(row_idx, 8, 0)
            ws.cell(row_idx, 9, taxable).number_format = '#,##0.00'
            ws.cell(row_idx, 10, 'N')
            ws.cell(row_idx, 11, igst).number_format = '#,##0.00'
            ws.cell(row_idx, 12, cgst).number_format = '#,##0.00'
            ws.cell(row_idx, 13, sgst).number_format = '#,##0.00'
            ws.cell(row_idx, 14, 0).number_format = '#,##0.00'
            ws.cell(row_idx, 15, self.safe_str(invoice['Place_Of_Supply']))
            row_idx += 1
        
        # --- SKIP ONE ROW (GAP) ---
        row_idx += 1
        
        # --- WRITE TOTAL ROW ---
        ws.cell(row_idx, 1, "Total")
        ws.cell(row_idx, 6, t_inv).number_format = '#,##0.00'
        ws.cell(row_idx, 9, t_tax).number_format = '#,##0.00'
        ws.cell(row_idx, 11, t_igst).number_format = '#,##0.00'
        ws.cell(row_idx, 12, t_cgst).number_format = '#,##0.00'
        ws.cell(row_idx, 13, t_sgst).number_format = '#,##0.00'
        ws.cell(row_idx, 14, t_cess).number_format = '#,##0.00'
        
        col_widths = [18, 25, 15, 15, 12, 12, 8, 8, 12, 10, 12, 12, 12, 10, 20]
        for i, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width

    def create_b2b_sheet(self, wb, data):
        ws = wb.create_sheet("b2b,sez,de")
        
        ws['A1'] = "Summary For B2B, SEZ, DE (4A, 4B, 6B, 6C)"
        ws['A1'].font = Font(bold=False, size=12)
        
        # Filter for rows that have a GSTIN
        b2b_data = data[data['GSTIN'].notna() & (data['GSTIN'] != '')].copy()
        
        total_val = 0
        for _, row in b2b_data.iterrows():
            grand_totals = self.parse_comma_separated(row['Grand_Total'])
            total_val += sum(self.safe_float(x) for x in grand_totals)
            
        ws['A2'] = "No. of Recipients"
        ws['C2'] = "No. of Invoices"
        ws['E2'] = "Total Invoice Value"
        ws['A3'] = b2b_data['GSTIN'].nunique() if not b2b_data.empty else 0
        ws['C3'] = len(b2b_data)
        ws['E3'] = total_val
        ws['E3'].number_format = '#,##0.00'
        
        headers = ['GSTIN/UIN of Recipient', 'Receiver Name', 'Invoice Number', 'Invoice date',
                   'Invoice Value', 'Place Of Supply', 'Reverse Charge', 'Applicable % of Tax Rate',
                   'Invoice Type', 'E-Commerce GSTIN', 'Rate', 'Taxable Value', 'Cess Amount']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, header)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        row_idx = 5
        for _, invoice in b2b_data.iterrows():
            rates = self.parse_comma_separated(invoice['Rate'])
            taxables = self.parse_comma_separated(invoice['Taxable_Amount'])
            cgsts = self.parse_comma_separated(invoice['CGST'])
            sgsts = self.parse_comma_separated(invoice['SGST'])
            igsts = self.parse_comma_separated(invoice['IGST'])
            
            rate_groups = {}
            max_len = len(taxables)
            
            for i in range(max_len):
                tax_val = self.safe_float(taxables[i])
                c_val = self.safe_float(cgsts[i]) if i < len(cgsts) else 0.0
                s_val = self.safe_float(sgsts[i]) if i < len(sgsts) else 0.0
                i_val = self.safe_float(igsts[i]) if i < len(igsts) else 0.0
                
                total_tax = c_val + s_val + i_val
                if tax_val > 0:
                    calc_rate = (total_tax / tax_val) * 100
                    r_val = round(calc_rate, 2)
                else:
                    r_val = 0.0
                
                if r_val not in rate_groups:
                    rate_groups[r_val] = {'taxable': 0.0, 'tax': 0.0}
                
                rate_groups[r_val]['taxable'] += tax_val
                rate_groups[r_val]['tax'] += total_tax
            
            grand_totals = self.parse_comma_separated(invoice['Grand_Total'])
            total_inv_val = sum(self.safe_float(x) for x in grand_totals)
            
            for rate_key, amounts in rate_groups.items():
                ws.cell(row_idx, 1, self.safe_str(invoice['GSTIN']))
                ws.cell(row_idx, 2, self.safe_str(invoice['Buyer_Name']))
                ws.cell(row_idx, 3, self.safe_str(invoice['Invoice_No']))
                
                if pd.notna(invoice['Invoice_Date']):
                    val = invoice['Invoice_Date'].strftime('%d-%b-%Y') if isinstance(invoice['Invoice_Date'], datetime) else str(invoice['Invoice_Date'])
                    ws.cell(row_idx, 4, val)
                    
                ws.cell(row_idx, 5, total_inv_val)
                ws.cell(row_idx, 5).number_format = '#,##0.00'
                
                ws.cell(row_idx, 6, self.safe_str(invoice['Place_Of_Supply']))
                ws.cell(row_idx, 7, 'N')
                ws.cell(row_idx, 8, '')
                ws.cell(row_idx, 9, 'Regular')
                ws.cell(row_idx, 10, '')
                
                ws.cell(row_idx, 11, rate_key)
                ws.cell(row_idx, 11).number_format = '0.00'
                
                ws.cell(row_idx, 12, amounts['taxable'])
                ws.cell(row_idx, 12).number_format = '#,##0.00'
                
                ws.cell(row_idx, 13, 0)
                ws.cell(row_idx, 13).number_format = '#,##0.00'
                
                row_idx += 1
        
        for col in range(1, 14):
            ws.column_dimensions[get_column_letter(col)].width = 15

    def create_template_sheets(self, wb):
        
        # B2CL
        ws = wb.create_sheet("b2cl")
        ws['A1'] = "Summary For B2CL(5)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['A2'] = "No. of Invoices"
        ws['C2'] = "Total Invoice Value"
        ws['G2'] = "Total Taxable Value"
        ws['H2'] = "Total Cess"
        ws['A3'] = '0'
        ws['C3'] = '0'
        ws['G3'] = '0'
        ws['h3'] = '0'
        
        headers = ['Invoice Number', 'Invoice date', 'Invoice Value', 'Place Of Supply',
                   'Applicable % of Tax Rate', 'Rate', 'Taxable Value', 'Cess Amount', 'E-Commerce GSTIN']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # B2CS
        ws = wb.create_sheet("b2cs")
        ws['A1'] = "Summary For B2CS(7)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['E2'] = "Total Taxable Value"
        ws['F2'] = "Total Cess"
        ws['E3'] = '0'
        ws['F3'] = '0'
        
        headers = ['Type', 'Place Of Supply', 'Applicable % of Tax Rate', 'Rate',
                   'Taxable Value', 'Cess Amount', 'E-Commerce GSTIN']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # CDNR
        ws = wb.create_sheet("cdnr")
        ws['A1'] = "Summary For CDNR(9B)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['A2'] = "No. of Recipients"
        ws['C2'] = "No. of Notes"
        ws['I2'] = "Total Note Value"
        ws['A3'] = '0'
        ws['C3'] = '0'
        ws['I3'] = '0'
        ws['L3'] = '0'
        ws['M3'] = '0'
        
        headers = ['GSTIN/UIN of Recipient', 'Receiver Name', 'Note Number', 'Note Date',
                   'Note Type', 'Place Of Supply', 'Reverse Charge', 'Note Supply Type',
                   'Note Value', 'Applicable % of Tax Rate', 'Rate', 'Taxable Value',
                   'Central Tax Amount', 'State/UT Tax Amount', 'Integrated Tax Amount']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # CDNUR
        ws = wb.create_sheet("cdnur")
        ws['A1'] = "Summary For CDNUR(9B)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['B2'] = "No. of Notes/Vouchers"
        ws['F2'] = "Total Note Value"
        ws['I2'] = "Total Taxable Value"
        ws['B3'] = '0'
        ws['F3'] = '0'
        ws['I3'] = '0'
        ws['J3'] = '0'
        
        headers = ['UR Type', 'Note Number', 'Note Date', 'Note Type', 'Place Of Supply',
                   'Note Value', 'Applicable % of Tax Rate', 'Rate', 'Taxable Value',
                   'Central Tax Amount', 'State/UT Tax Amount', 'Integrated Tax Amount', 'Cess Amount']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # EXP
        ws = wb.create_sheet("exp")
        ws['A1'] = "Summary For EXP(6)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['B2'] = "No. of Invoices"
        ws['D2'] = "Total Invoice Value"
        ws['F2'] = "No. of Shipping Bill"
        ws['I2'] = "Total Taxable Value"
        
        headers = ['Export Type', 'Invoice Number', 'Invoice date', 'Invoice Value',
                   'Port Code', 'Shipping Bill Number', 'Shipping Bill Date', 'Rate', 'Taxable Value']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # AT
        ws = wb.create_sheet("at")
        ws['A1'] = "Summary For Advance Received(11B)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['D2'] = "Total Advance Received"
        ws['E2'] = "Total Cess"
        
        headers = ['Place Of Supply', 'Applicable % of Tax Rate', 'Rate',
                   'Gross Advance Received', 'Cess Amount']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # ATADJ
        ws = wb.create_sheet("atadj")
        ws['A1'] = "Summary For Advance Adjusted(11B)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['D2'] = "Total Advance Adjusted"
        ws['E2'] = "Total Cess"
        
        headers = ['Place Of Supply', 'Applicable % of Tax Rate', 'Rate',
                   'Gross Advance Adjusted', 'Cess Amount']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        # EXEMP
        ws = wb.create_sheet("exemp")
        ws['A1'] = "Summary For Nil rated, exempted and non GST outward supplies (8)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['B2'] = "Total Nil Rated Supplies"
        ws['C2'] = "Total Exempted Supplies"
        ws['D2'] = "Total Non-GST Supplies"
        ws['B3'] = '0'
        ws['C3'] = '0'
        ws['D3'] = '0'
        ws['B5'] = '0'
        ws['B6'] = '0'
        ws['B7'] = '0'
        ws['B8'] = '0'
        ws['C5'] = '0'
        ws['C6'] = '0'
        ws['C7'] = '0'
        ws['C8'] = '0'
        ws['D5'] = '0'
        ws['D6'] = '0'
        ws['D7'] = '0'
        ws['D8'] = '0'

        headers = ['Description', 'Nil Rated Supplies',
                   'Exempted(other than nil rated/non GST supply)', 'Non-GST Supplies']
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, h)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color="FFFFFF", end_color='FFFFFF')
        
        ws['A5'] = "Inter-State supplies to registered persons"
        ws['A6'] = "Intra-State supplies to registered persons"
        ws['A7'] = "Inter-State supplies to unregistered persons"
        ws['A8'] = "Intra-State supplies to unregistered persons"
    
    def create_hsn_b2b_sheet(self, wb, data):
        ws = wb.create_sheet("hsn(b2b)")
        ws['A1'] = "Summary For HSN(12)"
        ws['A1'].font = Font(bold=False, size=12)
        ws['H3'] = '0'
        ws['K3'] = '0'
        
        expanded_items = []
        for _, invoice in data.iterrows():
            items = self.parse_comma_separated(invoice['Items_Name'])
            hsns = self.parse_comma_separated(invoice['HSN_CODE'])
            qtys = self.parse_comma_separated(invoice['Quantity'])
            taxables = self.parse_comma_separated(invoice['Taxable_Amount'])
            cgsts = self.parse_comma_separated(invoice['CGST'])
            sgsts = self.parse_comma_separated(invoice['SGST'])
            igsts = self.parse_comma_separated(invoice['IGST'])
            
            for i in range(max(len(items), len(hsns))):
                item_data = {
                    'HSN': hsns[i] if i < len(hsns) else '',
                    'Quantity': self.safe_float(qtys[i] if i < len(qtys) else 0),
                    'Taxable_Amount': self.safe_float(taxables[i] if i < len(taxables) else 0),
                    'CGST': self.safe_float(cgsts[i] if i < len(cgsts) else 0),
                    'SGST': self.safe_float(sgsts[i] if i < len(sgsts) else 0),
                    'IGST': self.safe_float(igsts[i] if i < len(igsts) else 0)
                }
                item_data['Total_Value'] = (item_data['Taxable_Amount'] + 
                                           item_data['CGST'] + item_data['SGST'] + item_data['IGST'])
                expanded_items.append(item_data)
        
        if expanded_items:
            items_df = pd.DataFrame(expanded_items)
            hsn_summary = items_df.groupby('HSN').agg({
                'Quantity': 'sum', 'Total_Value': 'sum', 'Taxable_Amount': 'sum',
                'CGST': 'sum', 'SGST': 'sum', 'IGST': 'sum'
            }).reset_index()
        else:
            hsn_summary = pd.DataFrame()
        
        if not hsn_summary.empty:
            ws['A2'] = "No. of HSN"
            ws['E2'] = "Total Value"
            ws['G2'] = "Total Taxable Value"
            ws['H2'] = "Total Integrated Tax"
            ws['I2'] = "Total Central Tax"
            ws['J2'] = "Total State/UT Tax"
            
            ws['A3'] = len(hsn_summary)
            ws['E3'] = hsn_summary['Total_Value'].sum()
            ws['G3'] = hsn_summary['Taxable_Amount'].sum()
            ws['H3'] = hsn_summary['IGST'].sum()
            ws['I3'] = hsn_summary['CGST'].sum()
            ws['J3'] = hsn_summary['SGST'].sum()
            
            for cell in [ws['E3'], ws['G3'], ws['H3'], ws['I3'], ws['J3']]:
                cell.number_format = '#,##0.00'
        
        headers = ['HSN', 'Description', 'UQC', 'Total Quantity', 'Total Value',
                   'Rate', 'Taxable Value', 'Integrated Tax', 'Central Tax', 
                   'State/UT Tax', 'Cess Amount']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, header)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        row_idx = 5
        for _, hsn_row in hsn_summary.iterrows():
            ws.cell(row_idx, 1, hsn_row['HSN'])
            ws.cell(row_idx, 2, '')
            ws.cell(row_idx, 3, 'OTH-OTHERS')
            ws.cell(row_idx, 4, hsn_row['Quantity'])
            ws.cell(row_idx, 5, hsn_row['Total_Value'])
            
            if hsn_row['Taxable_Amount'] > 0:
                rate = (hsn_row['IGST'] / hsn_row['Taxable_Amount'] * 100) if hsn_row['IGST'] > 0 else \
                       ((hsn_row['CGST'] + hsn_row['SGST']) / hsn_row['Taxable_Amount'] * 100)
            else:
                rate = 0
            
            ws.cell(row_idx, 6, rate)
            ws.cell(row_idx, 7, hsn_row['Taxable_Amount'])
            ws.cell(row_idx, 8, hsn_row['IGST'])
            ws.cell(row_idx, 9, hsn_row['CGST'])
            ws.cell(row_idx, 10, hsn_row['SGST'])
            ws.cell(row_idx, 11, 0)
            
            ws.cell(row_idx, 4).number_format = '#,##0'
            ws.cell(row_idx, 5).number_format = '#,##0.00'
            ws.cell(row_idx, 6).number_format = '0.00'
            ws.cell(row_idx, 7).number_format = '#,##0.00'
            ws.cell(row_idx, 8).number_format = '#,##0.00'
            ws.cell(row_idx, 9).number_format = '#,##0.00'
            ws.cell(row_idx, 10).number_format = '#,##0.00'
            ws.cell(row_idx, 11).number_format = '#,##0.00'
            
            row_idx += 1
        
        for col in range(1, 12):
            ws.column_dimensions[get_column_letter(col)].width = 14
    
    def create_hsn_b2c_template(self, wb):
        ws = wb.create_sheet("hsn(b2c)")
        ws['A1'] = "Summary For HSN(12)"
        ws['A1'].font = Font(bold=False, size=11)
        ws['A3'] = '0'
        ws['E3'] = '0'
        ws['G3'] = '0'
        
        ws['A2'] = "No. of HSN"
        ws['E2'] = "Total Value"
        ws['G2'] = "Total Taxable Value"
        ws['H2'] = "Total Integrated Tax"
        ws['I2'] = "Total Central Tax"
        ws['J2'] = "Total State/UT Tax"
        
        headers = ['HSN', 'Description', 'UQC', 'Total Quantity', 'Total Value',
                   'Rate', 'Taxable Value', 'Integrated Tax Amount',
                   'Central Tax Amount', 'State/UT Tax Amount', 'Cess Amount']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, header)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
    
    def create_item_summary_sheet(self, wb, data):
        ws = wb.create_sheet("itemSummary")
        ws['A1'] = "Summary For Items"
        ws['A1'].font = Font(bold=False, size=12)
        
        expanded_items = []
        for _, invoice in data.iterrows():
            items = self.parse_comma_separated(invoice['Items_Name'])
            hsns = self.parse_comma_separated(invoice['HSN_CODE'])
            qtys = self.parse_comma_separated(invoice['Quantity'])
            taxables = self.parse_comma_separated(invoice['Taxable_Amount'])
            cgsts = self.parse_comma_separated(invoice['CGST'])
            sgsts = self.parse_comma_separated(invoice['SGST'])
            igsts = self.parse_comma_separated(invoice['IGST'])
            
            for i in range(max(len(items), len(hsns))):
                item_name = items[i] if i < len(items) else ''
                if not item_name:
                    continue
                
                item_data = {
                    'Item_Name': item_name,
                    'HSN': hsns[i] if i < len(hsns) else '',
                    'Quantity': self.safe_float(qtys[i] if i < len(qtys) else 0),
                    'Taxable_Amount': self.safe_float(taxables[i] if i < len(taxables) else 0),
                    'CGST': self.safe_float(cgsts[i] if i < len(cgsts) else 0),
                    'SGST': self.safe_float(sgsts[i] if i < len(sgsts) else 0),
                    'IGST': self.safe_float(igsts[i] if i < len(igsts) else 0)
                }
                item_data['Total_Value'] = (item_data['Taxable_Amount'] + 
                                           item_data['CGST'] + item_data['SGST'] + item_data['IGST'])
                expanded_items.append(item_data)
        
        if expanded_items:
            items_df = pd.DataFrame(expanded_items)
            item_summary = items_df.groupby(['Item_Name', 'HSN']).agg({
                'Quantity': 'sum', 'Total_Value': 'sum', 'Taxable_Amount': 'sum',
                'CGST': 'sum', 'SGST': 'sum', 'IGST': 'sum'
            }).reset_index()
        else:
            item_summary = pd.DataFrame()
        
        if not item_summary.empty:
            ws['A2'] = "No. of Items"
            ws['E2'] = "Total Value"
            ws['G2'] = "Total Taxable Value"
            ws['H2'] = "Total Integrated Tax"
            ws['I2'] = "Total Central Tax"
            ws['J2'] = "Total State/UT Tax"
            
            ws['A3'] = len(item_summary)
            ws['E3'] = item_summary['Total_Value'].sum()
            ws['G3'] = item_summary['Taxable_Amount'].sum()
            ws['H3'] = item_summary['IGST'].sum()
            ws['I3'] = item_summary['CGST'].sum()
            ws['J3'] = item_summary['SGST'].sum()
            
            for cell in [ws['E3'], ws['G3'], ws['H3'], ws['I3'], ws['J3']]:
                cell.number_format = '#,##0.00'
        
        headers = ['HSN', 'Description', 'UQC', 'Total Quantity', 'Total Value',
                   'Rate', 'Taxable Value', 'Integrated Tax', 'Central Tax',
                   'State/UT Tax', 'Cess Amount']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, header)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        row_idx = 5
        for _, item in item_summary.iterrows():
            ws.cell(row_idx, 1, item['HSN'])
            ws.cell(row_idx, 2, item['Item_Name'])
            ws.cell(row_idx, 3, 'OTH-OTHERS')
            ws.cell(row_idx, 4, item['Quantity'])
            ws.cell(row_idx, 5, item['Total_Value'])
            
            if item['Taxable_Amount'] > 0:
                rate = (item['IGST'] / item['Taxable_Amount'] * 100) if item['IGST'] > 0 else \
                       ((item['CGST'] + item['SGST']) / item['Taxable_Amount'] * 100)
            else:
                rate = 0
            
            ws.cell(row_idx, 6, rate)
            ws.cell(row_idx, 7, item['Taxable_Amount'])
            ws.cell(row_idx, 8, item['IGST'])
            ws.cell(row_idx, 9, item['CGST'])
            ws.cell(row_idx, 10, item['SGST'])
            ws.cell(row_idx, 11, 0)
            
            ws.cell(row_idx, 4).number_format = '#,##0'
            ws.cell(row_idx, 5).number_format = '#,##0.00'
            ws.cell(row_idx, 6).number_format = '0.00'
            ws.cell(row_idx, 7).number_format = '#,##0.00'
            ws.cell(row_idx, 8).number_format = '#,##0.00'
            ws.cell(row_idx, 9).number_format = '#,##0.00'
            ws.cell(row_idx, 10).number_format = '#,##0.00'
            ws.cell(row_idx, 11).number_format = '#,##0.00'
            
            row_idx += 1
        
        for col in range(1, 12):
            ws.column_dimensions[get_column_letter(col)].width = 16
        ws.column_dimensions['B'].width = 30
    
    def create_docs_sheet(self, wb, data, from_date, to_date):
        ws = wb.create_sheet("docs")
        
        ws['A1'] = "Summary of documents issued during the tax period (13)"
        ws['A1'].font = Font(bold=False, size=12)
        
        invoice_numbers = data['Invoice_No'].tolist()
        
        if invoice_numbers:
            first_invoice = invoice_numbers[0]
            last_invoice = invoice_numbers[-1]
            total_number = len(invoice_numbers)
        else:
            first_invoice = last_invoice = ""
            total_number = 0
        
        ws['D2'] = "Total Number"
        ws['E2'] = "Total Cancelled"
        ws['D3'] = total_number
        ws['E3'] = 0
        
        headers = ['Nature of Document', 'Sr. No. From', 'Sr. No. To', 'Total Number', 'Cancelled']
        
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(4, col_idx, header)
            cell.font = Font(bold=False)
            cell.fill = PatternFill(start_color='FFFFFF', end_color='FFFFFF')
        
        ws['A5'] = "Invoices for outward supply"
        ws['B5'] = first_invoice
        ws['C5'] = last_invoice
        ws['D5'] = total_number
        ws['E5'] = 0
        
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 20
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 15

if __name__ == "__main__":
    try:
        app = GSTR1Generator()
        app.mainloop()
    except Exception as e:
        print(f"\nFatal Error: {e}")
        traceback.print_exc()
        input("\nPress Enter to exit...")