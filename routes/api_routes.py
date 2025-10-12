from flask import Blueprint, request, jsonify
from utils.auth import admin_required
from models.data_handler import load_mapping, save_mapping
import requests
from bs4 import BeautifulSoup

bp = Blueprint('api_routes', __name__)

@bp.route('/api/scrape-hotpepper', methods=['POST'])
@admin_required
def scrape_hotpepper():
    url = request.json.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URLが指定されていません'}), 400
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        mapping = load_mapping()
        count = 0
        staff_elements = soup.select('.staff-item')
        for element in staff_elements:
            name = element.select_one('.staff-name')
            line_id = element.select_one('.line-id')
            if name and line_id:
                mapping[name.text.strip()] = line_id.text.strip()
                count += 1
        save_mapping(mapping)
        return jsonify({'success': True, 'count': count, 'message': f'{count}件の顧客データを取得しました'})
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'error': 'タイムアウトしました'}), 408
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
