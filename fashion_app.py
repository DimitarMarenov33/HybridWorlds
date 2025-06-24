import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from pathlib import Path

# Import the database class - adjust path if needed
try:
    from database_setup import FashionEnvironmentDB
except ImportError:
    # If database_setup.py is not found, define FashionEnvironmentDB locally
    import sqlite3
    from datetime import datetime
    
    class FashionEnvironmentDB:
        def __init__(self, db_path="fashion_env.db"):
            self.db_path = db_path
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
        
        def get_clothing_item(self, qr_code):
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM clothing_items WHERE qr_code = ?', (qr_code,))
            return cursor.fetchone()
        
        def get_material_composition(self, qr_code):
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT m.material_name, cmc.percentage
            FROM clothing_material_composition cmc
            JOIN materials m ON cmc.material_id = m.material_id
            WHERE cmc.qr_code = ?
            ''', (qr_code,))
            return cursor.fetchall()
        
        def get_environmental_impact(self, material_name, impact_category):
            cursor = self.conn.cursor()
            cursor.execute('''
            SELECT ei.impact_value, ei.unit
            FROM environmental_impacts ei
            JOIN materials m ON ei.material_id = m.material_id
            WHERE m.material_name = ? AND ei.impact_category = ?
            ''', (material_name.lower(), impact_category))
            return cursor.fetchone()
        
        def list_all_clothing_items(self):
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM clothing_items ORDER BY item_name')
            return cursor.fetchall()
        
        def list_all_materials(self):
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM materials ORDER BY material_name')
            return cursor.fetchall()
        
        def add_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
            conn = self.get_connection()  # ← Use get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO clothing_items (qr_code, item_name, brand, category, weight_grams)
                VALUES (?, ?, ?, ?, ?)
                ''', (qr_code, name, brand, category, weight_grams))
                conn.commit()
                conn.close()  # ← Close the connection
                return True
            except sqlite3.IntegrityError:
                conn.close()  # ← Close on error too
                return False
        
        def add_material(self, name, density=None, description=None):
            cursor = self.conn.cursor()
            try:
                cursor.execute('''
                INSERT INTO materials (material_name, density_g_per_cm3, description)
                VALUES (?, ?, ?)
                ''', (name.lower(), density, description))
                self.conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
        
        def add_material_composition(self, qr_code, material_name, percentage):
            """Add material composition for a clothing item"""
            cursor = self.conn.cursor()
            
            # Get material ID
            cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
            material = cursor.fetchone()
            
            if not material:
                return False
            
            cursor.execute('''
            INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
            VALUES (?, ?, ?)
            ''', (qr_code, material['material_id'], percentage))
            
            self.conn.commit()
            return True
        

        def list_all_materials_with_impact_count(self):
            """Get all materials with their impact data count"""
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT m.*, 
                COUNT(ei.impact_id) as impact_count
            FROM materials m
            LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
            GROUP BY m.material_id, m.material_name, m.density_g_per_cm3, m.description
            ORDER BY m.material_name
            ''')
            result = cursor.fetchall()
            conn.close()
            return result
        
        def list_all_environmental_impacts(self):
            """Get all environmental impacts with material names"""
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT ei.impact_id, m.material_name, ei.impact_category, 
                ei.impact_value, ei.unit, ei.source
            FROM environmental_impacts ei
            JOIN materials m ON ei.material_id = m.material_id
            ORDER BY m.material_name, ei.impact_category
            ''')
            result = cursor.fetchall()
            conn.close()
            return result
        
        def add_environmental_impact(self, material_name, impact_category, impact_value, unit, source=None):
            """Add environmental impact data for a material"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get material ID
            cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
            material = cursor.fetchone()
            
            if not material:
                conn.close()
                return False
            
            try:
                cursor.execute('''
                INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
                VALUES (?, ?, ?, ?, ?)
                ''', (material['material_id'], impact_category, impact_value, unit, source))
                
                impact_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return impact_id
            except sqlite3.IntegrityError:
                conn.close()
                return False
        
        def update_environmental_impact(self, impact_id, material_name, impact_category, impact_value, unit, source=None):
            """Update existing environmental impact data"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get material ID
            cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
            material = cursor.fetchone()
            
            if not material:
                conn.close()
                return False
            
            try:
                cursor.execute('''
                UPDATE environmental_impacts 
                SET material_id=?, impact_category=?, impact_value=?, unit=?, source=?
                WHERE impact_id=?
                ''', (material['material_id'], impact_category, impact_value, unit, source, impact_id))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def delete_environmental_impact(self, impact_id):
            """Delete environmental impact data"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM environmental_impacts WHERE impact_id = ?", (impact_id,))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def update_material(self, material_id, name, density=None, description=None):
            """Update existing material"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                UPDATE materials 
                SET material_name=?, density_g_per_cm3=?, description=?
                WHERE material_id=?
                ''', (name.lower(), density, description, material_id))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def delete_material(self, material_id):
            """Delete material and associated data"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Delete environmental impacts first
                cursor.execute("DELETE FROM environmental_impacts WHERE material_id = ?", (material_id,))
                
                # Delete material compositions
                cursor.execute("DELETE FROM clothing_material_composition WHERE material_id = ?", (material_id,))
                
                # Delete material
                cursor.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def update_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
            """Update existing clothing item"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                UPDATE clothing_items 
                SET item_name=?, brand=?, category=?, weight_grams=?
                WHERE qr_code=?
                ''', (name, brand, category, weight_grams, qr_code))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def delete_clothing_item(self, qr_code):
            """Delete clothing item and its material composition"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Delete material composition first (foreign key constraint)
                cursor.execute("DELETE FROM clothing_material_composition WHERE qr_code = ?", (qr_code,))
                
                # Delete clothing item
                cursor.execute("DELETE FROM clothing_items WHERE qr_code = ?", (qr_code,))
                
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def clear_material_composition(self, qr_code):
            """Clear all material composition for an item"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('DELETE FROM clothing_material_composition WHERE qr_code=?', (qr_code,))
                conn.commit()
                conn.close()
                return True
            except sqlite3.Error:
                conn.close()
                return False
        
        def get_database_stats(self):
            """Get overview statistics for the database"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            stats = {}
            
            # Get counts
            cursor.execute('SELECT COUNT(*) as count FROM clothing_items')
            stats['items_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM materials')
            stats['materials_count'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM environmental_impacts')
            stats['impacts_count'] = cursor.fetchone()['count']
            
            # Get unique brands
            cursor.execute('SELECT COUNT(DISTINCT brand) as count FROM clothing_items WHERE brand IS NOT NULL')
            stats['brands_count'] = cursor.fetchone()['count']
            
            # Get unique categories
            cursor.execute('SELECT COUNT(DISTINCT category) as count FROM clothing_items WHERE category IS NOT NULL')
            stats['categories_count'] = cursor.fetchone()['count']
            
            # Get unique impact categories
            cursor.execute('SELECT COUNT(DISTINCT impact_category) as count FROM environmental_impacts')
            stats['impact_categories_count'] = cursor.fetchone()['count']
            
            # Get average weight
            cursor.execute('SELECT AVG(weight_grams) as avg_weight FROM clothing_items')
            avg_weight = cursor.fetchone()['avg_weight']
            stats['avg_weight'] = round(avg_weight, 1) if avg_weight else 0
            
            conn.close()
            return stats
        
        def search_items(self, search_term):
            """Search clothing items by name, brand, category, or QR code"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_pattern = f"%{search_term.lower()}%"
            cursor.execute('''
            SELECT * FROM clothing_items 
            WHERE LOWER(qr_code) LIKE ? 
            OR LOWER(item_name) LIKE ? 
            OR LOWER(brand) LIKE ? 
            OR LOWER(category) LIKE ?
            ORDER BY item_name
            ''', (search_pattern, search_pattern, search_pattern, search_pattern))
            
            result = cursor.fetchall()
            conn.close()
            return result
        
        def search_materials(self, search_term):
            """Search materials by name or description"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            search_pattern = f"%{search_term.lower()}%"
            cursor.execute('''
            SELECT m.*, COUNT(ei.impact_id) as impact_count
            FROM materials m
            LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
            WHERE LOWER(m.material_name) LIKE ? 
            OR LOWER(m.description) LIKE ?
            GROUP BY m.material_id
            ORDER BY m.material_name
            ''', (search_pattern, search_pattern))
            
            result = cursor.fetchall()
            conn.close()
            return result
        
        def get_material_usage_count(self, material_id):
            """Get how many clothing items use this material"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT COUNT(*) as count FROM clothing_material_composition 
            WHERE material_id = ?
            ''', (material_id,))
            
            result = cursor.fetchone()['count']
            conn.close()
            return result
        
        def backup_database(self, backup_path):
            """Create a backup of the database"""
            import shutil
            try:
                shutil.copy2(self.db_path, backup_path)
                return True
            except Exception:
                return False
        
        def validate_material_composition(self, qr_code):
            """Validate that material composition adds up to 100%"""
            materials = self.get_material_composition(qr_code)
            total_percentage = sum(material['percentage'] for material in materials)
            return abs(total_percentage - 100) < 0.1  # Allow small rounding errors
        
        def get_items_by_material(self, material_name):
            """Get all clothing items that contain a specific material"""
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT ci.*, cmc.percentage
            FROM clothing_items ci
            JOIN clothing_material_composition cmc ON ci.qr_code = cmc.qr_code
            JOIN materials m ON cmc.material_id = m.material_id
            WHERE m.material_name = ?
            ORDER BY ci.item_name
            ''', (material_name.lower(),))
            
            result = cursor.fetchall()
            conn.close()
            return result
        
        def close(self):
            """Close database connection (if needed for certain operations)"""
            # This method is mainly for compatibility with existing code
            # Since we use get_connection() pattern, individual connections are closed in methods
            pass
        
        def close(self):
            self.conn.close()

class FashionEnvironmentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Fashion Environmental Impact Analyzer")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize database
        try:
            self.db = FashionEnvironmentDB()
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not connect to database: {e}")
            return
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_scanner_tab()
        self.create_database_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_scanner_tab(self):
        """Create the item scanner/lookup tab"""
        scanner_frame = ttk.Frame(self.notebook)
        self.notebook.add(scanner_frame, text="🔍 Item Scanner")
        
        # Main container
        main_container = ttk.Frame(scanner_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Input section
        input_frame = ttk.LabelFrame(main_container, text="Enter Item QR Code", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        entry_frame = ttk.Frame(input_frame)
        entry_frame.pack(fill=tk.X)
        
        ttk.Label(entry_frame, text="QR Code:").pack(side=tk.LEFT, padx=(0, 10))
        self.qr_entry = ttk.Entry(entry_frame, font=("Arial", 12))
        self.qr_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.qr_entry.bind('<Return>', lambda e: self.scan_item())
        
        scan_btn = ttk.Button(entry_frame, text="Analyze Item", command=self.scan_item)
        scan_btn.pack(side=tk.RIGHT)
        
        # Results section
        results_frame = ttk.LabelFrame(main_container, text="Analysis Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable text widget for results
        text_frame = ttk.Frame(results_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10), 
                                   bg='white', fg='black', padx=10, pady=10)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure text tags for formatting
        self.results_text.tag_configure("title", font=("Arial", 14, "bold"), foreground="blue")
        self.results_text.tag_configure("section", font=("Arial", 12, "bold"), foreground="darkgreen")
        self.results_text.tag_configure("material", font=("Arial", 10, "bold"))
        self.results_text.tag_configure("impact", font=("Arial", 10))
        self.results_text.tag_configure("total", font=("Arial", 11, "bold"), foreground="red")
        
        # Add welcome message
        self.show_welcome_message()
    
    def create_database_tab(self):
        """Create the database management tab"""
        db_frame = ttk.Frame(self.notebook)
        self.notebook.add(db_frame, text="🗃️ Database Manager")
        
        # Create sub-notebook for different tables
        self.db_notebook = ttk.Notebook(db_frame)
        self.db_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs for different database tables
        self.create_clothing_items_tab()
        self.create_materials_tab()
        self.create_impacts_tab()
    
    def create_clothing_items_tab(self):
        """Create clothing items management tab"""
        items_frame = ttk.Frame(self.db_notebook)
        self.db_notebook.add(items_frame, text="Clothing Items")
        
        # Control buttons
        btn_frame = ttk.Frame(items_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Add Item", command=self.add_clothing_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Item", command=self.edit_clothing_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Item", command=self.delete_clothing_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_clothing_items).pack(side=tk.RIGHT, padx=5)
        
        # Treeview for clothing items
        columns = ("QR Code", "Name", "Brand", "Category", "Weight (g)", "Created")
        self.items_tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=120)
        
        # Scrollbars
        items_scrollbar_y = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        items_scrollbar_x = ttk.Scrollbar(items_frame, orient=tk.HORIZONTAL, command=self.items_tree.xview)
        self.items_tree.configure(yscrollcommand=items_scrollbar_y.set, xscrollcommand=items_scrollbar_x.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        items_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        items_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        self.refresh_clothing_items()
    
    def create_materials_tab(self):
        """Create materials management tab"""
        materials_frame = ttk.Frame(self.db_notebook)
        self.db_notebook.add(materials_frame, text="Materials")
        
        # Control buttons
        btn_frame = ttk.Frame(materials_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Add Material", command=self.add_material).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Material", command=self.edit_material).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Material", command=self.delete_material).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_materials).pack(side=tk.RIGHT, padx=5)
        
        # Treeview for materials
        columns = ("ID", "Name", "Density", "Description")
        self.materials_tree = ttk.Treeview(materials_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.materials_tree.heading(col, text=col)
            if col == "Description":
                self.materials_tree.column(col, width=300)
            else:
                self.materials_tree.column(col, width=100)
        
        # Scrollbars
        materials_scrollbar_y = ttk.Scrollbar(materials_frame, orient=tk.VERTICAL, command=self.materials_tree.yview)
        materials_scrollbar_x = ttk.Scrollbar(materials_frame, orient=tk.HORIZONTAL, command=self.materials_tree.xview)
        self.materials_tree.configure(yscrollcommand=materials_scrollbar_y.set, xscrollcommand=materials_scrollbar_x.set)
        
        self.materials_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        materials_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        materials_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        self.refresh_materials()
    
    def create_impacts_tab(self):
        """Create environmental impacts management tab"""
        impacts_frame = ttk.Frame(self.db_notebook)
        self.db_notebook.add(impacts_frame, text="Environmental Impacts")
        
        # Control buttons
        btn_frame = ttk.Frame(impacts_frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(btn_frame, text="Add Impact", command=self.add_impact).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Edit Impact", command=self.edit_impact).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Impact", command=self.delete_impact).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_impacts).pack(side=tk.RIGHT, padx=5)
        
        # Treeview for impacts
        columns = ("ID", "Material", "Category", "Value", "Unit", "Source")
        self.impacts_tree = ttk.Treeview(impacts_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            self.impacts_tree.heading(col, text=col)
            if col == "Source":
                self.impacts_tree.column(col, width=200)
            else:
                self.impacts_tree.column(col, width=100)
        
        # Scrollbars
        impacts_scrollbar_y = ttk.Scrollbar(impacts_frame, orient=tk.VERTICAL, command=self.impacts_tree.yview)
        impacts_scrollbar_x = ttk.Scrollbar(impacts_frame, orient=tk.HORIZONTAL, command=self.impacts_tree.xview)
        self.impacts_tree.configure(yscrollcommand=impacts_scrollbar_y.set, xscrollcommand=impacts_scrollbar_x.set)
        
        self.impacts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=5)
        impacts_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        impacts_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X, padx=10)
        
        self.refresh_impacts()
    
    def show_welcome_message(self):
        """Show welcome message in results area"""
        welcome_text = """
Welcome to Fashion Environmental Impact Analyzer!

Enter a QR code above to analyze a clothing item's environmental impact.

Sample QR codes to try:
• SHIRT001 - Cotton T-Shirt
• JEANS001 - Denim Jeans  
• SWEAT001 - Cotton-Poly Hoodie
• DRESS001 - Summer Dress
• SOCK001 - Cotton Socks

The analysis will show:
✓ Item details (weight, materials)
✓ Material composition breakdown
✓ Environmental impacts per material
✓ Total calculated impact for the item
        """
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, welcome_text, "impact")
    
    def scan_item(self):
        """Analyze the environmental impact of a clothing item"""
        qr_code = self.qr_entry.get().strip()
        if not qr_code:
            messagebox.showwarning("Input Error", "Please enter a QR code")
            return
        
        try:
            # Get clothing item
            item = self.db.get_clothing_item(qr_code)
            if not item:
                self.results_text.delete(1.0, tk.END)
                self.results_text.insert(tk.END, f"❌ No item found with QR code: {qr_code}\n\n", "total")
                self.results_text.insert(tk.END, "Available QR codes:\n", "section")
                
                # Show available items
                all_items = self.db.list_all_clothing_items()
                for available_item in all_items:
                    self.results_text.insert(tk.END, f"• {available_item['qr_code']} - {available_item['item_name']}\n", "impact")
                return
            
            # Get material composition
            materials = self.db.get_material_composition(qr_code)
            
            # Clear results and show analysis
            self.results_text.delete(1.0, tk.END)
            
            # Item header
            self.results_text.insert(tk.END, f"🏷️ ITEM ANALYSIS: {item['item_name']}\n", "title")
            self.results_text.insert(tk.END, "=" * 50 + "\n\n", "impact")
            
            # Item details
            self.results_text.insert(tk.END, "📋 ITEM DETAILS:\n", "section")
            self.results_text.insert(tk.END, f"QR Code: {item['qr_code']}\n", "impact")
            self.results_text.insert(tk.END, f"Name: {item['item_name']}\n", "impact")
            self.results_text.insert(tk.END, f"Brand: {item['brand'] or 'N/A'}\n", "impact")
            self.results_text.insert(tk.END, f"Category: {item['category'] or 'N/A'}\n", "impact")
            self.results_text.insert(tk.END, f"Weight: {item['weight_grams']}g\n\n", "impact")
            
            # Material composition
            self.results_text.insert(tk.END, "🧵 MATERIAL COMPOSITION:\n", "section")
            for material in materials:
                self.results_text.insert(tk.END, f"• {material['material_name'].title()}: {material['percentage']}%\n", "material")
            self.results_text.insert(tk.END, "\n")
            
            # Environmental impacts
            self.results_text.insert(tk.END, "🌍 ENVIRONMENTAL IMPACT ANALYSIS:\n", "section")
            self.results_text.insert(tk.END, "-" * 50 + "\n", "impact")
            
            impact_categories = ["water_usage", "carbon_footprint", "energy_usage"]
            category_names = {
                "water_usage": "💧 Water Usage",
                "carbon_footprint": "🏭 Carbon Footprint", 
                "energy_usage": "⚡ Energy Usage"
            }
            
            total_impacts = {}
            
            for category in impact_categories:
                self.results_text.insert(tk.END, f"\n{category_names[category]}:\n", "section")
                
                category_total = 0
                unit = None
                
                for material in materials:
                    impact_data = self.db.get_environmental_impact(material['material_name'], category)
                    if impact_data:
                        # Calculate impact for this material
                        material_impact = (
                            impact_data['impact_value'] * 
                            (material['percentage'] / 100) * 
                            (item['weight_grams'] / 1000)
                        )
                        category_total += material_impact
                        unit = impact_data['unit']
                        
                        # Get the final unit (remove /kg since we calculated for specific weight)
                        final_unit = impact_data['unit'].replace('/kg', '')

                        self.results_text.insert(tk.END, 
                            f"  {material['material_name'].title()}: "
                            f"{material_impact:.2f} {final_unit} for this {item['weight_grams']}g item\n"
                            f"    (calculation: {material['percentage']}% × {impact_data['impact_value']} {impact_data['unit']} × {item['weight_grams']/1000:.3f}kg)\n", 
                            "impact")
                    else:
                        self.results_text.insert(tk.END, 
                            f"  {material['material_name'].title()}: No {category.replace('_', ' ')} data available\n", 
                            "impact")
                
                if unit:
                    final_unit = unit.replace('/kg', '')  # Remove /kg for final display
                    total_impacts[category] = {'value': category_total, 'unit': final_unit}
                    self.results_text.insert(tk.END, 
                        f"  TOTAL: {category_total:.2f} {final_unit}\n", 
                        "total")
            
            # Summary
            self.results_text.insert(tk.END, "\n" + "=" * 50 + "\n", "impact")
            self.results_text.insert(tk.END, f"📊 TOTAL IMPACT FOR THIS {item['weight_grams']}g ITEM:\n", "title")
            for category, data in total_impacts.items():
                category_name = category_names[category].split(' ', 1)[1]  # Remove emoji
                self.results_text.insert(tk.END, 
                    f"{category_name}: {data['value']:.2f} {data['unit']}\n", 
                    "total")
            
            self.status_var.set(f"Analysis complete for {qr_code}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error analyzing item: {e}")
            self.status_var.set("Analysis failed")
    
    # Database management methods
    def refresh_clothing_items(self):
        """Refresh the clothing items display"""
        for item in self.items_tree.get_children():
            self.items_tree.delete(item)
        
        items = self.db.list_all_clothing_items()
        for item in items:
            self.items_tree.insert("", tk.END, values=(
                item['qr_code'], item['item_name'], item['brand'], 
                item['category'], item['weight_grams'], item['created_date']
            ))
    
    def refresh_materials(self):
        """Refresh the materials display"""
        for item in self.materials_tree.get_children():
            self.materials_tree.delete(item)
        
        materials = self.db.list_all_materials()
        for material in materials:
            self.materials_tree.insert("", tk.END, values=(
                material['material_id'], material['material_name'], 
                material['density_g_per_cm3'], material['description']
            ))
    
    def refresh_impacts(self):
        """Refresh the environmental impacts display"""
        for item in self.impacts_tree.get_children():
            self.impacts_tree.delete(item)
        
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT ei.impact_id, m.material_name, ei.impact_category, 
               ei.impact_value, ei.unit, ei.source
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        ORDER BY m.material_name, ei.impact_category
        ''')
        
        impacts = cursor.fetchall()
        for impact in impacts:
            self.impacts_tree.insert("", tk.END, values=(
                impact['impact_id'], impact['material_name'], 
                impact['impact_category'], impact['impact_value'],
                impact['unit'], impact['source']
            ))
    
    # Add/Edit/Delete methods (full implementation)
    def add_clothing_item(self):
        """Add new clothing item with material composition"""
        print("Add clothing item clicked")  # Debug
        try:
            dialog = ClothingItemDialog(self.root, "Add Clothing Item", self.db)
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Dialog result: {dialog.result}")  # Debug
                data = dialog.result
                success = self.db.add_clothing_item(
                    data['qr_code'], data['name'], data['weight'], 
                    data['brand'], data['category']
                )
                print(f"Item add success: {success}")  # Debug
                
                if success:
                    # Add material composition
                    for material_name, percentage in data['materials']:
                        if percentage > 0:  # Only add materials with non-zero percentage
                            result = self.db.add_material_composition(data['qr_code'], material_name, percentage)
                            print(f"Material composition add: {material_name} {percentage}% - {result}")  # Debug
                    
                    self.refresh_clothing_items()
                    self.status_var.set(f"Added item: {data['qr_code']}")
                    messagebox.showinfo("Success", f"Item {data['qr_code']} added successfully!")
                else:
                    messagebox.showerror("Error", "Failed to add item (QR code may already exist)")
            else:
                print("Dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in add_clothing_item: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def add_material(self):
        """Add new material"""
        print("Add material clicked")  # Debug
        try:
            dialog = MaterialDialog(self.root, "Add Material")
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Material dialog result: {dialog.result}")  # Debug
                data = dialog.result
                result = self.db.add_material(data['name'], data['density'], data['description'])
                print(f"Material add result: {result}")  # Debug
                
                if result:
                    self.refresh_materials()
                    self.status_var.set(f"Added material: {data['name']}")
                    messagebox.showinfo("Success", f"Material '{data['name']}' added successfully!")
                else:
                    messagebox.showerror("Error", "Material already exists or invalid data")
            else:
                print("Material dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in add_material: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def edit_clothing_item(self):
        """Edit selected clothing item"""
        print("Edit clothing item clicked")  # Debug
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select an item to edit")
            return
        
        try:
            item_values = self.items_tree.item(selection[0])['values']
            qr_code = item_values[0]
            print(f"Editing item: {qr_code}")  # Debug
            
            # Get current item data
            current_item = self.db.get_clothing_item(qr_code)
            current_materials = self.db.get_material_composition(qr_code)
            print(f"Current item: {dict(current_item) if current_item else None}")  # Debug
            print(f"Current materials: {[dict(m) for m in current_materials] if current_materials else None}")  # Debug
            
            dialog = ClothingItemDialog(self.root, "Edit Clothing Item", self.db, 
                                       current_item, current_materials)
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Edit dialog result: {dialog.result}")  # Debug
                data = dialog.result
                
                # Update item details
                cursor = self.db.conn.cursor()
                cursor.execute('''
                UPDATE clothing_items 
                SET item_name=?, brand=?, category=?, weight_grams=?
                WHERE qr_code=?
                ''', (data['name'], data['brand'], data['category'], data['weight'], qr_code))
                
                # Delete old material composition
                cursor.execute('DELETE FROM clothing_material_composition WHERE qr_code=?', (qr_code,))
                
                # Add new material composition
                for material_name, percentage in data['materials']:
                    if percentage > 0:
                        # Get material ID
                        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
                        material = cursor.fetchone()
                        if material:
                            cursor.execute('''
                            INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
                            VALUES (?, ?, ?)
                            ''', (qr_code, material['material_id'], percentage))
                            print(f"Updated material composition: {material_name} {percentage}%")  # Debug
                
                self.db.conn.commit()
                self.refresh_clothing_items()
                self.status_var.set(f"Updated item: {qr_code}")
                messagebox.showinfo("Success", f"Item {qr_code} updated successfully!")
            else:
                print("Edit dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in edit_clothing_item: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def delete_clothing_item(self):
        """Delete selected clothing item"""
        print("Delete clothing item clicked")  # Debug
        selection = self.items_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select an item to delete")
            return
        
        try:
            item_values = self.items_tree.item(selection[0])['values']
            qr_code = item_values[0]
            item_name = item_values[1]
            print(f"Deleting item: {item_name} ({qr_code})")  # Debug
            
            if messagebox.askyesno("Confirm Delete", 
                                  f"Delete item '{item_name}' ({qr_code})?\n\nThis will also delete its material composition."):
                cursor = self.db.conn.cursor()
                # Delete material composition first (foreign key constraint)
                cursor.execute("DELETE FROM clothing_material_composition WHERE qr_code = ?", (qr_code,))
                # Delete clothing item
                cursor.execute("DELETE FROM clothing_items WHERE qr_code = ?", (qr_code,))
                self.db.conn.commit()
                self.refresh_clothing_items()
                self.status_var.set(f"Deleted item: {qr_code}")
                messagebox.showinfo("Success", f"Item {qr_code} deleted successfully!")
                print(f"Successfully deleted item: {qr_code}")  # Debug
        except Exception as e:
            print(f"Error deleting item: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def edit_material(self):
        """Edit selected material"""
        print("Edit material clicked")  # Debug
        selection = self.materials_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a material to edit")
            return
        
        try:
            material_values = self.materials_tree.item(selection[0])['values']
            material_id = material_values[0]
            print(f"Editing material ID: {material_id}")  # Debug
            
            # Get current material data
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM materials WHERE material_id = ?', (material_id,))
            current_material = cursor.fetchone()
            print(f"Current material: {dict(current_material) if current_material else None}")  # Debug
            
            dialog = MaterialDialog(self.root, "Edit Material", current_material)
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Edit material dialog result: {dialog.result}")  # Debug
                data = dialog.result
                cursor.execute('''
                UPDATE materials 
                SET material_name=?, density_g_per_cm3=?, description=?
                WHERE material_id=?
                ''', (data['name'].lower(), data['density'], data['description'], material_id))
                self.db.conn.commit()
                self.refresh_materials()
                self.status_var.set(f"Updated material: {data['name']}")
                messagebox.showinfo("Success", f"Material updated successfully!")
            else:
                print("Edit material dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in edit_material: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def delete_material(self):
        """Delete selected material"""
        print("Delete material clicked")  # Debug
        selection = self.materials_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select a material to delete")
            return
        
        try:
            material_values = self.materials_tree.item(selection[0])['values']
            material_id = material_values[0]
            material_name = material_values[1]
            print(f"Deleting material: {material_name} (ID: {material_id})")  # Debug
            
            # Check if material is used in any clothing items
            cursor = self.db.conn.cursor()
            cursor.execute('''
            SELECT COUNT(*) as count FROM clothing_material_composition 
            WHERE material_id = ?
            ''', (material_id,))
            usage_count = cursor.fetchone()['count']
            print(f"Material usage count: {usage_count}")  # Debug
            
            if usage_count > 0:
                if not messagebox.askyesno("Material In Use", 
                                         f"Material '{material_name}' is used in {usage_count} clothing item(s).\n\n"
                                         f"Deleting it will affect those items' environmental calculations.\n\n"
                                         f"Are you sure you want to delete it?"):
                    return
            else:
                if not messagebox.askyesno("Confirm Delete", f"Delete material '{material_name}'?"):
                    return
            
            # Delete environmental impacts first
            cursor.execute("DELETE FROM environmental_impacts WHERE material_id = ?", (material_id,))
            # Delete material compositions
            cursor.execute("DELETE FROM clothing_material_composition WHERE material_id = ?", (material_id,))
            # Delete material
            cursor.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
            self.db.conn.commit()
            
            self.refresh_materials()
            self.status_var.set(f"Deleted material: {material_name}")
            messagebox.showinfo("Success", f"Material '{material_name}' deleted successfully!")
            print(f"Successfully deleted material: {material_name}")  # Debug
        except Exception as e:
            print(f"Error deleting material: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def add_impact(self):
        """Add environmental impact data"""
        print("Add impact clicked")  # Debug
        try:
            dialog = ImpactDialog(self.root, "Add Environmental Impact", self.db)
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Impact dialog result: {dialog.result}")  # Debug
                data = dialog.result
                
                # Get material ID
                cursor = self.db.conn.cursor()
                cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (data['material'].lower(),))
                material = cursor.fetchone()
                
                if material:
                    cursor.execute('''
                    INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
                    VALUES (?, ?, ?, ?, ?)
                    ''', (material['material_id'], data['category'], data['value'], data['unit'], data['source']))
                    self.db.conn.commit()
                    self.refresh_impacts()
                    self.status_var.set(f"Added impact data for {data['material']}")
                    messagebox.showinfo("Success", "Environmental impact data added successfully!")
                    print(f"Successfully added impact for {data['material']}")  # Debug
                else:
                    messagebox.showerror("Error", f"Material '{data['material']}' not found")
            else:
                print("Impact dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in add_impact: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def edit_impact(self):
        """Edit selected environmental impact"""
        print("Edit impact clicked")  # Debug
        selection = self.impacts_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select an impact to edit")
            return
        
        try:
            impact_values = self.impacts_tree.item(selection[0])['values']
            impact_id = impact_values[0]
            print(f"Editing impact ID: {impact_id}")  # Debug
            
            # Get current impact data
            cursor = self.db.conn.cursor()
            cursor.execute('''
            SELECT ei.*, m.material_name
            FROM environmental_impacts ei
            JOIN materials m ON ei.material_id = m.material_id
            WHERE ei.impact_id = ?
            ''', (impact_id,))
            current_impact = cursor.fetchone()
            print(f"Current impact: {dict(current_impact) if current_impact else None}")  # Debug
            
            dialog = ImpactDialog(self.root, "Edit Environmental Impact", self.db, current_impact)
            self.root.wait_window(dialog.dialog)  # Wait for dialog to close
            
            if dialog.result:
                print(f"Edit impact dialog result: {dialog.result}")  # Debug
                data = dialog.result
                
                # Get material ID
                cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (data['material'].lower(),))
                material = cursor.fetchone()
                
                if material:
                    cursor.execute('''
                    UPDATE environmental_impacts 
                    SET material_id=?, impact_category=?, impact_value=?, unit=?, source=?
                    WHERE impact_id=?
                    ''', (material['material_id'], data['category'], data['value'], 
                         data['unit'], data['source'], impact_id))
                    self.db.conn.commit()
                    self.refresh_impacts()
                    self.status_var.set(f"Updated impact data")
                    messagebox.showinfo("Success", "Environmental impact data updated successfully!")
                    print(f"Successfully updated impact")  # Debug
                else:
                    messagebox.showerror("Error", f"Material '{data['material']}' not found")
            else:
                print("Edit impact dialog was cancelled")  # Debug
        except Exception as e:
            print(f"Error in edit_impact: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def delete_impact(self):
        """Delete selected environmental impact"""
        print("Delete impact clicked")  # Debug
        selection = self.impacts_tree.selection()
        if not selection:
            messagebox.showwarning("Selection Error", "Please select an impact to delete")
            return
        
        try:
            impact_values = self.impacts_tree.item(selection[0])['values']
            impact_id = impact_values[0]
            material_name = impact_values[1]
            category = impact_values[2]
            print(f"Deleting impact: {category} for {material_name} (ID: {impact_id})")  # Debug
            
            if messagebox.askyesno("Confirm Delete", 
                                  f"Delete {category} impact data for {material_name}?"):
                cursor = self.db.conn.cursor()
                cursor.execute("DELETE FROM environmental_impacts WHERE impact_id = ?", (impact_id,))
                self.db.conn.commit()
                self.refresh_impacts()
                self.status_var.set(f"Deleted impact data")
                messagebox.showinfo("Success", "Environmental impact data deleted successfully!")
                print(f"Successfully deleted impact")  # Debug
        except Exception as e:
            print(f"Error deleting impact: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")


class ClothingItemDialog:
    """Dialog for adding/editing clothing items with dynamic material composition"""
    def __init__(self, parent, title, db, current_item=None, current_materials=None):
        self.result = None
        self.db = db
        self.material_rows = []
        self.material_row_vars = []

        print(f"Creating dialog: {title}")  # Debug

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))

        # Create main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Basic item information
        basic_frame = ttk.LabelFrame(main_frame, text="Item Information", padding="10")
        basic_frame.pack(fill=tk.X, pady=(0, 10))

        # QR Code
        ttk.Label(basic_frame, text="QR Code:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.qr_entry = ttk.Entry(basic_frame, width=30)
        self.qr_entry.grid(row=0, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Name
        ttk.Label(basic_frame, text="Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(basic_frame, width=30)
        self.name_entry.grid(row=1, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Brand
        ttk.Label(basic_frame, text="Brand:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.brand_entry = ttk.Entry(basic_frame, width=30)
        self.brand_entry.grid(row=2, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Category
        ttk.Label(basic_frame, text="Category:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.category_entry = ttk.Entry(basic_frame, width=30)
        self.category_entry.grid(row=3, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        # Weight
        ttk.Label(basic_frame, text="Weight (g):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.weight_entry = ttk.Entry(basic_frame, width=30)
        self.weight_entry.grid(row=4, column=1, sticky=tk.EW, pady=5, padx=(10, 0))

        basic_frame.columnconfigure(1, weight=1)

        # Material composition section (dynamic)
        self.materials_frame = ttk.LabelFrame(main_frame, text="Material Composition", padding="10")
        self.materials_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(self.materials_frame, text="Enter percentages (must equal 100%):").pack(anchor=tk.W, pady=(0, 5))

        self.material_rows_container = ttk.Frame(self.materials_frame)
        self.material_rows_container.pack(fill=tk.BOTH, expand=True)

        # Total display (create this BEFORE adding the first row)
        self.total_label = ttk.Label(self.materials_frame, text="Total: 0%", foreground="red")
        self.total_label.pack(anchor=tk.W, pady=(5, 0))

        # Add the first material row by default
        self.add_material_row()

        # Add Material button
        ttk.Button(self.materials_frame, text="Add Material", command=self.add_material_row).pack(anchor=tk.W, pady=(5, 0))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)

        # Populate with current data if editing
        if current_item:
            self.qr_entry.insert(0, current_item['qr_code'])
            self.qr_entry.config(state='readonly')
            self.name_entry.insert(0, current_item['item_name'])
            self.brand_entry.insert(0, current_item['brand'] or '')
            self.category_entry.insert(0, current_item['category'] or '')
            self.weight_entry.insert(0, str(current_item['weight_grams']))
            if current_materials:
                for i, material in enumerate(current_materials):
                    if i == 0:
                        # Set first row
                        self.material_row_vars[0][0].set(material['material_name'])
                        self.material_row_vars[0][1].set(str(material['percentage']))
                    else:
                        self.add_material_row(material['material_name'], material['percentage'])

        # Focus on first entry
        if not current_item:
            self.qr_entry.focus()
        else:
            self.name_entry.focus()

        print("Dialog created successfully")  # Debug

    def add_material_row(self, material_name=None, percentage=None):
        available_materials = self.db.list_all_materials()
        row_frame = ttk.Frame(self.material_rows_container)
        row_frame.pack(fill=tk.X, pady=2)

        # Material dropdown
        material_var = tk.StringVar(value=material_name if material_name else "")
        material_dropdown = ttk.Combobox(row_frame, textvariable=material_var, state="readonly", width=18)
        material_dropdown['values'] = [m['material_name'] for m in available_materials]
        material_dropdown.pack(side=tk.LEFT, padx=(0, 5))

        # Percentage entry
        percent_var = tk.StringVar(value=str(percentage) if percentage is not None else "0")
        percent_entry = ttk.Entry(row_frame, textvariable=percent_var, width=8)
        percent_entry.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(row_frame, text="%").pack(side=tk.LEFT)

        # Remove button
        remove_btn = ttk.Button(row_frame, text="×", width=2, command=lambda: self.remove_material_row(row_frame))
        remove_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Track variables for later
        self.material_row_vars.append((material_var, percent_var))
        self.material_rows.append(row_frame)

        # Update total when changed
        percent_var.trace_add("write", lambda *args: self.update_total_percentage())
        material_var.trace_add("write", lambda *args: self.update_total_percentage())

        self.update_total_percentage()

    def remove_material_row(self, row_frame):
        idx = self.material_rows.index(row_frame)
        self.material_rows.pop(idx)
        self.material_row_vars.pop(idx)
        row_frame.destroy()
        self.update_total_percentage()

    def update_total_percentage(self):
        total = 0
        for material_var, percent_var in self.material_row_vars:
            try:
                val = float(percent_var.get())
                total += val
            except ValueError:
                pass
        self.total_label.config(text=f"Total: {total:.1f}%")
        if abs(total - 100) < 0.1:
            self.total_label.config(foreground="green")
        else:
            self.total_label.config(foreground="red")

    def save(self):
        print("Save button clicked")  # Debug
        try:
            qr_code = self.qr_entry.get().strip()
            name = self.name_entry.get().strip()
            weight_str = self.weight_entry.get().strip()
            print(f"Basic validation: QR='{qr_code}', Name='{name}', Weight='{weight_str}'")  # Debug
            if not qr_code or not name or not weight_str:
                messagebox.showerror("Input Error", "QR Code, Name, and Weight are required")
                return
            try:
                weight = int(weight_str)
            except ValueError:
                messagebox.showerror("Input Error", "Weight must be a number")
                return
            # Collect materials from dynamic rows
            materials = []
            total_percentage = 0
            for material_var, percent_var in self.material_row_vars:
                material = material_var.get()
                try:
                    percentage = float(percent_var.get())
                except ValueError:
                    percentage = 0
                if material and percentage > 0:
                    materials.append((material, percentage))
                    total_percentage += percentage
            if not materials:
                if not messagebox.askyesno("No Materials", "No materials specified. Continue anyway?"):
                    return
            elif abs(total_percentage - 100) > 0.1:
                if not messagebox.askyesno("Percentage Warning", f"Material percentages total {total_percentage}% (not 100%). Continue anyway?"):
                    return
            self.result = {
                'qr_code': qr_code,
                'name': name,
                'brand': self.brand_entry.get().strip() or None,
                'category': self.category_entry.get().strip() or None,
                'weight': weight,
                'materials': materials
            }
            print(f"Result set: {self.result}")  # Debug
            self.dialog.destroy()
        except Exception as e:
            print(f"Error in save: {e}")  # Debug
            messagebox.showerror("Error", f"An error occurred: {e}")

    def cancel(self):
        print("Cancel button clicked")  # Debug
        self.dialog.destroy()


class MaterialDialog:
    """Dialog for adding/editing materials"""
    def __init__(self, parent, title, current_material=None):
        self.result = None
        
        print(f"Creating material dialog: {title}")  # Debug
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # Create form
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Material name
        ttk.Label(main_frame, text="Material Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(main_frame, width=30)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Density
        ttk.Label(main_frame, text="Density (g/cm³):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.density_entry = ttk.Entry(main_frame, width=30)
        self.density_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        # Description
        ttk.Label(main_frame, text="Description:").grid(row=2, column=0, sticky=tk.NW, pady=5)
        self.description_text = tk.Text(main_frame, width=30, height=5)
        self.description_text.grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Populate with current data if editing
        if current_material:
            self.name_entry.insert(0, current_material['material_name'])
            if current_material['density_g_per_cm3']:
                self.density_entry.insert(0, str(current_material['density_g_per_cm3']))
            if current_material['description']:
                self.description_text.insert(1.0, current_material['description'])
        
        # Focus on first entry
        self.name_entry.focus()
        print("Material dialog created successfully")  # Debug
    
    def save(self):
        """Save the material data"""
        print("Material save button clicked")  # Debug
        
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Input Error", "Material name is required")
            return
        
        try:
            density = None
            density_text = self.density_entry.get().strip()
            if density_text:
                density = float(density_text)
        except ValueError:
            messagebox.showerror("Input Error", "Density must be a number")
            return
        
        self.result = {
            'name': name,
            'density': density,
            'description': self.description_text.get(1.0, tk.END).strip() or None
        }
        print(f"Material result set: {self.result}")  # Debug
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the dialog"""
        print("Material cancel button clicked")  # Debug
        self.dialog.destroy()


class ImpactDialog:
    """Dialog for adding/editing environmental impacts"""
    def __init__(self, parent, title, db, current_impact=None):
        self.result = None
        self.db = db
        
        print(f"Creating impact dialog: {title}")  # Debug
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x350")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # Create form
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Material selection
        ttk.Label(main_frame, text="Material:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.material_var = tk.StringVar()
        
        # Get available materials
        try:
            materials = self.db.list_all_materials()
            material_names = [mat['material_name'] for mat in materials]
            print(f"Available materials: {material_names}")  # Debug
        except Exception as e:
            print(f"Error getting materials: {e}")  # Debug
            material_names = []
        
        self.material_combo = ttk.Combobox(main_frame, textvariable=self.material_var, 
                                          values=material_names, state="readonly", width=27)
        self.material_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Impact category
        ttk.Label(main_frame, text="Impact Category:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.category_var = tk.StringVar()
        categories = ["water_usage", "carbon_footprint", "energy_usage", "chemical_usage", "land_use"]
        self.category_combo = ttk.Combobox(main_frame, textvariable=self.category_var, 
                                          values=categories, state="readonly", width=27)
        self.category_combo.grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        # Impact value
        ttk.Label(main_frame, text="Impact Value:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.value_entry = ttk.Entry(main_frame, width=30)
        self.value_entry.grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        # Unit
        ttk.Label(main_frame, text="Unit:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.unit_var = tk.StringVar()
        units = ["L/kg", "kg_CO2/kg", "MJ/kg", "kg/kg", "m²/kg"]
        self.unit_combo = ttk.Combobox(main_frame, textvariable=self.unit_var, 
                                      values=units, width=27)
        self.unit_combo.grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        # Source
        ttk.Label(main_frame, text="Source:").grid(row=4, column=0, sticky=tk.NW, pady=5)
        self.source_text = tk.Text(main_frame, width=30, height=4)
        self.source_text.grid(row=4, column=1, sticky=tk.EW, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Populate with current data if editing
        if current_impact:
            self.material_var.set(current_impact['material_name'])
            self.category_var.set(current_impact['impact_category'])
            self.value_entry.insert(0, str(current_impact['impact_value']))
            self.unit_var.set(current_impact['unit'])
            if current_impact['source']:
                self.source_text.insert(1.0, current_impact['source'])
        
        # Focus on first entry
        if not current_impact:
            self.material_combo.focus()
        else:
            self.value_entry.focus()
        
        print("Impact dialog created successfully")  # Debug
    
    def save(self):
        """Save the impact data"""
        print("Impact save button clicked")  # Debug
        
        material = self.material_var.get()
        category = self.category_var.get()
        unit = self.unit_var.get()
        
        print(f"Impact form data: material='{material}', category='{category}', unit='{unit}'")  # Debug
        
        if not all([material, category, unit]):
            messagebox.showerror("Input Error", "Material, category, and unit are required")
            return
        
        try:
            value_str = self.value_entry.get().strip()
            if not value_str:
                messagebox.showerror("Input Error", "Impact value is required")
                return
            value = float(value_str)
        except ValueError:
            messagebox.showerror("Input Error", "Impact value must be a number")
            return
        
        self.result = {
            'material': material,
            'category': category,
            'value': value,
            'unit': unit,
            'source': self.source_text.get(1.0, tk.END).strip() or None
        }
        print(f"Impact result set: {self.result}")  # Debug
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel the dialog"""
        print("Impact cancel button clicked")  # Debug
        self.dialog.destroy()


def main():
    """Main function to run the application"""
    # Check if database exists
    if not Path("fashion_env.db").exists():
        answer = messagebox.askyesno(
            "Database Not Found", 
            "No database found. Would you like to create a new database with sample data?"
        )
        if answer:
            try:
                from database_setup import setup_sample_data
                setup_sample_data()
                messagebox.showinfo("Success", "Database created with sample data!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create database: {e}")
                return
        else:
            messagebox.showinfo("Info", "Please run database_setup.py first to create the database")
            return
    
    # Create and run the app
    root = tk.Tk()
    app = FashionEnvironmentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()