import fitz
import pyautogui
from PyQt5.QtWidgets import QMainWindow, QLabel, QScrollArea, QMenu, QFileDialog, QAction, QListWidget, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QFont, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint
from dictionary import JMDict
from menu import Menu
import re

class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scale_mod = 1

        self.setWindowTitle('PDF Reader with Dictionary')
        self.setGeometry(100, 100, 720, 720)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.scroll_area)

        self.pdf_label = PDFLabel(self)
        self.pdf_label.setAlignment(Qt.AlignCenter)
        self.scroll_area.setWidget(self.pdf_label)

        self.dictionary = JMDict('./JMdict.xml')

        self.context_menu = QMenu(self)
        self.search_action = QAction("Search in Dictionary", self)
        self.highlight_action = QAction("Highlight Selection", self)

        self.search_action.triggered.connect(self.search_selected_text)
        self.highlight_action.triggered.connect(self.highlight_selection)

        self.context_menu.addAction(self.search_action)
        self.context_menu.addAction(self.highlight_action)

        self.selection_rect = None
        self.doc = None
        self.scale_factor = 1  # Initialize scale_factor

        self.show()

        self.menu = Menu(self)
        self.menu.init_menu()

        self.load_pdf()

    def highlight_selection(self):
        """Highlight the selected text on the PDF page."""
        if not self.pdf_label.selection_rect:
            return

        # Load the current page
        page = self.doc.load_page(self.current_page)

        # Adjust selection rectangle to PDF coordinates, including scroll offsets
        scroll_x = self.scroll_area.horizontalScrollBar().value()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        rect = self.pdf_label.selection_rect

        # Screen coordinates (on the label)
        x0_screen = rect.left() + scroll_x
        y0_screen = rect.top() + scroll_y
        x1_screen = rect.right() + scroll_x
        y1_screen = rect.bottom() + scroll_y

        # Map screen coordinates to PDF coordinates
        x0_pdf = x0_screen / self.scale_factor
        y0_pdf = y0_screen / self.scale_factor
        x1_pdf = x1_screen / self.scale_factor
        y1_pdf = y1_screen / self.scale_factor

        # Create a rectangle in PDF coordinates
        pdf_rect = fitz.Rect(x0_pdf, y0_pdf, x1_pdf, y1_pdf)

        # Add highlight annotation to the rectangle
        annot = page.add_highlight_annot(pdf_rect)
        annot.set_colors(stroke=fitz.utils.getColor('yellow'))
        annot.update()

        # Re-render the page to show the highlight
        self.show_page(self.current_page)

    def show_page(self, page_number):
        """Display the specified PDF page with the current zoom level."""
        page = self.doc.load_page(page_number)

        # Calculate the base scale factor to fit the page width to the window width
        window_width = self.scroll_area.viewport().width()
        page_width = page.rect.width
        base_scale = window_width / page_width

        # Calculate the total scale factor including zoom level
        self.scale_factor = base_scale * self.scale_mod

        # Generate the pixmap with the total scaling
        pix = page.get_pixmap(
            matrix=fitz.Matrix(self.scale_factor, self.scale_factor),
            annots=True  # Include annotations
        )
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pdf_label.setPixmap(QPixmap.fromImage(img))
        self.resize_to_fit()

    def resize_to_fit(self):
        """Ensure the page is centered in the window."""
        self.pdf_label.adjustSize()

    def resizeEvent(self, event):
        """Resize the PDF page when the window is resized."""
        if self.doc is not None:
            self.show_page(self.current_page)
        super().resizeEvent(event)

    def get_selected_text(self):
        """Extract the selected text based on the selection rectangle."""
        if not self.pdf_label.selection_rect:
            return None

        # Load the current page
        page = self.doc.load_page(self.current_page)

        # Adjust selection rectangle to PDF coordinates, including scroll offsets
        scroll_x = self.scroll_area.horizontalScrollBar().value()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        rect = self.pdf_label.selection_rect

        # Screen coordinates (on the label)
        x0_screen = rect.left() + scroll_x
        y0_screen = rect.top() + scroll_y
        x1_screen = rect.right() + scroll_x
        y1_screen = rect.bottom() + scroll_y

        # Map screen coordinates to PDF coordinates
        x0_pdf = x0_screen / self.scale_factor
        y0_pdf = y0_screen / self.scale_factor
        x1_pdf = x1_screen / self.scale_factor
        y1_pdf = y1_screen / self.scale_factor

        # Extract text from the selected region
        selected_text = page.get_text("text", clip=fitz.Rect(x0_pdf, y0_pdf, x1_pdf, y1_pdf))

        return selected_text.strip() if selected_text else None

    def search_selected_text(self):
        """Search the selected text in the dictionary."""
        selected_text = self.get_selected_text()
        if selected_text:
            clean_text = self.clean_word(selected_text)
            words = self.split_into_possible_words(clean_text)
            if words:
                self.show_word_list(words)

    def clean_word(self, word):
        """Clean and normalize the extracted word for Japanese word lookup."""
        word = re.sub(r'[^\u3040-\u30FF\u4E00-\u9FAF]', '', word)
        return word

    def split_into_possible_words(self, text):
        """Split the text into individual words."""
        words = []
        length = len(text)

        for start in range(length):
            for end in range(start + 1, length + 1):
                candidate_word = text[start:end]
                if self.dictionary.search_word(candidate_word):
                    words.append(candidate_word)
        return words

    def show_word_list(self, words):
        """Show a list of possible words from the selection to choose one for full details."""
        winSize = 300

        word_list = QListWidget()
        word_list.addItems(words)

        font = QFont()
        font.setPointSize(15)
        word_list.setFont(font)

        def word_selected():
            selected_word = word_list.currentItem().text()
            self.show_definition(selected_word)

        word_list.itemClicked.connect(word_selected)
        word_list.setWindowTitle("Select a Word")
        word_list.setGeometry(200, 200, winSize, winSize)
        word_list.show()

    def show_definition(self, word):
        """Show the dictionary definition in a pop-up."""
        entries = self.dictionary.search_word(word)

        if entries:
            result_text = ""
            for entry in entries:
                word_text = entry.get("word", "")
                reading = entry.get("reading", "")
                tags = entry.get("tags", "")

                result_text += f"Word: {word_text}\n"
                result_text += f"Reading: {reading}\n"
                result_text += f"Tags: {tags}\n\n"

                meanings = entry.get("meaning", [])
                if meanings:
                    result_text += "Meanings:\n"
                    for meaning in meanings:
                        result_text += f"- {meaning}\n"
                else:
                    result_text += "Meanings: None\n"

                s_inf = entry.get("notes", [])
                if s_inf:
                    result_text += "Other Info:\n"
                    for example in s_inf:
                        result_text += f"- {example}\n"
                    else:
                        result_text += "Other Info: None\n"

                result_text += "\n---\n"

        else:
            result_text = "Word not found."

        msg = QMessageBox()
        msg.setWindowTitle("Dictionary Entry")
        msg.setText(result_text)
        msg.exec_()

    def show_message(self, text, title):
        """Show a simple pop-up message."""
        msg = QMessageBox()
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.exec_()

    def keyPressEvent(self, event):
        """Handle page scrolling with arrow keys."""
        if event.key() == Qt.Key_Right:
            self.next_page()
        elif event.key() == Qt.Key_Left:
            self.prev_page()

    # Menu Functions

    def zoom_in(self):
        """Increase the zoom level."""
        self.scale_mod += 0.1
        self.show_page(self.current_page)

    def zoom_out(self):
        """Decrease the zoom level."""
        if self.scale_mod > 0.2:
            self.scale_mod -= 0.1
            self.show_page(self.current_page)

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

    def load_pdf(self):
        """Load the PDF and show only the first page."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF Files (*.pdf)", options=options)
        if file_path:
            self.doc = fitz.open(file_path)
            self.current_page = 0
            self.show_page(self.current_page)

class PDFLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Reference to PDFReader
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        self.begin = QPoint()
        self.end = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selection_start = event.pos()
            self.begin = event.pos()
            self.end = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self.selection_start:
            self.selection_end = event.pos()
            self.selection_rect = QRect(self.selection_start, self.selection_end)
            self.end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selection_rect:
            selected_text = self.main_window.get_selected_text()
            if selected_text:
                self.main_window.context_menu.exec_(event.globalPos())
                self.begin = QPoint()
                self.end = QPoint()
            else:
                self.main_window.show_message("No valid text selected.", "Selection Error")
            # Clear the selection after using it
            self.selection_start = None
            self.selection_end = None
            self.selection_rect = None
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.selection_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            br = QBrush(QColor(0, 0, 255, 50))
            painter.setBrush(br)
            painter.setPen(QPen(QColor(0, 0, 255), 1))
            painter.drawRect(QRect(self.begin, self.end))
