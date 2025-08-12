from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime
import sqlite3

hotzone_bp = Blueprint('hotzone', __name__)

# 데이터베이스 파일 경로
DB_FILE = os.path.join(os.path.dirname(__file__), '../../database/hotzone.db')

def init_database():
    """핫존 데이터베이스 초기화"""
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 핫존 영역 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hotzones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_name TEXT NOT NULL,
                description TEXT,
                risk_level INTEGER NOT NULL CHECK (risk_level >= 1 AND risk_level <= 5),
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                radius REAL DEFAULT 0.5,
                crime_type TEXT,
                last_incident_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 범죄 사건 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hotzone_id INTEGER,
                incident_type TEXT NOT NULL,
                description TEXT,
                incident_date DATE NOT NULL,
                latitude REAL,
                longitude REAL,
                severity INTEGER CHECK (severity >= 1 AND severity >= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hotzone_id) REFERENCES hotzones (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ 핫존 데이터베이스 초기화 완료")
        
        # 샘플 데이터 추가
        add_sample_data()
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")

def add_sample_data():
    """샘플 핫존 데이터 추가"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 기존 데이터 확인
        cursor.execute('SELECT COUNT(*) FROM hotzones')
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # 서울시 주요 지역 샘플 데이터
        sample_hotzones = [
            ('강남역 주변', '강남역 인근 번화가', 4, 37.4979, 127.0276, 0.8, '절도, 폭력'),
            ('홍대입구역 주변', '홍대입구역 인근 상권', 3, 37.5571, 126.9236, 0.6, '절도, 성범죄'),
            ('동대문역사문화공원역', '동대문 상권', 3, 37.5658, 127.0090, 0.7, '절도, 폭력'),
            ('신촌역 주변', '신촌 대학가', 2, 37.5552, 126.9368, 0.5, '절도'),
            ('건대입구역 주변', '건대입구역 인근', 2, 37.5407, 127.0892, 0.6, '절도, 폭력')
        ]
        
        cursor.executemany('''
            INSERT INTO hotzones (area_name, description, risk_level, latitude, longitude, radius, crime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', sample_hotzones)
        
        conn.commit()
        conn.close()
        
        print("✅ 샘플 핫존 데이터 추가 완료")
        
    except Exception as e:
        print(f"❌ 샘플 데이터 추가 실패: {e}")

def get_db_connection():
    """데이터베이스 연결"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@hotzone_bp.route('/', methods=['GET'])
def get_hotzones():
    """모든 핫존 영역 조회"""
    try:
        risk_level = request.args.get('risk_level', type=int)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if risk_level:
            cursor.execute('SELECT * FROM hotzones WHERE risk_level = ? ORDER BY risk_level DESC', (risk_level,))
        else:
            cursor.execute('SELECT * FROM hotzones ORDER BY risk_level DESC')
        
        hotzones = cursor.fetchall()
        conn.close()
        
        # 딕셔너리로 변환
        hotzones_list = []
        for zone in hotzones:
            hotzones_list.append({
                'id': zone['id'],
                'area_name': zone['area_name'],
                'description': zone['description'],
                'risk_level': zone['risk_level'],
                'latitude': zone['latitude'],
                'longitude': zone['longitude'],
                'radius': zone['radius'],
                'crime_type': zone['crime_type'],
                'last_incident_date': zone['last_incident_date'],
                'created_at': zone['created_at']
            })
        
        return jsonify({
            'success': True,
            'count': len(hotzones_list),
            'data': hotzones_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hotzone_bp.route('/nearby', methods=['GET'])
def get_nearby_hotzones():
    """특정 위치 근처의 핫존 조회"""
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 5.0, type=float)  # 기본 5km
        
        if not lat or not lng:
            return jsonify({
                'success': False,
                'error': '위도(lat)와 경도(lng)가 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM hotzones')
        all_hotzones = cursor.fetchall()
        conn.close()
        
        nearby_hotzones = []
        
        for zone in all_hotzones:
            try:
                zone_lat = float(zone['latitude'])
                zone_lng = float(zone['longitude'])
                
                # 거리 계산 (간단한 유클리드 거리)
                distance = ((lat - zone_lat) ** 2 + (lng - zone_lng) ** 2) ** 0.5
                
                if distance <= radius / 111:  # 대략적인 km 변환
                    zone_dict = {
                        'id': zone['id'],
                        'area_name': zone['area_name'],
                        'description': zone['description'],
                        'risk_level': zone['risk_level'],
                        'latitude': zone_lat,
                        'longitude': zone_lng,
                        'radius': zone['radius'],
                        'crime_type': zone['crime_type'],
                        'distance_km': round(distance * 111, 2)
                    }
                    nearby_hotzones.append(zone_dict)
                    
            except (ValueError, TypeError):
                continue
        
        # 위험도 순으로 정렬
        nearby_hotzones.sort(key=lambda x: x['risk_level'], reverse=True)
        
        return jsonify({
            'success': True,
            'count': len(nearby_hotzones),
            'search_radius_km': radius,
            'center': {'lat': lat, 'lng': lng},
            'data': nearby_hotzones
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hotzone_bp.route('/', methods=['POST'])
def create_hotzone():
    """새 핫존 영역 추가"""
    try:
        data = request.get_json()
        
        if not data or not data.get('area_name') or not data.get('risk_level'):
            return jsonify({
                'success': False,
                'error': '지역명과 위험도가 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO hotzones (area_name, description, risk_level, latitude, longitude, radius, crime_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['area_name'],
            data.get('description'),
            data['risk_level'],
            data.get('latitude'),
            data.get('longitude'),
            data.get('radius', 0.5),
            data.get('crime_type')
        ))
        
        hotzone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '핫존 영역이 추가되었습니다.',
            'hotzone_id': hotzone_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hotzone_bp.route('/<int:hotzone_id>', methods=['GET'])
def get_hotzone(hotzone_id):
    """특정 핫존 영역 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 핫존 정보 조회
        cursor.execute('SELECT * FROM hotzones WHERE id = ?', (hotzone_id,))
        hotzone = cursor.fetchone()
        
        if not hotzone:
            conn.close()
            return jsonify({
                'success': False,
                'error': '핫존 영역을 찾을 수 없습니다.'
            }), 404
        
        # 관련 사건 조회
        cursor.execute('SELECT * FROM incidents WHERE hotzone_id = ? ORDER BY incident_date DESC', (hotzone_id,))
        incidents = cursor.fetchall()
        
        conn.close()
        
        # 사건 딕셔너리로 변환
        incidents_list = []
        for incident in incidents:
            incidents_list.append({
                'id': incident['id'],
                'incident_type': incident['incident_type'],
                'description': incident['description'],
                'incident_date': incident['incident_date'],
                'latitude': incident['latitude'],
                'longitude': incident['longitude'],
                'severity': incident['severity']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'id': hotzone['id'],
                'area_name': hotzone['area_name'],
                'description': hotzone['description'],
                'risk_level': hotzone['risk_level'],
                'latitude': hotzone['latitude'],
                'longitude': hotzone['longitude'],
                'radius': hotzone['radius'],
                'crime_type': hotzone['crime_type'],
                'last_incident_date': hotzone['last_incident_date'],
                'created_at': hotzone['created_at'],
                'incidents': incidents_list
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hotzone_bp.route('/stats', methods=['GET'])
def get_hotzone_stats():
    """핫존 통계 정보"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 위험도별 통계
        cursor.execute('SELECT risk_level, COUNT(*) FROM hotzones GROUP BY risk_level ORDER BY risk_level DESC')
        risk_stats = dict(cursor.fetchall())
        
        # 전체 핫존 수
        cursor.execute('SELECT COUNT(*) FROM hotzones')
        total_hotzones = cursor.fetchone()[0]
        
        # 전체 사건 수
        cursor.execute('SELECT COUNT(*) FROM incidents')
        total_incidents = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_hotzones': total_hotzones,
            'total_incidents': total_incidents,
            'risk_level_stats': risk_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 데이터베이스 초기화
init_database()
