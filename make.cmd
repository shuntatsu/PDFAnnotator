@echo off

cmd /k "cd PDFAnnotator"
cmd /k "python -m venv venv"
cmd /k ".\venv\Scripts\activate" 
cmd /k "pip install -r requirements.txt" 
cmd /k "python main.py"