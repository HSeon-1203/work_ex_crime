from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime

emergency_bells_bp = Blueprint('emergency_bells', __name__)

# 데이터 파일 경로
DATA_FILE = os.path.join(os.path.dirname(__file__), '../../emergency_bells.json')

def load_emergency_bells():
    """안전벨 데이터 로드"""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"데이터 로드 에러: {e}")
        return []

@emergency_bells_bp.route('/', methods=['GET'])
def get_all_emergency_bells():
    """모든 안전벨 조회"""
    try:
        bells = load_emergency_bells()
        return jsonify({
            'success': True,
            'count': len(bells),
            'data': bells
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@emergency_bells_bp.route('/nearby', methods=['GET'])
def get_nearby_emergency_bells():
    """특정 위치 근처의 안전벨 조회"""
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', 2.0, type=float)  # 기본 2km
        
        if not lat or not lng:
            return jsonify({
                'success': False,
                'error': '위도(lat)와 경도(lng)가 필요합니다.'
            }), 400
        
        bells = load_emergency_bells()
        nearby_bells = []
        
        for bell in bells:
            try:
                bell_lat = float(bell.get('WGS84위도', 0))
                bell_lng = float(bell.get('WGS84경도', 0))
                
                if bell_lat == 0 or bell_lng == 0:
                    continue
                
                # 거리 계산 (간단한 유클리드 거리)
                distance = ((lat - bell_lat) ** 2 + (lng - bell_lng) ** 2) ** 0.5
                
                if distance <= radius / 111:  # 대략적인 km 변환
                    bell['distance'] = round(distance * 111, 2)
                    nearby_bells.append(bell)
                    
            except (ValueError, TypeError):
                continue
        
        # 거리순 정렬
        nearby_bells.sort(key=lambda x: x.get('distance', float('inf')))
        
        return jsonify({
            'success': True,
            'count': len(nearby_bells),
            'radius_km': radius,
            'center': {'lat': lat, 'lng': lng},
            'data': nearby_bells
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@emergency_bells_bp.route('/filter', methods=['GET'])
def get_filtered_emergency_bells():
    """설치목적별 안전벨 필터링"""
    try:
        purpose = request.args.get('purpose', 'all')
        bells = load_emergency_bells()
        
        if purpose != 'all':
            filtered_bells = [bell for bell in bells if bell.get('설치목적') == purpose]
        else:
            filtered_bells = bells
        
        return jsonify({
            'success': True,
            'count': len(filtered_bells),
            'filter': purpose,
            'data': filtered_bells
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@emergency_bells_bp.route('/stats', methods=['GET'])
def get_emergency_bells_stats():
    """안전벨 통계 정보"""
    try:
        bells = load_emergency_bells()
        
        # 구별 통계
        district_stats = {}
        purpose_stats = {}
        location_stats = {}
        
        for bell in bells:
            # 구별 통계
            district = bell.get('관리기관명', '기타')
            district_stats[district] = district_stats.get(district, 0) + 1
            
            # 설치목적별 통계
            purpose = bell.get('설치목적', '기타')
            purpose_stats[purpose] = purpose_stats.get(purpose, 0) + 1
            
            # 설치장소별 통계
            location = bell.get('설치장소유형', '기타')
            location_stats[location] = location_stats.get(location, 0) + 1
        
        return jsonify({
            'success': True,
            'total_count': len(bells),
            'district_stats': district_stats,
            'purpose_stats': purpose_stats,
            'location_stats': location_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
