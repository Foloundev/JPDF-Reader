import fitz
import pyautogui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QScrollArea, QMenu, QFileDialog, QAction, QListWidget, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QWidget
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
        self.setCentralWidget(self.scroll_area)

        self.pdf_label = PDFLabel(self)

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.container = QWidget()
        self.container.setLayout(self.layout)

        self.layout.addWidget(self.pdf_label)
        self.scroll_area.setWidget(self.container)

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
        if not self.pdf_label.selection_rect:
            return

        page = self.doc.load_page(self.current_page)
        rect = self.pdf_label.selection_rect

        # Map the selection rectangle coordinates to PDF coordinates
        x0_pixmap = rect.left()
        y0_pixmap = rect.top()
        x1_pixmap = rect.right()
        y1_pixmap = rect.bottom()

        # Map pixmap coordinates to PDF coordinates
        x0_pdf = x0_pixmap / self.scale_factor
        y0_pdf = y0_pixmap / self.scale_factor
        x1_pdf = x1_pixmap / self.scale_factor
        y1_pdf = y1_pixmap / self.scale_factor

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

        # Calculate the base scale factor to fit the page width to the viewport width
        viewport_width = self.scroll_area.viewport().width()
        page_width = page.rect.width
        base_scale = viewport_width / page_width

        # Calculate the total scale factor including zoom level
        self.scale_factor = base_scale * self.scale_mod

        # Generate the pixmap with the total scaling
        pix = page.get_pixmap(
            matrix=fitz.Matrix(self.scale_factor, self.scale_factor),
            annots=True  # Include annotations
        )

        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pdf_label.setPixmap(QPixmap.fromImage(img))

        # Adjust the label size
        self.pdf_label.resize(pix.width, pix.height)

        # Ensure the scroll area resizes the widget
        self.scroll_area.setWidgetResizable(True)

    def resize_to_fit(self):
        """Ensure the page is centered in the window."""
        self.pdf_label.adjustSize()

    def resizeEvent(self, event):
        """Resize the PDF page when the window is resized."""
        if self.doc is not None:
            self.show_page(self.current_page)
        super().resizeEvent(event)

    def get_selected_text(self):
        if not self.pdf_label.selection_rect:
            return None

        page = self.doc.load_page(self.current_page)
        rect = self.pdf_label.selection_rect

        # Adjust rectangle coordinates
        x0 = rect.left() - self.pdf_label.get_label_position()[0] - self.scroll_area.horizontalScrollBar().value()
        y0 = rect.top() - self.pdf_label.get_label_position()[1] - self.scroll_area.verticalScrollBar().value()
        x1 = rect.right() - self.pdf_label.get_label_position()[0] - self.scroll_area.horizontalScrollBar().value()
        y1 = rect.bottom() - self.pdf_label.get_label_position()[1] - self.scroll_area.verticalScrollBar().value()

        # Map to PDF coordinates
        x0_pdf = x0 / self.scale_factor
        y0_pdf = y0 / self.scale_factor
        x1_pdf = x1 / self.scale_factor
        y1_pdf = y1 / self.scale_factor

        selected_text = page.get_text("text", clip=fitz.Rect(x0_pdf, y0_pdf, x1_pdf, y1_pdf))
        self.last_selected_text = selected_text.strip() if selected_text else None
        return self.last_selected_text

    def search_selected_text(self):
        """Search the selected text in the dictionary."""
        selected_text = self.get_selected_text()
        if selected_text:
            clean_text = self.clean_word(selected_text)
            words = self.split_into_possible_words(clean_text)
            if words:
                self.show_word_list(words, selected_text)


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

    def show_word_list(self, words, selected_text):
        """Show a list of possible words from the selection to choose one for full details."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Select a Word")
        dialog.setGeometry(200, 200, 300, 400)

        layout = QVBoxLayout()

        word_list = QListWidget()
        word_list.addItems(words)

        font = QFont()
        font.setPointSize(30)
        word_list.setFont(font)

        layout.addWidget(word_list)

        button_layout = QHBoxLayout()

        copy_button = QPushButton("Copy")
        button_layout.addWidget(copy_button)

        close_button = QPushButton("Close")
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        def word_selected():
            selected_word = word_list.currentItem().text()
            self.show_definition(selected_word)

        word_list.itemClicked.connect(word_selected)

        # Copy button functionality
        def copy_selected_text():
            clipboard = QApplication.clipboard()
            clipboard.setText(selected_text)
            QMessageBox.information(self, "Copied", "Selected text copied to clipboard.")

        copy_button.clicked.connect(copy_selected_text)
        close_button.clicked.connect(dialog.close)

        dialog.exec_()


    def show_definition(self, word):
        """Show the dictionary definition in a pop-up."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit

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

        dialog = QDialog(self)
        dialog.setWindowTitle("Dictionary Entry")
        dialog.setGeometry(200, 200, 400, 400)

        layout = QVBoxLayout()

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(result_text)
        layout.addWidget(text_edit)
        
        font = QFont()
        font.setPointSize(20)
        text_edit.setFont(font)

        button_layout = QHBoxLayout()

        copy_button = QPushButton("Copy")
        button_layout.addWidget(copy_button)

        close_button = QPushButton("Close")
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        # Copy button functionality
        def copy_word():
            clipboard = QApplication.clipboard()
            clipboard.setText(word)
            QMessageBox.information(self, "Copied", f"'{word}' copied to clipboard.")

        copy_button.clicked.connect(copy_word)
        close_button.clicked.connect(dialog.close)

        dialog.exec_()

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            label_x, label_y = self.get_label_position()
            scroll_x = self.main_window.scroll_area.horizontalScrollBar().value()
            scroll_y = self.main_window.scroll_area.verticalScrollBar().value()
            pos_x = event.pos().x() + label_x + scroll_x
            pos_y = event.pos().y() + label_y + scroll_y
            self.selection_start = QPoint(int(pos_x), int(pos_y))
            self.update()


    def mouseMoveEvent(self, event):
        if self.selection_start:
            label_x, label_y = self.get_label_position()
            scroll_x = self.main_window.scroll_area.horizontalScrollBar().value()
            scroll_y = self.main_window.scroll_area.verticalScrollBar().value()
            pos_x = label_x + event.pos().x() + scroll_x
            pos_y = label_y + event.pos().y() + scroll_y
            self.selection_end = QPoint(pos_x, pos_y)
            self.selection_rect = QRect(self.selection_start, self.selection_end)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.selection_rect:
            label_x, label_y = self.get_label_position()
            scroll_x = self.main_window.scroll_area.horizontalScrollBar().value()
            scroll_y = self.main_window.scroll_area.verticalScrollBar().value()
            pos_x = label_x + event.pos().x() + scroll_x
            pos_y = label_y + event.pos().y() + scroll_y
            self.selection_end = QPoint(pos_x, pos_y)
            self.selection_rect = QRect(self.selection_start, self.selection_end)
            selected_text = self.main_window.get_selected_text()
            if selected_text:
                self.main_window.context_menu.exec_(event.globalPos())
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

            # Get positions
            label_x, label_y = self.get_label_position()
            scroll_x = self.main_window.scroll_area.horizontalScrollBar().value()
            scroll_y = self.main_window.scroll_area.verticalScrollBar().value()

            # Adjust selection start and end positions
            x0 = self.selection_start.x() - label_x - scroll_x
            y0 = self.selection_start.y() - label_y - scroll_y
            x1 = self.selection_end.x() - label_x - scroll_x
            y1 = self.selection_end.y() - label_y - scroll_y

            # Create QRect with adjusted positions
            rect = QRect(int(x0), int(y0), int(x1 - x0), int(y1 - y0))
            painter.drawRect(rect)
            painter.end()
    def get_label_position(self):
        """Get the position of the label within the scroll area's viewport."""
        pos = self.mapTo(self.main_window.scroll_area.viewport(), QPoint(0, 0))
        return pos.x(), pos.y()

    