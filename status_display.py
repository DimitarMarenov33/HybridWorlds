# status_display.py

from flask import Blueprint, render_template

status_bp = Blueprint('status', __name__, template_folder='templates')

@status_bp.route('/status')
def show_status():
    try:
        with open('status_value.txt', 'r') as f:
            current_value = int(f.read().strip())
    except:
        current_value = 1

    current_value = max(1, min(current_value, 5))
    return render_template('status.html', current_value=current_value)
