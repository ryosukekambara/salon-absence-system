from flask import Blueprint, render_template, request, redirect, url_for, make_response
from utils.auth import admin_required
from models.data_handler import load_messages, save_messages, load_mapping, load_absences
from datetime import datetime
import csv
from io import StringIO
from collections import defaultdict

bp = Blueprint('admin_routes', __name__)

@bp.route('/admin')
@admin_required
def admin():
    messages = load_messages()
    mapping = load_mapping()
    customer_count = len(mapping)
    absences = load_absences()
    total_absences = len(absences)
    current_month = datetime.now().strftime("%Y-%m")
    monthly_absences = sum(1 for a in absences if a.get("submitted_at", "").startswith(current_month))
    success = request.args.get('success')
    return render_template('admin.html', messages=messages, success=success, customer_count=customer_count, monthly_absences=monthly_absences, total_absences=total_absences)

@bp.route('/update', methods=['POST'])
@admin_required
def update():
    messages = {'absence_request': request.form.get('absence_request'), 'substitute_confirmed': request.form.get('substitute_confirmed'), 'absence_confirmed': request.form.get('absence_confirmed')}
    save_messages(messages)
    return redirect(url_for('admin_routes.admin', success='true'))

@bp.route('/customers')
@admin_required
def customer_list():
    mapping = load_mapping()
    return render_template('customers.html', mapping=mapping)

@bp.route('/absences')
@admin_required
def absence_list():
    absences = load_absences()
    def get_full_name(staff_id):
        from utils.auth import load_staff
        staff_data = load_staff()
        return staff_data.get(staff_id, {}).get('full_name', staff_id)
    grouped_absences = defaultdict(list)
    for absence in absences:
        month_key = absence['submitted_at'][:7]
        grouped_absences[month_key].append(absence)
    return render_template('absences.html', grouped_absences=dict(sorted(grouped_absences.items(), reverse=True)), get_full_name=get_full_name)

@bp.route('/export/absences')
@admin_required
def export_absences():
    absences = load_absences()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['スタッフ名', '欠勤理由', '状況説明', '代替可能日時', '申請日時'])
    for absence in absences:
        writer.writerow([absence.get('staff_name', ''), absence.get('reason', ''), absence.get('details', ''), absence.get('alternative_date', ''), absence.get('submitted_at', '')[:19].replace('T', ' ')])
    output = si.getvalue()
    si.close()
    response = make_response(output)
    response.headers['Content-Type'] = 'text/csv; charset=utf-8-sig'
    response.headers['Content-Disposition'] = f'attachment; filename=absences_{datetime.now().strftime("%Y%m%d")}.csv'
    return response

@bp.route('/scrape')
@admin_required
def scrape_page():
    return render_template('scrape.html')
