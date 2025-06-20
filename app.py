# app.py - Add this file to your existing project
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, make_response, flash
import sqlite3
import os
from datetime import datetime

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
        return redirect(url_for('slider'))
    return redirect(url_for('username_page'))

@app.route('/index')
def index():
    username = session.get('username')
    if not username:
        return redirect(url_for('slider'))
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
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
    
    # Get item details from the form
    item_name = request.form.get('item_name')
    qr_code = request.form.get('qr_code')
    environmental_impact = request.form.get('environmental_impact')
    
    # Initialize cart in session if it doesn't exist
    if 'cart_items' not in session:
        session['cart_items'] = []
    
    # Check if cart already has 3 items
    if len(session['cart_items']) >= 3:
        return jsonify({'success': False, 'message': 'Maximum 3 items allowed in cart'})
    
    # Add item to cart
    cart_item = {
        'name': item_name,
        'qr_code': qr_code,
        'impact': environmental_impact,
        'price': '0.00',  # Placeholder
        'quantity': 1
    }
    
    session['cart_items'].append(cart_item)
    session.modified = True
    
    return jsonify({'success': True, 'message': 'Item added to cart'})

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
    """Save the current cart details and shift the previous one."""
    # If a 'current' choice exists in the session, move it to become the 'previous' choice.
    if 'current_choice_for_receipt' in session:
        session['prev_choice_for_receipt'] = session['current_choice_for_receipt']
    
    # Save the new data, which was just sent from the cart, as the new 'current' choice.
    data = request.get_json()
    session['current_choice_for_receipt'] = data
    session.modified = True
    return jsonify({'success': True})

@app.route('/receipt')
def receipt():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))
        
    current_choice = session.get('current_choice_for_receipt', {})
    prev_choice = session.get('prev_choice_for_receipt', {})
    
    # Get the current date and time to display on the receipt
    date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        
    return render_template(
        'receipt.html', 
        current_choice=current_choice, 
        prev_choice=prev_choice,
        username=username, 
        date=date_str,
        hide_nav=True
    )

@app.route('/slider')
def slider():
    username = session.get('username')
    if not username:
        # If no user, send them to login first
        return redirect(url_for('username_page'))
    # hide_nav is used in base.html to conditionally hide the navigation bar
    return render_template('slider.html', username=username, hide_nav=True)

@app.route('/care', methods=['GET', 'POST'])
def care():
    username = session.get('username')
    if not username:
        return redirect(url_for('username_page'))

    if request.method == 'POST':
        wear_frequency = request.form.get('wear_frequency')
        wash_frequency = request.form.get('wash_frequency')
        
        # Save to database
        try:
            conn = sqlite3.connect('fashion_env.db')
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_care_habits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    wear_frequency INTEGER,
                    wash_frequency TEXT,
                    initial_score INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Get the initial score from session
            initial_score = session.get('initial_score', 0)
            
            # Insert or update the user's care habits
            cursor.execute('''
                INSERT OR REPLACE INTO user_care_habits 
                (username, wear_frequency, wash_frequency, initial_score) 
                VALUES (?, ?, ?, ?)
            ''', (username, wear_frequency, wash_frequency, initial_score))
            
            conn.commit()
            conn.close()
            
            flash('Your care habits have been saved successfully!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Error saving care habits: {e}")
            flash('Error saving your habits. Please try again.', 'error')
            return redirect(url_for('care'))

    return render_template('care.html', hide_nav=True, username=username)

@app.route('/save_score', methods=['POST'])
def save_score():
    data = request.get_json()
    score = data.get('score')
    username = session.get('username')

    if score is None or username is None:
        return jsonify({'status': 'error', 'message': 'Missing score or user information.'}), 400

    session['initial_score'] = score
    
    print(f"Received score from {username}: {score}%. Stored in session.")

    return jsonify({'status': 'success', 'message': f'Initial score of {score} saved for user {username}.'})

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

if __name__ == '__main__':
    app.run(debug=True)