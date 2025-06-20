# app.py - Add this file to your existing project
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response
import sqlite3
import os
from datetime import datetime
from flask import request, jsonify
import traceback

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for session

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
    
    def list_all_materials(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM materials ORDER BY material_name')
        result = cursor.fetchall()
        conn.close()
        return result
    
    def add_clothing_item(self, qr_code, name, weight_grams, brand=None, category=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO clothing_items (qr_code, item_name, brand, category, weight_grams)
            VALUES (?, ?, ?, ?, ?)
            ''', (qr_code, name, brand, category, weight_grams))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def add_material(self, name, density=None, description=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
            INSERT INTO materials (material_name, density_g_per_cm3, description)
            VALUES (?, ?, ?)
            ''', (name.lower(), density, description))
            conn.commit()
            material_id = cursor.lastrowid
            conn.close()
            return material_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def add_material_composition(self, qr_code, material_name, percentage):
        """Add material composition for a clothing item"""
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
            INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
            VALUES (?, ?, ?)
            ''', (qr_code, material['material_id'], percentage))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error:
            conn.close()
            return False
    
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
        """Close database connection (compatibility method)"""
        # Since we use get_connection() pattern, individual connections are closed in methods
        pass

# Initialize database
db = FashionEnvironmentDB()

@app.route('/', methods=['GET'])
def username_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('username.html')

@app.route('/set_username', methods=['POST'])
def set_username():
    username = request.form.get('username')
    if username:
        session['username'] = username
        # Save username to the database if not already present
        conn = sqlite3.connect('fashion_env.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE)''')
        cursor.execute('''INSERT OR IGNORE INTO users (username) VALUES (?)''', (username,))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    return redirect(url_for('username_page'))

@app.route('/index')
def index():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    """Main page with QR scanner"""
    return render_template('index.html', username=username)

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



@app.route('/api/items')
def get_all_items():
    """Get all clothing items for database view"""
    try:
        items = db.list_all_clothing_items()
        return jsonify([dict(item) for item in items])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)})

def normalize(value, best, worst):
    if worst == best:
        return 1.0
    return max(0, min(1, (worst - value) / (worst - best)))

