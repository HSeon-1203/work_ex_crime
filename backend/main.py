from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime
import json

# 각 기능별 모듈 import
from emergency_bells.routes import emergency_bells_bp
from community.routes import community_bp
from hotzone.routes import hotzone_bp

app = Flask(__name__)
CORS(app)  # 프론트엔드와 통신 허용

# 환경 변수 설정
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['DATABASE'] = os.environ.get('DATABASE', 'safety_app.db')

# 블루프린트 등록
app.register_blueprint(emergency_bells_bp, url_prefix='/api/emergency-bells')
app.register_blueprint(community_bp, url_prefix='/api/community')
app.register_blueprint(hotzone_bp, url_prefix='/api/hotzone')

@app.route('/')
def home():
    """API 홈페이지"""
    return jsonify({
        'message': '서울시 안전 앱 API 서버',
        'version': '1.0.0',
        'endpoints': {
            'emergency_bells': '/api/emergency-bells',
            'community': '/api/community',
            'hotzone': '/api/hotzone'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/health')
def health_check():
    """서버 상태 확인"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # 5000 → 5001로 변경
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"🚀 서버 시작: http://localhost:{port}")
    print(f"🔧 디버그 모드: {debug}")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
