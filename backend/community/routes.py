from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime
import sqlite3

community_bp = Blueprint('community', __name__)

# 데이터베이스 파일 경로
DB_FILE = os.path.join(os.path.dirname(__file__), '../../database/community.db')

def init_database():
    """커뮤니티 데이터베이스 초기화"""
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # 커뮤니티 게시물 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                author TEXT NOT NULL,
                location TEXT,
                latitude REAL,
                longitude REAL,
                category TEXT DEFAULT '일반',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 댓글 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ 커뮤니티 데이터베이스 초기화 완료")
        
    except Exception as e:
        print(f"❌ 데이터베이스 초기화 실패: {e}")

def get_db_connection():
    """데이터베이스 연결"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

@community_bp.route('/', methods=['GET'])
def get_posts():
    """게시물 목록 조회"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        category = request.args.get('category', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 카테고리별 필터링
        if category != 'all':
            cursor.execute('''
                SELECT * FROM posts 
                WHERE category = ? 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (category, per_page, (page - 1) * per_page))
        else:
            cursor.execute('''
                SELECT * FROM posts 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (per_page, (page - 1) * per_page))
        
        posts = cursor.fetchall()
        
        # 전체 게시물 수 조회
        if category != 'all':
            cursor.execute('SELECT COUNT(*) FROM posts WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT COUNT(*) FROM posts')
        
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        # 딕셔너리로 변환
        posts_list = []
        for post in posts:
            posts_list.append({
                'id': post['id'],
                'title': post['title'],
                'content': post['content'][:100] + '...' if len(post['content']) > 100 else post['content'],
                'author': post['author'],
                'location': post['location'],
                'latitude': post['latitude'],
                'longitude': post['longitude'],
                'category': post['category'],
                'created_at': post['created_at']
            })
        
        return jsonify({
            'success': True,
            'data': posts_list,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@community_bp.route('/', methods=['POST'])
def create_post():
    """새 게시물 작성"""
    try:
        data = request.get_json()
        
        if not data or not data.get('title') or not data.get('content') or not data.get('author'):
            return jsonify({
                'success': False,
                'error': '제목, 내용, 작성자가 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO posts (title, content, author, location, latitude, longitude, category)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['title'],
            data['content'],
            data['author'],
            data.get('location'),
            data.get('latitude'),
            data.get('longitude'),
            data.get('category', '일반')
        ))
        
        post_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '게시물이 작성되었습니다.',
            'post_id': post_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@community_bp.route('/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """특정 게시물 조회"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 게시물 조회
        cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
        post = cursor.fetchone()
        
        if not post:
            conn.close()
            return jsonify({
                'success': False,
                'error': '게시물을 찾을 수 없습니다.'
            }), 404
        
        # 댓글 조회
        cursor.execute('SELECT * FROM comments WHERE post_id = ? ORDER BY created_at ASC', (post_id,))
        comments = cursor.fetchall()
        
        conn.close()
        
        # 댓글 딕셔너리로 변환
        comments_list = []
        for comment in comments:
            comments_list.append({
                'id': comment['id'],
                'content': comment['content'],
                'author': comment['author'],
                'created_at': comment['created_at']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'id': post['id'],
                'title': post['title'],
                'content': post['content'],
                'author': post['author'],
                'location': post['location'],
                'latitude': post['latitude'],
                'longitude': post['longitude'],
                'category': post['category'],
                'created_at': post['created_at'],
                'updated_at': post['updated_at'],
                'comments': comments_list
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@community_bp.route('/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    """댓글 추가"""
    try:
        data = request.get_json()
        
        if not data or not data.get('content') or not data.get('author'):
            return jsonify({
                'success': False,
                'error': '댓글 내용과 작성자가 필요합니다.'
            }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 게시물 존재 확인
        cursor.execute('SELECT id FROM posts WHERE id = ?', (post_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'success': False,
                'error': '게시물을 찾을 수 없습니다.'
            }), 404
        
        # 댓글 추가
        cursor.execute('''
            INSERT INTO comments (post_id, content, author)
            VALUES (?, ?, ?)
        ''', (post_id, data['content'], data['author']))
        
        comment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '댓글이 추가되었습니다.',
            'comment_id': comment_id
        }), 201
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# 데이터베이스 초기화
init_database()
