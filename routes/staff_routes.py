from flask import Blueprint, render_template, request, redirect, url_for, session
from utils.auth import login_required
from utils.line_sender import send_line_message
from models.data_handler import load_mapping, save_absence, load_messages
from datetime import datetime

bp = Blueprint('staff_routes', __name__)

@bp.route('/staff/absence', methods=['GET', 'POST'])
@login_required
def staff_absence():
    user = session.get('user')
    if request.method == 'POST':
        staff_name = user['staff_id']
        reason = request.form.get('reason')
        details = request.form.get('details', '')
        alternative_date = request.form.get('alternative_date', '')
        absence_data = {"staff_name": staff_name, "reason": reason, "details": details, "alternative_date": alternative_date, "submitted_at": datetime.now().isoformat()}
        save_absence(absence_data)
        mapping = load_mapping()
        messages = load_messages()
        absence_message = messages['absence_confirmed'].format(reason=reason, details=details)
        for customer_name, line_id in mapping.items():
            if customer_name == staff_name:
                send_line_message(line_id, absence_message)
                break
        request_message = messages['absence_request'].format(staff_name=user['full_name'])
        for customer_name, line_id in mapping.items():
            if customer_name != staff_name:
                send_line_message(line_id, request_message)
        return render_template('staff_absence.html', success=True, staff_name=user['full_name'])
    return render_template('staff_absence.html', staff_name=user['full_name'])