@app.route("/cart")
def cart():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    
    cart_items = session.get('cart_items', [])
    summary = {
        "subtotal": "0.00",
        "total": "0.00",
        "free_shipping_threshold": "22.01"
    }

    minmax = {
        'water_usage': (5.91996, 6000),
        'carbon_footprint': (0.9, 10.4),
        'energy_usage': (1.09323, 138)
    }
    
    def get_item_score(qr_code):
        impacts = {}
        item = db.get_clothing_item(qr_code)
        if not item:
            return None
        materials = db.get_material_composition(qr_code)
        for category in minmax:
            total = 0
            for mat in materials:
                impact_data = db.get_environmental_impact(mat['material_name'], category)
                if impact_data:
                    total += impact_data['impact_value'] * (mat['percentage']/100) * (item['weight_grams']/1000)
            impacts[category] = total
        scores = [normalize(impacts[cat], minmax[cat][0], minmax[cat][1]) for cat in minmax]
        return sum(scores) / len(scores) * 100
    
    item_scores = []
    if cart_items:
        for item in cart_items:
            score = get_item_score(item['qr_code'])
            if score is not None:
                item_scores.append({'name': item['name'], 'score': round(score, 1)})
        scores = [s['score'] for s in item_scores]
        if scores:
            sustainability_score = round(sum(scores) / len(scores), 1)
        else:
            sustainability_score = None
    else:
        sustainability_score = None
    
    return render_template("cart.html", cart_items=cart_items, summary=summary, hide_nav=True, username=username, sustainability_score=sustainability_score, item_scores=item_scores)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('username_page'))

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Unified route to handle both form submissions and JSON requests for adding items to cart"""
    
    username = session.get('username')
    if not username:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Please log in first'})
        else:
            return redirect(url_for('username_page'))
    
    # Initialize cart in session if it doesn't exist
    if 'cart_items' not in session:
        session['cart_items'] = []
    
    # Check if cart already has 3 items
    if len(session['cart_items']) >= 3:
        return jsonify({'success': False, 'message': 'Maximum 3 items allowed in cart'})
    
    # Handle different request types
    if request.is_json:
        # JSON request (from QR scanner)
        data = request.json
        qr_code = data.get('qr_code')
        
        if not qr_code:
            return jsonify({'success': False, 'message': 'No QR code provided'})
        
        try:
            # Check if item already in cart
            if any(cart_item['qr_code'] == qr_code for cart_item in session['cart_items']):
                return jsonify({'success': False, 'message': 'Item already in cart'})
            
            # Fetch item details from database using your existing logic
            # You'll need to implement get_item_details_by_qr function
            item_details = get_item_details_by_qr(qr_code)
            
            if not item_details:
                return jsonify({'success': False, 'message': 'Item not found'})
            
            # Create cart item with fetched details
            cart_item = {
                'name': item_details['item_name'],
                'qr_code': qr_code,
                'impact': f"{item_details['weight_grams']}g",  # You can enhance this with full environmental data
                'price': '0.00',  # Placeholder
                'quantity': 1,
                'brand': item_details.get('brand', ''),
                'category': item_details.get('category', ''),
                'options': []  # Add any options if needed
            }
            
            session['cart_items'].append(cart_item)
            session.modified = True
            
            return jsonify({
                'success': True, 
                'message': 'Item added to cart',
                'item_name': item_details['item_name']
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error adding item: {str(e)}'})
    
    else:
        # Form request (your existing functionality)
        item_name = request.form.get('item_name')
        qr_code = request.form.get('qr_code')
        environmental_impact = request.form.get('environmental_impact')
        
        if not item_name or not qr_code:
            return jsonify({'success': False, 'message': 'Missing required fields'})
        
        # Check if item already in cart
        if any(cart_item['qr_code'] == qr_code for cart_item in session['cart_items']):
            return jsonify({'success': False, 'message': 'Item already in cart'})
        
        # Create cart item from form data
        cart_item = {
            'name': item_name,
            'qr_code': qr_code,
            'impact': environmental_impact,
            'price': '0.00',  # Placeholder
            'quantity': 1,
            'options': []  # Add any options if needed
        }
        
        session['cart_items'].append(cart_item)
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Item added to cart'})


def get_item_details_by_qr(qr_code):
    """
    Helper function to get item details by QR code from your database
    Replace this with your actual database query logic
    """
    try:
        # Using your existing database connection logic
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query to get item details
        cursor.execute("""
            SELECT qr_code, item_name, brand, category, weight_grams, created_date
            FROM clothing_items 
            WHERE qr_code = %s
        """, (qr_code,))
        
        row = cursor.fetchone()
        
        if row:
            return {
                'qr_code': row[0],
                'item_name': row[1],
                'brand': row[2],
                'category': row[3],
                'weight_grams': row[4],
                'created_date': row[5]
            }
        else:
            return None
            
    except Exception as e:
        print(f"Database error: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()
            
@app.route('/api/suggestions/<query>')
def get_suggestions(query):
    """Get QR code suggestions based on user input"""
    try:
        # Get all clothing items from database
        items = db.list_all_clothing_items()
        
        # Filter items that match the query (case-insensitive)
        suggestions = []
        query_lower = query.lower()
        
        for item in items:
            if (query_lower in item['qr_code'].lower() or 
                query_lower in item['item_name'].lower()):
                suggestions.append({
                    'qr_code': item['qr_code'],
                    'item_name': item['item_name']
                })
        
        return jsonify({'suggestions': suggestions[:5]})  # Limit to 5 suggestions
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    """Remove an item from the cart"""
    if 'username' not in session:
        return jsonify({'success': False, 'message': 'User not logged in'})
    
    try:
        data = request.get_json()
        item_name = data.get('item_name')
        
        if not item_name:
            return jsonify({'success': False, 'message': 'Item name is required'})
        
        # Get current cart
        cart = session.get('cart_items', [])
        
        # Find and remove the item
        original_length = len(cart)
        cart = [item for item in cart if item['name'] != item_name]
        
        if len(cart) == original_length:
            return jsonify({'success': False, 'message': 'Item not found in cart'})
        
        # Update session
        session['cart_items'] = cart
        
        return jsonify({'success': True, 'message': 'Item removed from cart'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error removing item: {str(e)}'})

@app.route('/save_choice', methods=['POST'])
def save_choice():
    data = request.get_json()
    session['last_choice'] = data
    session.modified = True
    return jsonify({'success': True})

@app.route('/get_last_choice')
def get_last_choice():
    return jsonify(session.get('last_choice', {}))

@app.route('/save_current_choice_for_receipt', methods=['POST'])
def save_current_choice_for_receipt():
    """Save the current cart details to the session before showing the receipt."""
    data = request.get_json()
    session['current_choice_for_receipt'] = data
    session.modified = True
    return jsonify({'success': True})

@app.route('/receipt')
def receipt():
    """Render the printable receipt page."""
    username = session.get('username', 'Guest')
    # These are the choices for the *current* receipt view
    current_choice = session.get('current_choice_for_receipt', {})
    prev_choice = session.get('last_choice', {})
    if not current_choice:
        # If there's no data, redirect to cart to prevent errors
        return redirect(url_for('cart'))
    response = make_response(render_template(
        'receipt.html',
        username=username,
        date=datetime.now().strftime("%B %d, %Y at %I:%M %p"),
        current_choice=current_choice,
        prev_choice=prev_choice
    ))
    # NOW, after we've prepared the receipt with the old 'last_choice',
    # we update 'last_choice' to be the 'current_choice' for the *next* transaction.
    session['last_choice'] = current_choice
    session.modified = True
    return response

@app.route('/api/cart_summary')
def api_cart_summary():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    cart_items = session.get('cart_items', [])
    minmax = {
        'water_usage': (5.91996, 6000),
        'carbon_footprint': (0.9, 10.4),
        'energy_usage': (1.09323, 138)
    }
    def get_item_score(qr_code):
        impacts = {}
        item = db.get_clothing_item(qr_code)
        if not item:
            return None
        materials = db.get_material_composition(qr_code)
        for category in minmax:
            total = 0
            for mat in materials:
                impact_data = db.get_environmental_impact(mat['material_name'], category)
                if impact_data:
                    total += impact_data['impact_value'] * (mat['percentage']/100) * (item['weight_grams']/1000)
            impacts[category] = total
        scores = [normalize(impacts[cat], minmax[cat][0], minmax[cat][1]) for cat in minmax]
        return sum(scores) / len(scores) * 100
    item_scores = []
    if cart_items:
        for item in cart_items:
            score = get_item_score(item['qr_code'])
            if score is not None:
                item_scores.append({'name': item['name'], 'score': round(score, 1)})
        scores = [s['score'] for s in item_scores]
        if scores:
            sustainability_score = round(sum(scores) / len(scores), 1)
        else:
            sustainability_score = None
    else:
        sustainability_score = None
    return jsonify({
        'sustainability_score': sustainability_score,
        'item_scores': item_scores
    })

# Materials API endpoints
@app.route('/api/materials', methods=['GET'])
def get_all_materials():
    """Get all materials with impact counts"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get materials with impact counts
        cursor.execute('''
        SELECT m.*, 
               COUNT(ei.impact_id) as impact_count
        FROM materials m
        LEFT JOIN environmental_impacts ei ON m.material_id = ei.material_id
        GROUP BY m.material_id, m.material_name, m.density_g_per_cm3, m.description
        ORDER BY m.material_name
        ''')
        
        materials = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(material) for material in materials])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials', methods=['POST'])
