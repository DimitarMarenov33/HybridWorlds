# app.py - Add this file to your existing project
from flask import Flask, render_template, request, jsonify
import sqlite3
import os

app = Flask(__name__)

# Use your existing database class structure
class FashionEnvironmentDB:
    def __init__(self, db_path="fashion_env.db"):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_clothing_item(self, qr_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clothing_items WHERE qr_code = ?', (qr_code,))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_material_composition(self, qr_code):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT m.material_name, cmc.percentage
        FROM clothing_material_composition cmc
        JOIN materials m ON cmc.material_id = m.material_id
        WHERE cmc.qr_code = ?
        ''', (qr_code,))
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_environmental_impact(self, material_name, impact_category):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT ei.impact_value, ei.unit
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        WHERE m.material_name = ? AND ei.impact_category = ?
        ''', (material_name.lower(), impact_category))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def list_all_clothing_items(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clothing_items ORDER BY item_name')
        result = cursor.fetchall()
        conn.close()
        return result

# Initialize database
db = FashionEnvironmentDB()

@app.route('/')
def index():
    """Main page with QR scanner"""
    return render_template('index.html')

@app.route('/api/analyze/<qr_code>')
def analyze_item(qr_code):
    """API endpoint to analyze clothing item - same logic as your desktop app"""
    try:
        # Get clothing item
        item = db.get_clothing_item(qr_code)
        if not item:
            return jsonify({
                'error': True,
                'message': f'No item found with QR code: {qr_code}',
                'available_items': [dict(item) for item in db.list_all_clothing_items()]
            })
        
        # Get material composition
        materials = db.get_material_composition(qr_code)
        
        # Calculate environmental impacts - exact same logic as your desktop app
        impact_categories = ["water_usage", "carbon_footprint", "energy_usage"]
        category_names = {
            "water_usage": "💧 Water Usage",
            "carbon_footprint": "🏭 Carbon Footprint", 
            "energy_usage": "⚡ Energy Usage"
        }
        
        results = {
            'item': dict(item),
            'materials': [dict(mat) for mat in materials],
            'impacts': {}
        }
        
        total_impacts = {}
        
        for category in impact_categories:
            category_total = 0
            unit = None
            material_impacts = []
            
            for material in materials:
                impact_data = db.get_environmental_impact(material['material_name'], category)
                if impact_data:
                    # Same calculation as your desktop app
                    material_impact = (
                        impact_data['impact_value'] * 
                        (material['percentage'] / 100) * 
                        (item['weight_grams'] / 1000)
                    )
                    category_total += material_impact
                    unit = impact_data['unit']
                    
                    material_impacts.append({
                        'material': material['material_name'].title(),
                        'impact': material_impact,
                        'percentage': material['percentage'],
                        'base_impact': impact_data['impact_value'],
                        'unit': impact_data['unit']
                    })
            
            if unit:
                # Remove /kg from final unit display (same as your desktop app fix)
                final_unit = unit.replace('/kg', '')
                total_impacts[category] = {
                    'value': category_total, 
                    'unit': final_unit,
                    'name': category_names[category],
                    'materials': material_impacts
                }
        
        results['impacts'] = total_impacts
        
        # Add tube scale calculation
        water_usage = total_impacts.get('water_usage', {}).get('value', 0)
        results['tube_scale'] = calculate_tube_scale(water_usage)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)})

def calculate_tube_scale(water_liters):
    """Convert water usage to tube scale (0.7L = 0.06ml, 4800L = 400ml)"""
    if water_liters <= 0:
        return 0
    
    # Scale mapping: 4800L = 400ml, so 1L = 0.0833ml on tube scale
    tube_volume = water_liters * (400 / 4800)
    return round(tube_volume, 2)

@app.route('/database')
def database_view():
    """Database management page"""
    return render_template('database.html')

@app.route('/api/items')
def get_all_items():
    """Get all clothing items for database view"""
    try:
        items = db.list_all_clothing_items()
        return jsonify([dict(item) for item in items])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)