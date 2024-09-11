import fitz
from PyQt5.QtWidgets import QMainWindow, QMenu, QAction, QFileDialog
from PyQt5 import QtCore

class Menu:
    def __init__(self, parent):
        self.parent = parent  # Reference to PDFReader instance

    def init_menu(self):
        """Initialize the menu and add it to the parent."""
        menubar = self.parent.menuBar()  # Get the menubar from the parent (PDFReader)

        # File menu
        menuFile = menubar.addMenu('File')
        open_pdf_action = QAction("Open PDF", self.parent)
        open_pdf_action.setStatusTip("Select a new PDF file to open")
        open_pdf_action.triggered.connect(self.parent.load_pdf)  # Use parent's load_pdf method
        open_pdf_action.setShortcut("Ctrl+O")
        menuFile.addAction(open_pdf_action)

        # View menu
        menuView = menubar.addMenu('View')
        zoom_in_action = QAction("Zoom In", self.parent)
        zoom_in_action.setStatusTip("Increase page scale")
        zoom_in_action.setShortcut("Ctrl++")
        zoom_in_action.triggered.connect(self.parent.zoom_in)
        menuView.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self.parent)
        zoom_out_action.setStatusTip("Decrease page scale")
        zoom_out_action.setShortcut("Ctrl+-")
        zoom_out_action.triggered.connect(self.parent.zoom_out)
        menuView.addAction(zoom_out_action)

        page_prev_action = QAction("Previous Page", self.parent)
        page_prev_action.setStatusTip("Move to previous page")
        page_prev_action.setShortcut(QtCore.Qt.Key_Left)
        page_prev_action.triggered.connect(self.parent.prev_page)
        menuView.addAction(page_prev_action)

        page_next_action = QAction("Next Page", self.parent)
        page_next_action.setStatusTip("Move to next page")
        page_next_action.setShortcut(QtCore.Qt.Key_Right)
        page_next_action.triggered.connect(self.parent.next_page)
        menuView.addAction(page_next_action)

        # Add menus to the menubar
        menubar.addMenu(menuFile)
        menubar.addMenu(menuView)