from cx_Freeze import setup, Executable
import sys
import os
import numpy

# Get numpy path
numpy_path = os.path.dirname(numpy.__file__)

build_exe_options = {
    "packages": [
        "numpy",
        "pandas",
        "flask",
        "flask_socketio",
        "engineio",
        "socketio",
        "tkinter",
        "PIL",
        "pyperclip",
        "qrcode",
        "openpyxl",  # Add openpyxl package
        "et_xmlfile"  # Required dependency for openpyxl
    ],
    "includes": [
        "numpy.core._methods",
        "numpy.lib.format",
        "numpy.core._dtype_ctypes",
        "numpy.core.numeric",
        "jinja2.ext",
        "tkinter.ttk",
        "openpyxl.cell",  # Add key openpyxl modules
        "openpyxl.workbook",
        "openpyxl.worksheet"
    ],
    "include_files": [
        ("Logo_DN.png", "Logo_DN.png"),
        ("Logo_DN.ico", "Logo_DN.ico"),
        ("templates/edit_order.html", "templates/edit_order.html"),
        ("Douzet.db", "Douzet.db"),
        ("panier.json", "panier.json"),
        (numpy_path, "numpy")
    ],
    "excludes": [],
    "zip_include_packages": "*",
    "zip_exclude_packages": ["numpy"],
    "include_msvcr": True
}

setup(
    name="GestionCommandes",
    version="1.0",
    description="Application de gestion des commandes",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "GestionDeCommande.py",
            base="Win32GUI" if sys.platform == "win32" else None,
            icon="Logo_DN.ico"
        )
    ]
)