import fitz  # PyMuPDF for PDF rendering
from PyQt5.QtWidgets import QMainWindow, QLabel, QScrollArea, QMenu, QFileDialog, QAction, QListWidget, QMessageBox, QHBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect
from dictionary import JMDict
import re

class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF Reader with Dictionary')
        self.setGeometry(100, 100, 800, 600)

        # Scroll area to handle PDF navigation
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.scroll_area)

        # PDF page display
        self.pdf_label = QLabel()
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.pdf_label)

        # Navigation buttons
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)

        # Layout for buttons
        self.nav_widget = QWidget()
        self.nav_layout = QHBoxLayout(self.nav_widget)
        self.nav_layout.addWidget(self.prev_button)
        self.nav_layout.addWidget(self.next_button)
        self.nav_widget.setParent(self)
        self.nav_widget.setGeometry(10, 10, 150, 50)

        # Context menu for dictionary lookup
        self.context_menu = QMenu(self)
        self.search_action = QAction("Search in Dictionary", self)
        self.search_action.triggered.connect(self.search_selected_text)
        self.context_menu.addAction(self.search_action)

        # Dictionary loading (adjust paths to your files)
        self.dictionary = JMDict('jmdict/tag_bank_1.json', [f'jmdict/term_bank_{i}.json' for i in range(1, 51)])

        # Variables for handling selection
        self.selection_start = None
        self.selection_rect = None
        self.doc = None  # PDF document
        self.current_page = 0  # Track the current page
        self.scale_factor = 1.0  # Track scaling factor for proper text selection

        # Load the PDF file
        self.load_pdf()

    def load_pdf(self):
        """Open and load the PDF."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)", options=options)
        if file_path:
            self.doc = fitz.open(file_path)
            self.current_page = 0
            self.show_page(self.current_page)

    def show_page(self, page_number):
        """Render and display the specified PDF page."""
        if self.doc is None or page_number < 0 or page_number >= len(self.doc):
            return
        page = self.doc.load_page(page_number)
        
        # Adjust scale based on the window size
        self.scale_factor = self.get_scale_factor(page)
        
        pix = page.get_pixmap(matrix=fitz.Matrix(self.scale_factor, self.scale_factor))  # Apply scaling
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pdf_label.setPixmap(QPixmap.fromImage(img))

    def get_scale_factor(self, page):
        """Calculate the scale factor based on window size and PDF page size."""
        window_width = self.scroll_area.viewport().width()
        page_width = page.rect.width
        return window_width / page_width

    def next_page(self):
        """Go to the next page."""
        if self.doc is not None and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.show_page(self.current_page)

    def prev_page(self):
        """Go to the previous page."""
        if self.doc is not None and self.current_page > 0:
            self.current_page -= 1
            self.show_page(self.current_page)

    def mousePressEvent(self, event):
        """Begin selection on mouse press."""
        if event.button() == Qt.LeftButton:
            self.selection_start = event.pos()

    def mouseMoveEvent(self, event):
        """Update the selection rectangle during dragging."""
        if self.selection_start:
            self.selection_rect = QRect(self.selection_start, event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        """Handle text selection and display the context menu."""
        if event.button() == Qt.LeftButton and self.selection_rect:
            selected_text = self.get_selected_text()
            if selected_text:
                self.context_menu.exec_(event.globalPos())
            else:
                self.show_message("No text selected.")
            self.selection_start = None
            self.selection_rect = None
            self.update()

    def get_selected_text(self):
        """Extract the selected text from the PDF."""
        if not self.selection_rect:
            return None
        page = self.doc.load_page(self.current_page)

        # Convert selection rectangle from screen to PDF coordinates
        scroll_x = self.scroll_area.horizontalScrollBar().value()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Adjust for scroll and scale
        x0 = (self.selection_rect.left() + scroll_x) / self.scale_factor
        y0 = (self.selection_rect.top() + scroll_y) / self.scale_factor
        x1 = (self.selection_rect.right() + scroll_x) / self.scale_factor
        y1 = (self.selection_rect.bottom() + scroll_y) / self.scale_factor

        # Extract text from the selected area
        selected_text = page.get_text("text", clip=fitz.Rect(x0, y0, x1, y1))
        print(f"Selected text: {selected_text.strip()}")
        return selected_text.strip()

    def search_selected_text(self):
        """Search the selected text in the dictionary."""
        selected_text = self.get_selected_text()
        if selected_text:
            clean_text = self.clean_word(selected_text)
            words = self.dictionary.search_word(clean_text)
            if words:
                self.show_word_list(words)

    def clean_word(self, word):
        """Clean and normalize the selected text."""
        return re.sub(r'[^\u3040-\u30FF\u4E00-\u9FAF]', '', word)

    def show_word_list(self, words):
        """Show possible dictionary words in a list."""
        word_list = QListWidget()
        for word in words:
            word_list.addItem(f"{word['word']} ({word['reading']})")

        word_list.itemClicked.connect(lambda item: self.show_definition(item.text()))
        word_list.setWindowTitle("Select a Word")
        word_list.setGeometry(100, 100, 300, 200)
        word_list.show()

    def show_definition(self, word):
        """Show the dictionary definition for the selected word."""
        entries = self.dictionary.search_word(word)
        if entries:
            result_text = "\n\n".join([f"Word: {entry['word']}\nReading: {entry['reading']}\nTags: {entry['tags']}\nMeanings:\n{', '.join(entry['meaning'])}\nExamples:\n{', '.join(entry['examples'])}" for entry in entries])
        else:
            result_text = "No dictionary entry found."
        msg = QMessageBox()
        msg.setWindowTitle("Dictionary Entry")
        msg.setText(result_text)
        msg.exec_()

    def show_message(self, text):
        """Show an error message."""
        msg = QMessageBox()
        msg.setWindowTitle("Error")
        msg.setText(text)
        msg.exec_()

    def paintEvent(self, event):
        """Draw the blue highlight box over the selected text."""
        super().paintEvent(event)
        if self.selection_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # Draw a blue rectangle for selection highlight
            painter.fillRect(self.selection_rect, QColor(173, 216, 230, 120))  # Light blue with transparency
            painter.setPen(QPen(QColor(0, 0, 255), 2))  # Blue solid border
            painter.drawRect(self.selection_rect)

    def resizeEvent(self, event):
        """Handle window resizing and recalculate scale factor."""
        if self.doc is not None:
            self.show_page(self.current_page)
