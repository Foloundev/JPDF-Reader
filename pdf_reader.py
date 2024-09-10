import fitz  # PyMuPDF for PDF rendering
from PyQt5.QtWidgets import QMainWindow, QLabel, QScrollArea, QMenu, QFileDialog, QPushButton, QHBoxLayout, QWidget, QAction, QListWidget, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
from PyQt5.QtCore import Qt, QRect, QRectF
from dictionary import JMDict
import re
import keyboard

class PDFReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PDF Reader with Dictionary')
        self.setGeometry(100, 100, 800, 600)

        # Create scroll area to handle PDF page navigation
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.setCentralWidget(self.scroll_area)

        # Create a label to display the PDF page
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
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setWidget(self.pdf_label)
        self.nav_widget.setGeometry(10, 10, 150, 50)
        self.nav_widget.setParent(self)

        # Load the JMDict dictionary (adjust file paths as needed)
        # Load the JMDict dictionary from the XML file
        self.dictionary = JMDict('./jmdict/JMdict.xml')

        # Context menu action to trigger dictionary search on selection
        self.context_menu = QMenu(self)
        self.search_action = QAction("Search in Dictionary", self)
        self.search_action.triggered.connect(self.search_selected_text)
        self.context_menu.addAction(self.search_action)

        # Variables for selection handling
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None
        self.selected_text_rects = []  # Holds rectangles of selected text
        self.doc = None

        # Open a PDF file
        self.load_pdf()

    def load_pdf(self):
        """Load the PDF and show the first page."""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "resources/sample.pdf", "PDF Files (*.pdf)", options=options)
        if file_path:
            self.doc = fitz.open(file_path)
            self.current_page = 0
            self.show_page(self.current_page)

    def show_page(self, page_number):
        """Display the specified PDF page."""
        page = self.doc.load_page(page_number)
        scale_factor = self.get_scale_factor(page)  # Pass the page to get_scale_factor
        pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))  # Apply scaling
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)
        self.pdf_label.setPixmap(QPixmap.fromImage(img))
        self.resize_to_fit()

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

    def resize_to_fit(self):
        """Ensure the page is centered in the window."""
        self.pdf_label.adjustSize()
        self.scroll_area.setWidgetResizable(True)

    def resizeEvent(self, event):
        """Resize the PDF page when the window is resized."""
        if self.doc is not None:
            self.show_page(self.current_page)

        # Update selection when resized
        if self.selection_rect:
            self.update()

    def mousePressEvent(self, event):
        """Start selection area on mouse press."""
        if event.button() == Qt.LeftButton:
            self.selection_start = event.pos()

    def mouseMoveEvent(self, event):
        """Update selection area on mouse drag."""
        if self.selection_start:
            self.selection_end = event.pos()
            self.selection_rect = QRect(self.selection_start, self.selection_end)
            self.update()

    def mouseReleaseEvent(self, event):
        """End selection and show the context menu for dictionary search."""
        if event.button() == Qt.LeftButton and self.selection_rect:
            # Ensure the selected text is valid before showing the dictionary option
            self.selected_text_rects = self.get_selected_text_rects()  # Get selected text rectangles for highlighting
            selected_text = self.get_selected_text()  # For dictionary lookup
            if selected_text:  # Only show the dictionary option if text is selected
                self.context_menu.exec_(event.globalPos())
            else:
                self.show_message("No valid text selected.")
            
            # Clear the selection once the context menu is triggered
            self.selection_start = None
            self.selection_end = None
            self.selection_rect = None
            self.update()

    def get_selected_text_rects(self):
        """Get the rectangles of the selected text for highlighting."""
        if not self.selection_rect:
            return []

        # Get the PDF page corresponding to the current page
        page = self.doc.load_page(self.current_page)

        # Get the displayed image dimensions and the original page dimensions
        pixmap_width = self.pdf_label.pixmap().width()
        pixmap_height = self.pdf_label.pixmap().height()
        page_width = page.rect.width
        page_height = page.rect.height

        # Calculate the scale factor based on the current page size and displayed size
        scale_x = page_width / pixmap_width
        scale_y = page_height / pixmap_height
        
        # Get the current scroll offsets
        scroll_x = self.scroll_area.horizontalScrollBar().value()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Adjust the selection rectangle to match the PDF page's coordinates, applying scroll offsets
        x0 = (self.selection_rect.left() + scroll_x) * scale_x
        y0 = (self.selection_rect.top() + scroll_y) * scale_y
        x1 = (self.selection_rect.right() + scroll_x) * scale_x
        y1 = (self.selection_rect.bottom() + scroll_y) * scale_y

        # Extract text rectangles from the selected region
        text_instances = page.get_text("dict", clip=fitz.Rect(x0, y0, x1, y1))['blocks']

        # Collect rectangles of selected text
        text_rects = []
        for block in text_instances:
            for line in block['lines']:
                for span in line['spans']:
                    text_rects.append(fitz.Rect(span['bbox']))

        return text_rects

    def get_selected_text(self):
        """Extract the selected text based on the selection rectangle."""
        if not self.selection_rect:
            return None

        # Get the PDF page corresponding to the current page
        page = self.doc.load_page(self.current_page)
        
        # Get the displayed image dimensions and the original page dimensions
        pixmap_width = self.pdf_label.pixmap().width()
        pixmap_height = self.pdf_label.pixmap().height()
        page_width = page.rect.width
        page_height = page.rect.height

        # Calculate the scale factor based on the current page size and displayed size
        scale_x = page_width / pixmap_width
        scale_y = page_height / pixmap_height
        
        # Get the current scroll offsets
        scroll_x = self.scroll_area.horizontalScrollBar().value()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Adjust the selection rectangle to match the PDF page's coordinates, applying scroll offsets
        x0 = (self.selection_rect.left() + scroll_x) * scale_x
        y0 = (self.selection_rect.top() + scroll_y) * scale_y
        x1 = (self.selection_rect.right() + scroll_x) * scale_x
        y1 = (self.selection_rect.bottom() + scroll_y) * scale_y

        # Extract the text from the selected region
        selected_text = page.get_text("text", clip=fitz.Rect(x0, y0, x1, y1))

        # Print the selected text to the terminal for debugging
        print(f"Selected text: '{selected_text.strip()}'")  # Ensure non-empty text
        
        return selected_text.strip() if selected_text else None

    def search_selected_text(self):
        """Search the selected text in the dictionary."""
        selected_text = self.get_selected_text()
        if selected_text:
            clean_text = self.clean_word(selected_text)
            words = self.split_into_possible_words(clean_text)
            if words:
                self.show_word_list(words)  # Show list of possible words

    def clean_word(self, word):
        """Clean and normalize the extracted word to ensure proper Japanese word lookup."""
        word = re.sub(r'[^\u3040-\u30FF\u4E00-\u9FAF]', '', word)  # Only keep Japanese characters
        return word

    def split_into_possible_words(self, text):
        """Split the text into individual words."""
        words = []
        length = len(text)

        # Start checking from the selected text and find valid words
        for start in range(length):
            for end in range(start + 1, length + 1):
                candidate_word = text[start:end]
                if self.dictionary.search_word(candidate_word):
                    words.append(candidate_word)
        return words

    def show_word_list(self, words):
        """Show a list of possible words from the selection to choose one for full details."""
        word_list = QListWidget()
        word_list.addItems(words)

        def word_selected():
            selected_word = word_list.currentItem().text()
            self.show_definition(selected_word)

        word_list.itemClicked.connect(word_selected)
        word_list.setWindowTitle("Select a Word")
        word_list.setGeometry(100, 100, 300, 200)
        word_list.show()

    def show_definition(self, word):
        """Show the dictionary definition in a pop-up."""
        entries = self.dictionary.search_word(word)
        
        if entries:
            result_text = ""
            for entry in entries:
                # Extract the word, reading, and tags
                word_text = entry.get("word", "")
                reading = entry.get("reading", "")
                tags = entry.get("tags", "")
                
                # Build the result string
                result_text += f"Word: {word_text}\n"
                result_text += f"Reading: {reading}\n"
                result_text += f"Tags: {tags}\n\n"
    
                # Extract meanings
                meanings = entry.get("meaning", [])
                if meanings:
                    result_text += "Meanings:\n"
                    for meaning in meanings:
                        result_text += f"- {meaning}\n"
                else:
                    result_text += "Meanings: None\n"
    
                # Extract s_inf
                s_inf = entry.get("notes", [])
                if s_inf:
                    result_text += "Other Info:\n"
                    for example in s_inf:
                        result_text += f"- {example}\n"
                else:
                    result_text += "Other Info: None\n"
    
                result_text += "\n---\n"  # Separate entries if there are multiple
    
        else:
            result_text = "Word not found."
    
        # Show the result in a message box
        msg = QMessageBox()
        msg.setWindowTitle("Dictionary Entry")
        msg.setText(result_text)
        msg.exec_()





    def show_message(self, text):
        """Show a simple pop-up message."""
        msg = QMessageBox()
        msg.setWindowTitle("Selection Error")
        msg.setText(text)
        msg.exec_()

    def paintEvent(self, event):
        """Draw the selection rectangle and highlights."""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw a blue box around the selected area
        if self.selection_rect:
            # Get the current scroll offsets
            scroll_x = self.scroll_area.horizontalScrollBar().value()
            scroll_y = self.scroll_area.verticalScrollBar().value()

            # Offset the selection rectangle by the scroll position
            adjusted_rect = self.selection_rect.translated(-scroll_x, -scroll_y)

            # Set the color to a more visible light blue background
            painter.fillRect(adjusted_rect, QColor(173, 216, 230, 120))  # Light blue highlight with transparency

            # Draw a clear, solid border around the selection
            pen = QPen(QColor(0, 0, 255), 2, Qt.SolidLine)  # Blue solid border
            painter.setPen(pen)
            painter.drawRect(adjusted_rect)

        # Draw blue highlights over selected text rectangles
        for rect in self.selected_text_rects:
            # Convert fitz.Rect (from PyMuPDF) to QRectF (for PyQt)
            qrect = QRectF(
                rect.x0, rect.y0,          # Top-left corner
                rect.width, rect.height    # Width and height
            )
            painter.fillRect(qrect, QColor(173, 216, 230, 120))  # Light blue highlight with transparency

    def keyPressEvent(self, event):
        """Handle page scrolling with arrow keys."""
        if event.key() == Qt.Key_Right:
            self.next_page()
        elif event.key() == Qt.Key_Left:
            self.prev_page()

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
