"""Quick smoke test — verify all Phase 2 imports resolve."""
import sys
sys.path.insert(0, "/Users/admin/Desktop/gst/gst_billing")

from config import APP_NAME
from database.connection import get_db
from database.migrations import initialise_database
from database.seed_data import seed_all
from ui.styles import get_stylesheet
from ui.widgets.sidebar import Sidebar
from ui.widgets.search_bar import SearchBar
from ui.widgets.date_picker import DatePicker
from ui.widgets.currency_input import CurrencyInput
from ui.widgets.gstin_input import GSTINInput
from ui.widgets.status_badge import StatusBadge
from ui.widgets.item_grid import ItemGrid
from ui.dialogs.customer_picker import CustomerPickerDialog
from ui.dialogs.product_picker import ProductPickerDialog
from ui.wizards.first_run_wizard import FirstRunWizard
from ui.pages.document_editor import DocumentEditor
from ui.pages.document_list import DocumentListPage
from ui.pages.customer_manager import CustomerManagerPage
from ui.pages.product_manager import ProductManagerPage
from ui.pages.purchase_tracker import PurchaseTrackerPage
from ui.pages.placeholder_pages import (
    DashboardPage, Gstr1Page, ReportsPage,
)
from ui.pages.settings_page import SettingsPage
from services.excel_io import export_to_excel, import_from_excel
from ui.main_window import MainWindow

print("All imports successful!")
print(f"  App: {APP_NAME}")
ss = get_stylesheet("light", "#1565C0")
print(f"  Stylesheet: {len(ss)} chars")
