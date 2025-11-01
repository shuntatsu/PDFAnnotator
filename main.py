# main.py
import tkinter as tk
from app_core import PDFAnnotator

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFAnnotator(root)
    root.mainloop()
