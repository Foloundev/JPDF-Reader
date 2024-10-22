import sys
from PyQt5.QtWidgets import QApplication
from pdf_reader import PDFReader
from menu import Menu

sys.dont_write_bytecode = True

if __name__ == '__main__':
    app = QApplication(sys.argv)
    reader = PDFReader()

    reader.show()
    sys.exit(app.exec_())