def add_material():
    """Add a new material"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip().lower()
        density = data.get('density')
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': True, 'message': 'Material name is required'}), 400
        
        # Convert empty strings to None
        density = density if density else None
        description = description if description else None
        
        material_id = db.add_material(name, density, description)
        
        if material_id:
            return jsonify({'success': True, 'material_id': material_id})
        else:
            return jsonify({'error': True, 'message': 'Material already exists or invalid data'}), 400
            
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials/<int:material_id>', methods=['PUT'])
def update_material(material_id):
    """Update an existing material"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip().lower()
        density = data.get('density')
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'error': True, 'message': 'Material name is required'}), 400
        
        # Convert empty strings to None
        density = density if density else None
        description = description if description else None
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE materials 
        SET material_name=?, density_g_per_cm3=?, description=?
        WHERE material_id=?
        ''', (name, density, description, material_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/materials/<int:material_id>', methods=['DELETE'])
def delete_material(material_id):
    """Delete a material and its associated data"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if material is used in clothing items
        cursor.execute('''
        SELECT COUNT(*) as count FROM clothing_material_composition 
        WHERE material_id = ?
        ''', (material_id,))
        usage_count = cursor.fetchone()['count']
        
        # Delete environmental impacts first
        cursor.execute("DELETE FROM environmental_impacts WHERE material_id = ?", (material_id,))
        
        # Delete material compositions
        cursor.execute("DELETE FROM clothing_material_composition WHERE material_id = ?", (material_id,))
        
        # Delete material
        cursor.execute("DELETE FROM materials WHERE material_id = ?", (material_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'affected_items': usage_count})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Material composition endpoints
@app.route('/api/materials/<qr_code>')
def get_item_materials(qr_code):
    """Get material composition for a specific item"""
    try:
        materials = db.get_material_composition(qr_code)
        return jsonify([dict(material) for material in materials])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Environmental impacts API endpoints
@app.route('/api/impacts', methods=['GET'])
def get_all_impacts():
    """Get all environmental impacts"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT ei.impact_id, m.material_name, ei.impact_category, 
               ei.impact_value, ei.unit, ei.source
        FROM environmental_impacts ei
        JOIN materials m ON ei.material_id = m.material_id
        ORDER BY m.material_name, ei.impact_category
        ''')
        
        impacts = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(impact) for impact in impacts])
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts', methods=['POST'])
def add_impact():
    """Add a new environmental impact"""
    try:
        data = request.get_json()
        
        material_name = data.get('material_name', '').strip().lower()
        impact_category = data.get('impact_category', '').strip()
        impact_value = data.get('impact_value')
        unit = data.get('unit', '').strip()
        source = data.get('source', '').strip()
        
        if not all([material_name, impact_category, impact_value is not None, unit]):
            return jsonify({'error': True, 'message': 'All fields except source are required'}), 400
        
        # Get material ID
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return jsonify({'error': True, 'message': f'Material "{material_name}" not found'}), 404
        
        # Convert empty string to None for source
        source = source if source else None
        
        cursor.execute('''
        INSERT INTO environmental_impacts (material_id, impact_category, impact_value, unit, source)
        VALUES (?, ?, ?, ?, ?)
        ''', (material['material_id'], impact_category, impact_value, unit, source))
        
        impact_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'impact_id': impact_id})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts/<int:impact_id>', methods=['PUT'])
