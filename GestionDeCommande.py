import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Toplevel
import pyperclip
import qrcode
from PIL import ImageTk
import socket
import threading
import json
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os
from tkinter import filedialog
import pandas as pd
import sys
import logging
import traceback
import openpyxl

# Configure logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class QuantityDialog(simpledialog.Dialog):
    def __init__(self, parent, title="", prompt="", initialvalue=None, minvalue=None, maxvalue=None):
        self.prompt = prompt
        self.minvalue = minvalue
        self.maxvalue = maxvalue
        self.initialvalue = initialvalue
        super().__init__(parent, title="")
        
    def body(self, master):
        self.entry = ttk.Entry(master)
        if self.initialvalue is not None:
            self.entry.insert(0, str(self.initialvalue))
        self.entry.grid(row=0, column=0, padx=5, pady=5)
        self.entry.focus_set()
        return self.entry

    def validate(self):
        try:
            value = int(self.entry.get())
            if self.minvalue is not None and value < self.minvalue:
                return False
            if self.maxvalue is not None and value > self.maxvalue:
                return False
            self.result = value
            return True
        except ValueError:
            return False

class DatabaseManagerWindow:
    def __init__(self, app, db_connection):
        # Changed parent to app to get access to the main application instance
        self.app = app  # Store main app reference instead of just the window
        self.window = Toplevel(app.root)
        self.window.title("Base de données")
        self.window.geometry("800x600")
        # Set icon for this window
        if hasattr(app, 'small_icon'):
            self.window.iconphoto(False, app.small_icon)
            
        self.conn = db_connection
        self.cursor = self.conn.cursor()
        self.setup_gui()

    def setup_gui(self):
        self.window.title("Gestion de la base de données")
        self.window.geometry("1200x800")
        
        # Create main frame
        main_frame = ttk.Frame(self.window)
        
        # Create button frames and search frame
        top_frame = ttk.Frame(main_frame)
        left_btn_frame = ttk.Frame(top_frame)
        right_btn_frame = ttk.Frame(top_frame)
        search_frame = ttk.Frame(top_frame)
        
        # Search fields - Single search bar
        ttk.Label(search_frame, text="Rechercher:").pack(side="left", padx=5)
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.search_database)
        
        # Left buttons on same line
        ttk.Button(left_btn_frame, text="Ajouter", command=self.add_item).pack(side="left", padx=5)
        ttk.Button(left_btn_frame, text="Modifier", command=self.edit_item).pack(side="left", padx=5)
        ttk.Button(left_btn_frame, text="Supprimer", command=self.delete_item).pack(side="left", padx=5)
        
        # Right buttons on same line
        ttk.Button(right_btn_frame, text="Exporter", command=self.export_to_excel).pack(side="left", padx=5)
        ttk.Button(right_btn_frame, text="Importer", command=self.import_from_excel).pack(side="left", padx=5)
        
        # Layout top frame
        left_btn_frame.pack(side="left", padx=10)
        search_frame.pack(side="left", expand=True)
        right_btn_frame.pack(side="right", padx=10)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        # Rest of the GUI setup
        self.tree = ttk.Treeview(main_frame, columns=("ID", "Description", "Type", "Prix", "Marque"), show="headings")
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Configure columns
        self.tree.heading("Marque", text="Marque")
        self.tree.heading("ID", text="ID")
        self.tree.heading("Description", text="Description")
        self.tree.heading("Type", text="Type")
        self.tree.heading("Prix", text="Prix")
        
        # Configure column widths
        self.tree.column("Marque", width=100)
        self.tree.column("ID", width=80)
        self.tree.column("Description", width=500)
        self.tree.column("Type", width=150)
        self.tree.column("Prix", width=100)
        
        # Layout
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_data()

    def load_data(self):
        self.tree.delete(*self.tree.get_children())
        self.cursor.execute("SELECT * FROM F1 ORDER BY id")
        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def add_item(self):
        dialog = ItemDialog(self.window, "Ajouter un élément")
        if dialog.result:
            try:
                # Update SQL statement to include marque
                self.cursor.execute(
                    "INSERT INTO F1 (id, description, type, prix, marque) VALUES (?, ?, ?, ?, ?)",
                    (
                        dialog.result[0],  # id
                        dialog.result[1],  # description
                        dialog.result[2],  # type
                        dialog.result[3],  # prix
                        dialog.result[4]   # marque
                    )
                )
                self.conn.commit()
                self.load_data()
            except sqlite3.Error as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'ajout : {str(e)}")

    def edit_item(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner un élément à modifier.")
            return
    
        item = self.tree.item(selected[0])
        dialog = ItemDialog(self.window, "Modifier l'élément", item['values'])
        if dialog.result:
            try:
                self.cursor.execute(
                    "UPDATE F1 SET id=?, description=?, type=?, prix=?, marque=? WHERE id=?",
                    (*dialog.result, item['values'][0])
                )
                self.conn.commit()
                self.load_data()
            except sqlite3.Error as e:
                messagebox.showerror("Erreur", f"Erreur lors de la modification : {str(e)}")

    def delete_item(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Attention", "Veuillez sélectionner un élément à supprimer")
            return
    
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer cet élément ?"):
            return
    
        try:
            # Use selected_item instead of selected
            item = self.tree.item(selected_item[0])
            item_id = item['values'][0]  # ID is in first column
            
            # Check if item is in cart
            if str(item_id) in self.app.panier:
                messagebox.showwarning("Attention", "Cet article est dans le panier actuel")
                return
                
            # Delete from database
            self.cursor.execute("DELETE FROM F1 WHERE id=?", (item_id,))
            self.conn.commit()
            
            # Delete from treeview
            self.tree.delete(selected_item[0])
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {str(e)}")

    def search_database(self, event=None):
        search_text = self.search_entry.get().strip().upper()
        
        self.tree.delete(*self.tree.get_children())
        
        if not search_text:
            self.cursor.execute("SELECT * FROM F1 ORDER BY id")
        else:
            keywords = search_text.split()
            conditions = []
            params = []
            
            for keyword in keywords:
                conditions.append("(UPPER(description) LIKE ? OR UPPER(type) LIKE ? OR UPPER(marque) LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
                
            query = f"""
                SELECT * FROM F1 
                WHERE {' AND '.join(conditions)}
                ORDER BY id
            """
            self.cursor.execute(query, params)

        for row in self.cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def export_to_excel(self):
        try:
            import pandas as pd
            
            # Get all data from database
            self.cursor.execute("SELECT * FROM F1")
            data = self.cursor.fetchall()
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=['ID', 'Description', 'Type', 'Prix', 'Marque'])
            
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension='.xlsx',
                filetypes=[("Excel files", "*.xlsx")],
                title="Exporter la base de données"
            )
            
            if file_path:
                df.to_excel(file_path, index=False)
                messagebox.showinfo("Succès", "Base de données exportée avec succès!")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
    
    def import_from_excel(self):
        try:
            import pandas as pd
            
            # Ask for file location
            file_path = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx")],
                title="Importer une base de données"
            )
            
            if file_path:
                # Read Excel file
                df = pd.read_excel(file_path)
                
                # Clear existing data
                self.cursor.execute("DELETE FROM F1")
                
                # Insert new data
                for _, row in df.iterrows():
                    self.cursor.execute("""
                        INSERT INTO F1 (id, description, type, prix, marque) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        int(row['ID']),
                        str(row['Description']),
                        str(row['Type']),
                        str(row['Prix']),
                        str(row['Marque'])
                    ))
                
                # Commit transaction
                self.cursor.execute("COMMIT")
                self.conn.commit()
                self.load_data()
                messagebox.showinfo("Succès", "Base de données importée avec succès!")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'import: {str(e)}")

class ItemDialog(simpledialog.Dialog):
    def __init__(self, parent, title, initial_values=None):
        self.initial_values = initial_values
        super().__init__(parent, title)

    def body(self, master):
        labels = ["ID:", "Description:", "Type:", "Prix:", "Marque:"]
        self.entries = []
        
        for i, label in enumerate(labels):
            ttk.Label(master, text=label).grid(row=i, column=0, padx=5, pady=5)
            entry = ttk.Entry(master, width=50)
            if self.initial_values:
                entry.insert(0, str(self.initial_values[i]))
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries.append(entry)
        
        return self.entries[0]
    
    def validate(self):
        try:
            prix = self.entries[3].get().strip()
            if not prix.endswith('€'):
                prix = f"{prix} €"
            
            self.result = [
                int(self.entries[0].get()),
                self.entries[1].get(),
                self.entries[2].get(),
                prix,
                self.entries[4].get()
            ]
            return True
        except ValueError:
            messagebox.showerror("Erreur", "L'ID doit être un nombre entier")
            return False

class GestionCommandes:
    def __init__(self):
        # Database connection
        self.conn = sqlite3.connect('DB.db')
        self.cursor = self.conn.cursor()
        
        # Enable high DPI awareness
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
        self.panier = {}
        self.setup_database()
        self.setup_flask()
        
        # Add icon setup before creating GUI
        self.icon_path = 'Logo_DN.ico'  # Ensure this path is correct
        self.setup_icon()
        
        self.create_gui()
        self.load_cart()

    def get_resource_path(self, relative_path):
        try:
            if hasattr(sys, '_MEIPASS'): 
                # PyInstaller path
                base_path = sys._MEIPASS
            elif getattr(sys, 'frozen', False):
                # cx_Freeze path
                base_path = os.path.dirname(sys.executable)
            else:
                # Development path
                base_path = os.path.abspath(os.path.dirname(__file__))
            return os.path.join(base_path, relative_path)
        except Exception as e:
            print(f"Error getting resource path: {e}")
            return relative_path

    def setup_icon(self):
        try:
            icon_path = self.get_resource_path("Logo_DN.png")
            print(f"Looking for icon at: {icon_path}")
            
            if os.path.exists(icon_path):
                self.icon = ImageTk.PhotoImage(file=icon_path)
                self.root.iconphoto(False, self.icon)
                self.small_icon = ImageTk.PhotoImage(file=icon_path)
            else:
                print(f"Icon file not found at: {icon_path}")
        except Exception as e:
            print(f"Error loading icon: {e}")

    def setup_database(self):
        db_exists = os.path.exists('DB.db')
        self.conn = sqlite3.connect('DB.db')
        self.cursor = self.conn.cursor()
        
        # Create table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS F1 (
                id INTEGER PRIMARY KEY,
                description TEXT,
                type TEXT,
                prix TEXT,
                marque TEXT
            )
        ''')
        self.conn.commit()

    def setup_flask(self):
        template_folder = self.get_resource_path(".")
        self.app = Flask(__name__, template_folder=template_folder)
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='threading'
        )
        self.clients = set()

        @self.app.route('/')
        def index():
            return render_template('templates/edit_order.html')

        @self.socketio.on('connect')
        def handle_connect():
            self.clients.add(request.sid)
            emit('panier_update', self.panier, to=request.sid)

        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.clients.remove(request.sid)

        @self.socketio.on('update_panier')
        def handle_panier_update(data):
            try:
                id_produit = str(data['id'])
                if data['quantite'] == 0:
                    self.panier.pop(id_produit, None)
                else:
                    self.panier[id_produit] = {
                        'element': data['element'],
                        'quantite': int(data['quantite'])
                    }
                self.save_cart()
                # Broadcast to all connected clients
                for client in self.clients:
                    emit('panier_update', self.panier, to=client)
                self.update_cart_display()
            except Exception as e:
                print(f"Erreur: {e}")

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Gestion de commandes")
        self.root.iconbitmap("Logo_DN.ico")
        
        # Set window icon with absolute path and alternative method
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.join(current_dir, "Logo_DN.png")
            if os.path.exists(icon_path):
                # Try PhotoImage method if iconbitmap fails
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
                self.root.tk.call('wm', 'iconphoto', self.root._w, icon)
            else:
                print(f"Icon file not found at: {icon_path}")
        except Exception as e:
            print(f"Could not load icon file: {e}")
        
        # Configure font quality
        self.root.option_add('*Font', ('Segoe UI', 10))
        self.root.tk.call('tk', 'scaling', 2.0)
        
        # Configure window
        self.root.configure(bg='#f8f9fa')
        
        self.setup_styles()
        self.setup_gui_elements()
        self.setup_grid_layout()
        # Call search to populate initial data
        self.search()
        
        # Add right-click binding for quantity modification
        self.treeview_panier.bind('<Button-3>', self.show_context_menu)

    def setup_styles(self):
        style = ttk.Style()
        # Configure theme
        style.theme_use('clam')
        
        # Configure font rendering
        font_config = {
            'family': 'Segoe UI',
            'size': 10,
            'weight': 'normal'
        }
        
        # Configure Treeview
        style.configure("Treeview",
            background="white",
            fieldbackground="white",
            foreground="black",
            rowheight=25,
            font=font_config
        )
        style.configure("Treeview.Heading",
            background="#0d6efd",
            foreground="white",
            padding=5,
            font=(font_config['family'], font_config['size'], 'bold')
        )
        
        # Configure Buttons
        style.configure("TButton", 
            padding=6,
            background="#0d6efd",
            foreground="black"
        )
        style.map('TButton',
            background=[('active', '#0b5ed7'), ('!active', '#0d6efd')],
            foreground=[('active', 'black'), ('!active', 'black')]
        )
        
        # Configure Entry and Label
        style.configure("TEntry",
            padding=6,
            fieldbackground="white",
            foreground="black"
        )
        style.configure("TLabel",
            background="#f8f9fa",
            foreground="black",
            font=('Helvetica', 10)
        )

    def setup_gui_elements(self):
        self.setup_styles()
        
        # Single search field
        self.entry_valeur = ttk.Entry(self.root)
        self.entry_valeur.bind("<KeyRelease>", self.search)

        # Results list with custom style
        self.listbox_resultats = tk.Listbox(
            self.root, 
            width=100,  # Increased width
            height=10,
            bg='white',
            selectmode='single',
            relief='flat',
            bd=1,
            highlightthickness=1,
            highlightcolor='#dee2e6'
        )
        
        # Add double-click binding to listbox
        self.listbox_resultats.bind('<Double-Button-1>', self.add_to_cart)
        
        # Add right-click binding to listbox
        self.listbox_resultats.bind('<Button-3>', self.show_database_manager)
        
        # Cart display with Bootstrap-like style
        columns = ("Désignation", "Références", "Marque", "Quantité", "Prix", "Prix totale")
        self.treeview_panier = ttk.Treeview(
            self.root, 
            columns=columns, 
            show="headings",
            style="Treeview"
        )
        
        # Configure columns
        for col in columns:
            self.treeview_panier.heading(col, text=col)
        
        # Configure column widths
        self.treeview_panier.column("Désignation", width=400)
        self.treeview_panier.column("Références", width=100)
        self.treeview_panier.column("Marque", width=100)
        self.treeview_panier.column("Quantité", width=80)
        self.treeview_panier.column("Prix", width=100)
        self.treeview_panier.column("Prix totale", width=100)

        # Add padding to main window
        for child in self.root.winfo_children():
            child.grid_configure(padx=20, pady=5)
        
        # Modifier le binding du treeview_panier pour utiliser le double-clic
        self.treeview_panier.bind('<Double-Button-1>', self.show_context_menu)

    def setup_grid_layout(self):
        # Configure grid
        for i in range(3):
            self.root.grid_columnconfigure(i, weight=1)

        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(4, weight=1)  # Make the listbox row expandable
        self.root.grid_rowconfigure(5, weight=1)  # Make the treeview row expandable

        # Layout elements - removing type search
        ttk.Label(self.root, text="Rechercher :").grid(row=0, column=0, sticky='w', padx=5)
        self.entry_valeur.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5)
        
        self.listbox_resultats.grid(row=4, column=0, columnspan=3, sticky='nsew', padx=5, pady=5)
        self.treeview_panier.grid(row=5, column=0, columnspan=3, sticky='nsew', padx=5, pady=5)
        
        ttk.Button(self.root, text="Afficher QR Code", command=self.show_qr_code).grid(
            row=6, column=0, pady=10, padx=5)
        ttk.Button(self.root, text="Copier la commande", command=self.copy_cart).grid(
            row=6, column=1, pady=10, padx=5)
        ttk.Button(self.root, text="Nouvelle commande", command=self.reset_cart).grid(
            row=6, column=2, pady=10, padx=5)

    def load_cart(self):
        try:
            with open('panier.json', 'r') as f:
                content = f.read()
                if content.strip():  # Check if file is not empty
                    self.panier = json.loads(content)
                else:
                    self.panier = {}
        except (FileNotFoundError, json.JSONDecodeError):
            print("Initializing empty cart")
            self.panier = {}
        self.update_cart_display()

    def save_cart(self):
        try:
            with open('panier.json', 'w') as f:
                json.dump(self.panier, f, indent=2)
        except Exception as e:
            print(f"Error saving cart: {e}")
            messagebox.showerror("Error", "Could not save cart")

    def search(self, _=None):
        search_text = self.entry_valeur.get().strip().upper()
        
        if not search_text:
            query = "SELECT * FROM F1"
            self.cursor.execute(query)
        else:
            keywords = search_text.split()
            conditions = []
            params = []
            
            for keyword in keywords:
                conditions.append("(UPPER(description) LIKE ? OR UPPER(type) LIKE ? OR UPPER(marque) LIKE ?)")
                params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
                
            query = f"""
                SELECT * FROM F1 
                WHERE {' AND '.join(conditions)}
            """
            self.cursor.execute(query, params)

        results = sorted(
            self.cursor.fetchall(),
            key=lambda x: float(x[3].replace("€", "").replace(",", ".").strip())
        )

        self.listbox_resultats.delete(0, tk.END)
        for row in results:
            marque = row[4] if len(row) > 4 else ""
            display_text = f"{marque} - {row[1]} ({row[2]}): {row[3]}"
            self.listbox_resultats.insert(tk.END, display_text)

        self.results_data = results

    def add_to_cart(self, event=None):
        selection = self.listbox_resultats.curselection()
        if not selection:
            messagebox.showwarning(" ", "Veuillez sélectionner un élément.")
            return

        element = self.results_data[selection[0]]
        dialog = QuantityDialog(
            self.root,
            prompt="Entrez la quantité :",
            minvalue=1
        )
        quantity = dialog.result
        
        if not quantity:
            return

        id_produit = str(element[0])
        # Include all 5 columns from database including marque
        element_data = list(element)  # This captures all fields including marque
        
        if id_produit in self.panier:
            self.panier[id_produit]['quantite'] += quantity
        else:
            self.panier[id_produit] = {'element': element_data, 'quantite': quantity}
        
        self.save_cart()
        # Corriger l'émission socketio
        self.socketio.emit('panier_update', self.panier, room=None)
        self.update_cart_display()

    def show_quantity_dialog(self, event):
        item = self.treeview_panier.identify_row(event.y)
        if not item:
            return
            
        values = self.treeview_panier.item(item)['values']
        if not values:
            return
            
        id_produit = str(values[1])
        dialog = QuantityDialog(
            self.root,
            prompt=f"Nouvelle quantité pour {values[0]}:",
            minvalue=0,
            initialvalue=values[3]
        )
        quantity = dialog.result

        if quantity is not None:
            if quantity == 0:
                del self.panier[id_produit]
            else:
                self.panier[id_produit]['quantite'] = quantity
            
            self.save_cart()
            self.socketio.emit('panier_update', self.panier, broadcast=True)
            self.update_cart_display()

    def show_context_menu(self, event):
        item = self.treeview_panier.identify_row(event.y)
        if not item:
            return
            
        values = self.treeview_panier.item(item)['values']
        if not values:
            return
            
        id_produit = str(values[1])
        dialog = QuantityDialog(
            self.root,
            prompt=f"Nouvelle quantité pour {values[0]}:",
            minvalue=0,
            initialvalue=values[3]
        )
        quantity = dialog.result

        if quantity is not None:
            if quantity == 0:
                del self.panier[id_produit]
            else:
                self.panier[id_produit]['quantite'] = quantity
            
            self.save_cart()
            # Correction de l'émission socketio
            self.socketio.emit('panier_update', self.panier, room=None)
            self.update_cart_display()

    def update_cart_display(self):
        self.treeview_panier.delete(*self.treeview_panier.get_children())
        total_sum = 0.0
        
        for item in self.panier.values():
            element = item['element']
            quantity = item['quantite']
            price = float(element[3].replace("€", "").replace(",", "."))
            total = quantity * price
            total_sum += total
            
            # Add safe access to marque with fallback
            try:
                marque = element[4] if len(element) > 4 else ""
            except (IndexError, TypeError):
                marque = ""
                
            self.treeview_panier.insert("", tk.END, values=(
                element[1],      # Description
                element[0],      # ID
                marque,         # Marque
                quantity,       # Quantité
                f"{price:.2f}€", # Prix
                f"{total:.2f}€"  # Prix total
            ))
        
        if self.panier:
            total_sum = sum(float(self.treeview_panier.item(item)['values'][5].replace('€','').replace(',','.')) 
                    for item in self.treeview_panier.get_children())
            self.treeview_panier.insert("", tk.END, values=(
                "TOTAL", "", "", "", "", f"{total_sum:.2f}€"
            ), tags=('total',))
            self.treeview_panier.tag_configure('total', font=('TkDefaultFont', 9, 'bold'))

    def reset_cart(self):
        self.panier = {}
        self.save_cart()
        # Corriger l'émission socketio
        self.socketio.emit('panier_update', self.panier, room=None)
        self.update_cart_display()

    def copy_cart(self):
        if not self.panier:
            messagebox.showwarning(" ", "Le panier est vide.")
            return
        
        content = ""
        for details in self.panier.values():
            element = details['element']
            quantity = details['quantite']
            price = float(element[3].replace('€','').replace(',','.'))
            content += f"{element[1]}\t{element[0]}\tU\t{quantity}\t{price:.2f}€\t{price*quantity:.2f}€\n"
        
        pyperclip.copy(content)
        messagebox.showinfo(" ", "Contenu copié dans le presse-papiers")

    def show_qr_code(self):
        ip_address = socket.gethostbyname(socket.gethostname())
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f'http://{ip_address}:5000')
        qr.make(fit=True)
        
        window = Toplevel(self.root)
        window.title("")  # Empty title
        window.geometry("300x300")
        
        img_tk = ImageTk.PhotoImage(qr.make_image(fill='black', back_color='white'))
        label = tk.Label(window, image=img_tk)
        label.image = img_tk
        label.pack(padx=20, pady=20)

    def show_database_manager(self, event):
        DatabaseManagerWindow(self, self.conn)

    def run(self):
        def run_flask():
            self.socketio.run(
                self.app,
                host='0.0.0.0',  # Écoute sur toutes les interfaces
                port=5000,
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
    
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
        try:
            self.root.mainloop()
        finally:
            # Cleanup when application closes
            self.conn.close()

if __name__ == '__main__':
    try:
        app = GestionCommandes()
        app.run()
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        logging.error(traceback.format_exc())
        print(f"An error occurred: {str(e)}")
        print("See app.log for details")
        input("Press Enter to exit...")  # Prevent console from closing