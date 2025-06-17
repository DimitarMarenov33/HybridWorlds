import sqlite3
import json
from datetime import datetime
from pathlib import Path

class FashionEnvironmentDB:
    def __init__(self, db_path="fashion_env.db"):
        """Initialize database connection and create tables if they don't exist"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
        self.create_tables()
    
    def create_tables(self):
        """Create all necessary tables"""
        cursor = self.conn.cursor()
        
        # Materials table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            material_id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name VARCHAR(50) UNIQUE NOT NULL,
            density_g_per_cm3 DECIMAL(4,3),
            description TEXT,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Environmental impacts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS environmental_impacts (
            impact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER,
            impact_category VARCHAR(30),
            impact_value DECIMAL(10,4) NOT NULL,
            unit VARCHAR(20) NOT NULL,
            source VARCHAR(100),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_id) REFERENCES materials(material_id)
        )
        ''')
        
        # Clothing items table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothing_items (
            qr_code VARCHAR(50) PRIMARY KEY,
            item_name VARCHAR(100) NOT NULL,
            brand VARCHAR(50),
            category VARCHAR(30),
            weight_grams INTEGER NOT NULL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Clothing material composition table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS clothing_material_composition (
            composition_id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code VARCHAR(50),
            material_id INTEGER,
            percentage DECIMAL(5,2) NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
            FOREIGN KEY (qr_code) REFERENCES clothing_items(qr_code),
            FOREIGN KEY (material_id) REFERENCES materials(material_id)
        )
        ''')
        
        # Scan history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scan_history (
            scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            qr_code VARCHAR(50),
            scan_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            calculated_impacts TEXT,  -- JSON string
            session_id VARCHAR(50),
            FOREIGN KEY (qr_code) REFERENCES clothing_items(qr_code)
        )
        ''')
        
        self.conn.commit()
        print(f"Database created/verified at: {Path(self.db_path).absolute()}")
    
    def add_material(self, name, density=None, description=None):
        """Add a new material to the database"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO materials (material_name, density_g_per_cm3, description)
            VALUES (?, ?, ?)
            ''', (name.lower(), density, description))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Material '{name}' already exists")
            return None
    
    def add_environmental_impact(self, material_name, category, value, unit, source=None):
        """Add environmental impact data for a material"""
        cursor = self.conn.cursor()
        
        # Get material ID
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
        material = cursor.fetchone()
        
        if not material:
            print(f"Material '{material_name}' not found. Add the material first.")
            return None
        
        cursor.execute('''
        INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
        VALUES (?, ?, ?, ?, ?)
        ''', (material['material_id'], category, value, unit, source))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def add_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
        """Add a clothing item"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO clothing_items (qr_code, item_name, brand, category, weight_grams)
            VALUES (?, ?, ?, ?, ?)
            ''', (qr_code, name, brand, category, weight_grams))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"QR code '{qr_code}' already exists")
            return False
    
    def add_material_composition(self, qr_code, material_name, percentage):
        """Add material composition for a clothing item"""
        cursor = self.conn.cursor()
        
        # Get material ID
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name.lower(),))
        material = cursor.fetchone()
        
        if not material:
            print(f"Material '{material_name}' not found")
            return False
        
        cursor.execute('''
        INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
        VALUES (?, ?, ?)
        ''', (qr_code, material['material_id'], percentage))
        
        self.conn.commit()
        return True
    
    def get_clothing_item(self, qr_code):
        """Get clothing item details by QR code"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clothing_items WHERE qr_code = ?', (qr_code,))
        return cursor.fetchone()
    
    def get_material_composition(self, qr_code):
        """Get material composition for a clothing item"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT m.material_name, cmc.percentage
        FROM clothing_material_composition cmc
        JOIN materials m ON cmc.material_id = m.material_id
        WHERE cmc.qr_code = ?
        ''', (qr_code,))
        return cursor.fetchall()
    
    def get_environmental_impact(self, material_name, impact_category):
        """Get environmental impact value for a material and category"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT ei.impact_value, ei.unit
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        WHERE m.material_name = ? AND ei.impact_category = ?
        ''', (material_name.lower(), impact_category))
        return cursor.fetchone()
    
    def calculate_total_impact(self, qr_code, impact_category):
        """Calculate total environmental impact for a clothing item"""
        clothing_item = self.get_clothing_item(qr_code)
        if not clothing_item:
            return None
        
        material_composition = self.get_material_composition(qr_code)
        total_impact = 0
        unit = None
        
        for material in material_composition:
            impact_data = self.get_environmental_impact(material['material_name'], impact_category)
            if impact_data:
                # Calculate weighted impact: impact_per_kg * percentage * weight_in_kg
                weighted_impact = (
                    impact_data['impact_value'] * 
                    (material['percentage'] / 100) * 
                    (clothing_item['weight_grams'] / 1000)
                )
                total_impact += weighted_impact
                unit = impact_data['unit']
        
        return {'value': total_impact, 'unit': unit} if unit else None
    
    def list_all_materials(self):
        """List all materials in the database"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM materials ORDER BY material_name')
        return cursor.fetchall()
    
    def list_all_clothing_items(self):
        """List all clothing items"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM clothing_items ORDER BY item_name')
        return cursor.fetchall()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def setup_sample_data():
    """Set up the database with sample data for testing"""
    db = FashionEnvironmentDB()
    
    print("Adding materials...")
    # Add common materials
    materials = [
        ("cotton", 1.54, "Natural fiber from cotton plants"),
        ("polyester", 1.38, "Synthetic polymer fiber"),
        ("wool", 1.31, "Natural fiber from sheep"),
        ("nylon", 1.14, "Synthetic polymer fiber"),
        ("linen", 1.50, "Natural fiber from flax plants"),
        ("silk", 1.25, "Natural protein fiber from silkworms"),
        ("elastane", 1.20, "Synthetic elastic fiber (spandex)"),
        ("viscose", 1.50, "Semi-synthetic fiber from wood pulp")
    ]
    
    for name, density, desc in materials:
        db.add_material(name, density, desc)
    
    print("Adding environmental impact data...")
    # Add environmental impacts (sample data based on research)
    impacts = [
        # Water usage (L/kg)
        ("cotton", "water_usage", 2700, "L/kg", "Textile Exchange 2017"),
        ("polyester", "water_usage", 70, "L/kg", "Textile Exchange 2017"),
        ("wool", "water_usage", 6000, "L/kg", "Textile Exchange 2017"),
        ("nylon", "water_usage", 60, "L/kg", "Higg MSI"),
        ("linen", "water_usage", 500, "L/kg", "European Flax"),
        
        # Carbon footprint (kg CO2/kg)
        ("cotton", "carbon_footprint", 5.9, "kg_CO2/kg", "Textile Exchange 2017"),
        ("polyester", "carbon_footprint", 9.5, "kg_CO2/kg", "Textile Exchange 2017"),
        ("wool", "carbon_footprint", 10.4, "kg_CO2/kg", "Textile Exchange 2017"),
        ("nylon", "carbon_footprint", 7.6, "kg_CO2/kg", "Higg MSI"),
        ("linen", "carbon_footprint", 0.9, "kg_CO2/kg", "European Flax"),
        
        # Energy usage (MJ/kg)
        ("cotton", "energy_usage", 55, "MJ/kg", "Ecoinvent 3.0"),
        ("polyester", "energy_usage", 125, "MJ/kg", "Ecoinvent 3.0"),
        ("wool", "energy_usage", 63, "MJ/kg", "Ecoinvent 3.0"),
        ("nylon", "energy_usage", 138, "MJ/kg", "Ecoinvent 3.0"),
    ]
    
    for material, category, value, unit, source in impacts:
        db.add_environmental_impact(material, category, value, unit, source)
    
    print("Adding sample clothing items...")
    # Add sample clothing items
    clothing_items = [
        ("SHIRT001", "Cotton T-Shirt", 180, "Generic", "shirt"),
        ("JEANS001", "Denim Jeans", 600, "Generic", "pants"),
        ("SWEAT001", "Cotton-Poly Hoodie", 450, "Generic", "sweatshirt"),
        ("DRESS001", "Summer Dress", 220, "Generic", "dress"),
        ("SOCK001", "Cotton Socks", 50, "Generic", "socks"),
    ]
    
    for qr_code, name, weight, brand, category in clothing_items:
        db.add_clothing_item(qr_code, name, weight, brand, category)
    
    print("Adding material compositions...")
    # Add material compositions
    compositions = [
        # Cotton T-Shirt: 100% cotton
        ("SHIRT001", "cotton", 100),
        
        # Denim Jeans: 98% cotton, 2% elastane
        ("JEANS001", "cotton", 98),
        ("JEANS001", "elastane", 2),
        
        # Hoodie: 70% cotton, 30% polyester
        ("SWEAT001", "cotton", 70),
        ("SWEAT001", "polyester", 30),
        
        # Summer Dress: 60% cotton, 40% linen
        ("DRESS001", "cotton", 60),
        ("DRESS001", "linen", 40),
        
        # Socks: 80% cotton, 18% nylon, 2% elastane
        ("SOCK001", "cotton", 80),
        ("SOCK001", "nylon", 18),
        ("SOCK001", "elastane", 2),
    ]
    
    for qr_code, material, percentage in compositions:
        db.add_material_composition(qr_code, material, percentage)
    
    print("\nSample data setup complete!")
    
    # Test calculations
    print("\n=== Testing Calculations ===")
    test_items = ["SHIRT001", "JEANS001", "SWEAT001"]
    impact_categories = ["water_usage", "carbon_footprint", "energy_usage"]
    
    for item in test_items:
        clothing = db.get_clothing_item(item)
        print(f"\n{clothing['item_name']} ({item}):")
        
        for category in impact_categories:
            result = db.calculate_total_impact(item, category)
            if result:
                print(f"  {category}: {result['value']:.2f} {result['unit']}")
    
    db.close()


if __name__ == "__main__":
    # Run this to set up your database with sample data
    setup_sample_data()
    
    print(f"\nDatabase file created at: {Path('fashion_env.db').absolute()}")
    print("\nTo view/edit the database, you can use:")
    print("1. DB Browser for SQLite (free GUI tool)")
    print("2. SQLite command line")
    print("3. Any SQLite-compatible database viewer")