def update_impact(impact_id):
    """Update an existing environmental impact"""
    try:
        data = request.get_json()
        
        material_name = data.get('material_name', '').strip().lower()
        impact_category = data.get('impact_category', '').strip()
        impact_value = data.get('impact_value')
        unit = data.get('unit', '').strip()
        source = data.get('source', '').strip()
        
        if not all([material_name, impact_category, impact_value is not None, unit]):
            return jsonify({'error': True, 'message': 'All fields except source are required'}), 400
        
        # Get material ID
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
        material = cursor.fetchone()
        
        if not material:
            conn.close()
            return jsonify({'error': True, 'message': f'Material "{material_name}" not found'}), 404
        
        # Convert empty string to None for source
        source = source if source else None
        
        cursor.execute('''
        UPDATE environmental_impacts 
        SET material_id=?, impact_category=?, impact_value=?, unit=?, source=?
        WHERE impact_id=?
        ''', (material['material_id'], impact_category, impact_value, unit, source, impact_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/impacts/<int:impact_id>', methods=['DELETE'])
def delete_impact(impact_id):
    """Delete an environmental impact"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM environmental_impacts WHERE impact_id = ?", (impact_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Clothing items CRUD endpoints
@app.route('/api/items', methods=['POST'])
def add_clothing_item():
    try:
        data = request.get_json()
        print(f"Raw request data: {data}")  # Debug print
        
        # Check if data is None
        if data is None:
            return jsonify({'error': True, 'message': 'No JSON data received'}), 400
        
        # Handle None values properly with extra safety
        qr_code = str(data.get('qr_code') or '').strip()
        name = str(data.get('name') or '').strip()
        brand = str(data.get('brand') or '').strip()
        category = str(data.get('category') or '').strip()
        weight = data.get('weight')
        materials = data.get('materials', [])
        
        print(f"Parsed data - QR: {qr_code}, Name: {name}, Weight: {weight}")  # Debug
        print(f"Materials: {materials}")  # Debug
        
        if not qr_code or not name or not weight:
            return jsonify({'error': True, 'message': 'QR code, name, and weight are required'}), 400
        
        # Convert empty strings to None
        brand = brand if brand else None
        category = category if category else None
        
        # Add clothing item
        success = db.add_clothing_item(qr_code, name, int(weight), brand, category)
        
        if not success:
            return jsonify({'error': True, 'message': 'QR code already exists'}), 400
        
        # Add material composition with better error handling
        if materials:
            conn = db.get_connection()
            cursor = conn.cursor()
            
            for i, material_data in enumerate(materials):
                print(f"Processing material {i}: {material_data}")  # Debug
                
                if material_data is None:
                    continue
                    
                material_name = str(material_data.get('material_name') or '').strip().lower()
                percentage = material_data.get('percentage')
                
                print(f"Material name: {material_name}, Percentage: {percentage}")  # Debug
                
                if material_name and percentage and float(percentage) > 0:
                    # Get material ID
                    cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
                    material = cursor.fetchone()
                    
                    if material:
                        cursor.execute('''
                        INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
                        VALUES (?, ?, ?)
                        ''', (qr_code, material['material_id'], float(percentage)))
                        print(f"Added material composition: {material_name} - {percentage}%")
            
            conn.commit()
            conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        import traceback
        print(f"Full error traceback:")
        print(traceback.format_exc())
        return jsonify({'error': True, 'message': str(e)}), 500
    
@app.route('/api/items/<qr_code>', methods=['PUT'])
def update_clothing_item(qr_code):
    """Update an existing clothing item"""
    try:
        data = request.get_json()
        
        name = data.get('name', '').strip()
        brand = data.get('brand', '').strip()
        category = data.get('category', '').strip()
        weight = data.get('weight')
        materials = data.get('materials', [])
        
        if not all([name, weight]):
            return jsonify({'error': True, 'message': 'Name and weight are required'}), 400
        
        # Convert empty strings to None
        brand = brand if brand else None
        category = category if category else None
        
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Update item details
        cursor.execute('''
        UPDATE clothing_items 
        SET item_name=?, brand=?, category=?, weight_grams=?
        WHERE qr_code=?
        ''', (name, brand, category, weight, qr_code))
        
        # Delete old material composition
        cursor.execute('DELETE FROM clothing_material_composition WHERE qr_code=?', (qr_code,))
        
        # Add new material composition
        for material_data in materials:
            material_name = material_data.get('material_name', '').strip().lower()
            percentage = material_data.get('percentage')
            
            if material_name and percentage and percentage > 0:
                # Get material ID
                cursor.execute('SELECT material_id FROM materials WHERE material_name = ?', (material_name,))
                material = cursor.fetchone()
                
                if material:
                    cursor.execute('''
                    INSERT INTO clothing_material_composition (qr_code, material_id, percentage)
                    VALUES (?, ?, ?)
                    ''', (qr_code, material['material_id'], percentage))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

@app.route('/api/items/<qr_code>', methods=['DELETE'])
def delete_clothing_item(qr_code):
    """Delete a clothing item and its material composition"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete material composition first (foreign key constraint)
        cursor.execute("DELETE FROM clothing_material_composition WHERE qr_code = ?", (qr_code,))
        
        # Delete clothing item
        cursor.execute("DELETE FROM clothing_items WHERE qr_code = ?", (qr_code,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500

# Enhanced database route to serve the new page
@app.route('/database')
def database_management():
    """Enhanced database management page"""
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    
    return render_template('database_management.html', username=username)

# Additional utility endpoints for database stats
@app.route('/api/stats/overview')
def get_database_overview():
    """Get overview statistics for the database"""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get counts
        cursor.execute('SELECT COUNT(*) as count FROM clothing_items')
        items_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM materials')
        materials_count = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM environmental_impacts')
        impacts_count = cursor.fetchone()['count']
        
        # Get unique brands
        cursor.execute('SELECT COUNT(DISTINCT brand) as count FROM clothing_items WHERE brand IS NOT NULL')
        brands_count = cursor.fetchone()['count']
        
        # Get unique categories
        cursor.execute('SELECT COUNT(DISTINCT category) as count FROM clothing_items WHERE category IS NOT NULL')
        categories_count = cursor.fetchone()['count']
        
        # Get unique impact categories
        cursor.execute('SELECT COUNT(DISTINCT impact_category) as count FROM environmental_impacts')
        impact_categories_count = cursor.fetchone()['count']
        
        # Get average weight
        cursor.execute('SELECT AVG(weight_grams) as avg_weight FROM clothing_items')
        avg_weight = cursor.fetchone()['avg_weight'] or 0
        
        conn.close()
        
        return jsonify({
            'items_count': items_count,
            'materials_count': materials_count,
            'impacts_count': impacts_count,
            'brands_count': brands_count,
            'categories_count': categories_count,
            'impact_categories_count': impact_categories_count,
            'avg_weight': round(avg_weight, 1) if avg_weight else 0
        })
        
    except Exception as e:
        return jsonify({'error': True, 'message': str(e)}), 500



@app.route('/api/cart')
def get_cart():
    """Get current cart items for display"""
    cart_items = session.get('cart_items', [])
    return jsonify({
        'success': True,
        'items': cart_items
    })

# Error handling middleware
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': True, 'message': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': True, 'message': 'Internal server error'}), 500
    return render_template('500.html'), 500



if __name__ == '__main__':
    app.run(debug=True)