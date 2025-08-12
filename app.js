// 전역 변수
let map;
let markers = [];
let emergencyBells = [];
let currentPosition = null;
let nearestBell = null;
let currentFilter = 'all';
let currentRadius = 2.0; // 기본 2km
let radiusCircle = null; // 반경 원 객체
let currentInfoWindow = null; // 현재 열린 정보창

// 카카오맵 초기화
function initMap() {
    const container = document.getElementById('map');
    const options = {
        center: new kakao.maps.LatLng(37.5665, 126.9780), // 서울시청
        level: 8
    };
    
    map = new kakao.maps.Map(container, options);
    
    // 지도 클릭 이벤트
    kakao.maps.event.addListener(map, 'click', function(mouseEvent) {
        const latlng = mouseEvent.latLng;
        updateCurrentLocation(latlng.getLat(), latlng.getLng());
    });
    
    // 지도 이동 완료 이벤트
    kakao.maps.event.addListener(map, 'dragend', function() {
        displayAllBells();
    });
    
    // 지도 줌 변경 이벤트
    kakao.maps.event.addListener(map, 'zoom_changed', function() {
        displayAllBells();
    });
    
    // 사용자 위치 가져오기
    getUserLocation();
}

// 사용자 위치 가져오기
function getUserLocation() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const lat = position.coords.latitude;
                const lng = position.coords.longitude;
                currentPosition = { lat, lng };
                
                // 지도 중심을 사용자 위치로 이동
                map.setCenter(new kakao.maps.LatLng(lat, lng));
                map.setLevel(6);
                
                // 사용자 위치 마커 추가
                addUserMarker(lat, lng);
                
                // 반경 원 그리기
                drawRadiusCircle(new kakao.maps.LatLng(lat, lng), currentRadius);
                
                // 가장 가까운 비상벨 찾기
                findNearestBell(lat, lng);
            },
            function(error) {
                console.log('위치 정보를 가져올 수 없습니다:', error);
                // 기본 위치(서울시청)에서 가장 가까운 비상벨 찾기
                findNearestBell(37.5665, 126.9780);
            }
        );
    } else {
        console.log('이 브라우저에서는 위치 정보를 지원하지 않습니다.');
    }
}

// 현재 위치 업데이트 함수
function updateCurrentLocation(lat, lng) {
    currentPosition = { lat, lng };
    
    // 기존 사용자 마커 제거
    if (window.userMarker) {
        window.userMarker.setMap(null);
    }
    
    // 새로운 사용자 위치 마커 추가
    addUserMarker(lat, lng);
    
    // 반경 원 그리기
    drawRadiusCircle(new kakao.maps.LatLng(lat, lng), currentRadius);
    
    // 가장 가까운 비상벨 찾기
    findNearestBell(lat, lng);
}

// 사용자 위치 마커 추가
function addUserMarker(lat, lng) {
    // 사용자 마커 스타일 설정
    const userCanvas = document.createElement('canvas');
    userCanvas.width = 30;
    userCanvas.height = 30;
    const userCtx = userCanvas.getContext('2d');
    
    // 파란색 원 그리기
    userCtx.beginPath();
    userCtx.arc(15, 15, 12, 0, 2 * Math.PI);
    userCtx.fillStyle = '#007bff';
    userCtx.fill();
    userCtx.strokeStyle = '#fff';
    userCtx.lineWidth = 2;
    userCtx.stroke();
    
    // 중앙에 흰색 점
    userCtx.beginPath();
    userCtx.arc(15, 15, 4, 0, 2 * Math.PI);
    userCtx.fillStyle = '#fff';
    userCtx.fill();
    
    const userImage = new kakao.maps.MarkerImage(
        userCanvas.toDataURL(),
        new kakao.maps.Size(30, 30)
    );
    
    const userMarker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(lat, lng),
        map: map,
        image: userImage
    });
    
    // 사용자 마커를 전역 변수로 저장
    window.userMarker = userMarker;
    
    // 사용자 위치 정보창
    const infowindow = new kakao.maps.InfoWindow({
        content: '<div style="padding:5px;font-size:12px;">📍 현재 위치</div>'
    });
    
    kakao.maps.event.addListener(userMarker, 'click', function() {
        infowindow.open(map, userMarker);
    });
}

// 비상벨 데이터 로드
async function loadEmergencyBells() {
    try {
        console.log('비상벨 데이터 로드 시작...');
        const response = await fetch('emergency_bells.json');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        emergencyBells = await response.json();
        
        console.log(`총 ${emergencyBells.length}개의 비상벨 데이터 로드 완료`);
        console.log('첫 번째 데이터 샘플:', emergencyBells[0]);
        
        // 위치 정보가 있는 데이터만 필터링
        const validBells = emergencyBells.filter(bell => {
            const lat = parseFloat(bell.WGS84위도);
            const lng = parseFloat(bell.WGS84경도);
            return !isNaN(lat) && !isNaN(lng) && lat !== null && lng !== null;
        });
        
        console.log(`위치 정보가 있는 비상벨: ${validBells.length}개`);
        
        // 통계 업데이트
        updateStats();
        
        // 모든 비상벨 표시
        displayAllBells();
        
        // 로딩 화면 숨기기
        document.getElementById('loadingSection').style.display = 'none';
        
    } catch (error) {
        console.error('비상벨 데이터 로드 실패:', error);
        document.getElementById('loadingSection').innerHTML = 
            '<p style="color: red;">데이터 로드에 실패했습니다: ' + error.message + '</p>';
    }
}

// 모든 비상벨 표시 (반경 제한)
function displayAllBells() {
    clearMarkers();
    
    // 현재 지도 중심 좌표
    const center = map.getCenter();
    const centerLat = center.getLat();
    const centerLng = center.getLng();
    
    // 반경 원 그리기
    drawRadiusCircle(center, currentRadius);
    
    let visibleCount = 0;
    
    emergencyBells.forEach((bell, index) => {
        if (currentFilter === 'all' || bell.설치목적 === currentFilter) {
            // NaN 값 처리
            const bellLat = bell.WGS84위도 === null || bell.WGS84위도 === undefined || bell.WGS84위도 === '' ? null : parseFloat(bell.WGS84위도);
            const bellLng = bell.WGS84경도 === null || bell.WGS84경도 === undefined || bell.WGS84경도 === '' ? null : parseFloat(bell.WGS84경도);
            
            if (isNaN(bellLat) || isNaN(bellLng) || bellLat === null || bellLng === null) return;
            
            // 현재 설정된 반경 내에 있는지 확인
            const distance = calculateDistance(centerLat, centerLng, bellLat, bellLng);
            if (distance <= currentRadius) {
                addBellMarker(bell, index);
                visibleCount++;
            }
        }
    });
    
    updateCurrentCount();
    
    // 반경 정보 업데이트
    updateRadiusInfo(visibleCount);
}

// 비상벨 마커 추가
function addBellMarker(bell, index) {
    // NaN 값 처리
    const lat = bell.WGS84위도 === null || bell.WGS84위도 === undefined || bell.WGS84위도 === '' ? null : parseFloat(bell.WGS84위도);
    const lng = bell.WGS84경도 === null || bell.WGS84경도 === undefined || bell.WGS84경도 === '' ? null : parseFloat(bell.WGS84경도);
    
    if (isNaN(lat) || isNaN(lng) || lat === null || lng === null) {
        console.log('위치 정보가 없는 비상벨:', bell.설치위치);
        return;
    }
    
    // 마커 이미지 설정
    const markerImage = new kakao.maps.MarkerImage(
        getBellIcon(bell.설치목적),
        new kakao.maps.Size(30, 30)
    );
    
    const marker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(lat, lng),
        map: map,
        image: markerImage
    });
    
    markers.push(marker);
    
    // 정보창 내용 - NaN 값 처리
    const content = `
        <div style="padding:10px;min-width:200px;position:relative;">
            <button onclick="closeInfoWindow()" style="position:absolute;top:5px;right:5px;background:none;border:none;color:#999;font-size:16px;cursor:pointer;padding:0;width:20px;height:20px;line-height:1;">×</button>
            <h4 style="margin:0 0 5px 0;color:#333;padding-right:20px;">🚨 ${bell.설치위치 || '위치정보없음'}</h4>
            <p style="margin:5px 0;font-size:12px;">
                <strong>설치목적:</strong> ${bell.설치목적 || '정보없음'}<br>
                <strong>설치장소:</strong> ${bell.설치장소유형 || '정보없음'}<br>
                <strong>주소:</strong> ${bell.소재지도로명주소 || bell.소재지지번주소 || '정보없음'}<br>
                <strong>관리기관:</strong> ${bell.관리기관명 || '정보없음'}<br>
                <strong>연락처:</strong> ${bell.관리기관전화번호 || '정보없음'}
            </p>
        </div>
    `;
    
    const infowindow = new kakao.maps.InfoWindow({
        content: content
    });
    
    // 마커 클릭 이벤트
    kakao.maps.event.addListener(marker, 'click', function() {
        // 기존 정보창 닫기
        if (currentInfoWindow) {
            currentInfoWindow.close();
        }
        
        // 새 정보창 열기
        infowindow.open(map, marker);
        currentInfoWindow = infowindow;
    });
}

// 비상벨 타입별 아이콘 반환
function getBellIcon(type) {
    let fillColor;
    
    switch(type) {
        case '방범용':
            fillColor = '#ff4757'; // 빨간색
            break;
        case '약자보호':
            fillColor = '#2ed573'; // 초록색
            break;
        default:
            fillColor = '#ffa502'; // 주황색
            break;
    }
    
    // 간단한 원형 마커 생성
    const canvas = document.createElement('canvas');
    canvas.width = 30;
    canvas.height = 30;
    const ctx = canvas.getContext('2d');
    
    // 원 그리기
    ctx.beginPath();
    ctx.arc(15, 15, 12, 0, 2 * Math.PI);
    ctx.fillStyle = fillColor;
    ctx.fill();
    ctx.strokeStyle = '#fff';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    return canvas.toDataURL();
}

// 마커들 제거
function clearMarkers() {
    markers.forEach(marker => marker.setMap(null));
    markers = [];
}

// 가장 가까운 비상벨 찾기
function findNearestBell(lat, lng) {
    let nearest = null;
    let minDistance = Infinity;
    
    emergencyBells.forEach(bell => {
        // NaN 값 처리
        const bellLat = bell.WGS84위도 === null || bell.WGS84위도 === undefined || bell.WGS84위도 === '' ? null : parseFloat(bell.WGS84위도);
        const bellLng = bell.WGS84경도 === null || bell.WGS84경도 === undefined || bell.WGS84경도 === '' ? null : parseFloat(bell.WGS84경도);
        
        if (isNaN(bellLat) || isNaN(bellLng) || bellLat === null || bellLng === null) return;
        
        const distance = calculateDistance(lat, lng, bellLat, bellLng);
        
        if (distance < minDistance) {
            minDistance = distance;
            nearest = { ...bell, distance };
        }
    });
    
    if (nearest) {
        nearestBell = nearest;
        showNearestBell(nearest);
        updateNearestDistance(minDistance);
        
        // 가장 가까운 비상벨을 지도에 강조 표시
        highlightNearestBell(nearest);
    }
}

// 두 지점 간 거리 계산 (Haversine 공식)
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // 지구 반지름 (km)
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// 가장 가까운 비상벨 정보 표시
function showNearestBell(bell) {
    const section = document.getElementById('nearestBellSection');
    const info = document.getElementById('nearestBellInfo');
    
    const distance = bell.distance < 1 ? 
        `${Math.round(bell.distance * 1000)}m` : 
        `${bell.distance.toFixed(2)}km`;
    
    info.innerHTML = `
        <p><strong>위치:</strong> ${bell.설치위치 || '위치정보없음'}</p>
        <p><strong>거리:</strong> ${distance}</p>
        <p><strong>설치목적:</strong> ${bell.설치목적 || '정보없음'}</p>
        <p><strong>주소:</strong> ${bell.소재지도로명주소 || bell.소재지지번주소 || '정보없음'}</p>
        <p><strong>관리기관:</strong> ${bell.관리기관명 || '정보없음'}</p>
        <p><strong>연락처:</strong> ${bell.관리기관전화번호 || '정보없음'}</p>
    `;
    
    section.style.display = 'block';
}

// 가장 가까운 비상벨 강조 표시
function highlightNearestBell(bell) {
    // NaN 값 처리
    const lat = bell.WGS84위도 === null || bell.WGS84위도 === undefined || bell.WGS84위도 === '' ? null : parseFloat(bell.WGS84위도);
    const lng = bell.WGS84경도 === null || bell.WGS84경도 === undefined || bell.WGS84경도 === '' ? null : parseFloat(bell.WGS84경도);
    
    if (isNaN(lat) || isNaN(lng) || lat === null || lng === null) {
        console.log('강조 표시할 비상벨의 위치 정보가 없습니다:', bell.설치위치);
        return;
    }
    
    // 기존 강조 마커 제거
    const existingHighlight = document.querySelector('.highlight-marker');
    if (existingHighlight) {
        existingHighlight.remove();
    }
    
    // 새로운 강조 마커 추가
    const highlightMarker = new kakao.maps.Marker({
        position: new kakao.maps.LatLng(lat, lng),
        map: map
    });
    
    // 강조 마커 스타일 설정 - 간단한 원형 마커
    const highlightCanvas = document.createElement('canvas');
    highlightCanvas.width = 40;
    highlightCanvas.height = 40;
    const highlightCtx = highlightCanvas.getContext('2d');
    
    // 큰 원 그리기
    highlightCtx.beginPath();
    highlightCtx.arc(20, 20, 18, 0, 2 * Math.PI);
    highlightCtx.fillStyle = '#ff4757';
    highlightCtx.fill();
    highlightCtx.strokeStyle = '#fff';
    highlightCtx.lineWidth = 3;
    highlightCtx.stroke();
    
    // 중앙에 작은 원 그리기
    highlightCtx.beginPath();
    highlightCtx.arc(20, 20, 6, 0, 2 * Math.PI);
    highlightCtx.fillStyle = '#fff';
    highlightCtx.fill();
    
    const highlightImage = new kakao.maps.MarkerImage(
        highlightCanvas.toDataURL(),
        new kakao.maps.Size(40, 40)
    );
    
    highlightMarker.setImage(highlightImage);
    highlightMarker.setZIndex(1000);
    
    // 정보창 표시
    const content = `
        <div style="padding:15px;min-width:250px;background:#fff3cd;border:2px solid #ff4757;position:relative;">
            <button onclick="closeInfoWindow()" style="position:absolute;top:5px;right:5px;background:none;border:none;color:#999;font-size:16px;cursor:pointer;padding:0;width:20px;height:20px;line-height:1;">×</button>
            <h4 style="margin:0 0 10px 0;color:#ff4757;padding-right:20px;">📍 가장 가까운 비상벨</h4>
            <p style="margin:5px 0;font-size:13px;">
                <strong>위치:</strong> ${bell.설치위치 || '위치정보없음'}<br>
                <strong>거리:</strong> ${bell.distance < 1 ? Math.round(bell.distance * 1000) + 'm' : bell.distance.toFixed(2) + 'km'}<br>
                <strong>설치목적:</strong> ${bell.설치목적 || '정보없음'}<br>
                <strong>주소:</strong> ${bell.소재지도로명주소 || bell.소재지지번주소 || '정보없음'}
            </p>
        </div>
    `;
    
    const infowindow = new kakao.maps.InfoWindow({
        content: content
    });
    
    // 기존 정보창 닫기
    if (currentInfoWindow) {
        currentInfoWindow.close();
    }
    
    infowindow.open(map, highlightMarker);
    currentInfoWindow = infowindow;
    
    // 10초 후 정보창 자동 닫기 (더 오래 보이도록)
    setTimeout(() => {
        if (currentInfoWindow === infowindow) {
            infowindow.close();
            currentInfoWindow = null;
        }
    }, 10000);
}

// 통계 업데이트
function updateStats() {
    document.getElementById('totalCount').textContent = emergencyBells.length.toLocaleString();
}

// 현재 표시된 비상벨 수 업데이트
function updateCurrentCount() {
    const count = markers.length;
    document.getElementById('currentCount').textContent = count.toLocaleString();
}

// 가장 가까운 거리 업데이트
function updateNearestDistance(distance) {
    const distanceText = distance < 1 ? 
        `${Math.round(distance * 1000)}m` : 
        `${distance.toFixed(2)}km`;
    document.getElementById('nearestDistance').textContent = distanceText;
}

// 반경 원 그리기
function drawRadiusCircle(center, radius) {
    // 기존 반경 원 제거
    if (radiusCircle) {
        radiusCircle.setMap(null);
    }
    
    // 새로운 반경 원 생성
    radiusCircle = new kakao.maps.Circle({
        center: center,
        radius: radius * 1000, // km를 m로 변환
        strokeWeight: 2,
        strokeColor: '#667eea',
        strokeOpacity: 0.8,
        strokeStyle: 'dashed',
        fillColor: '#667eea',
        fillOpacity: 0.1
    });
    
    radiusCircle.setMap(map);
}

// 반경 정보 업데이트
function updateRadiusInfo(visibleCount) {
    const radiusInfo = document.getElementById('radiusInfo');
    if (radiusInfo) {
        radiusInfo.textContent = `${currentRadius}km 반경 내: ${visibleCount}개`;
    }
}

// 정보창 닫기 함수
function closeInfoWindow() {
    // 현재 열린 정보창 닫기
    if (currentInfoWindow) {
        currentInfoWindow.close();
        currentInfoWindow = null;
    }
}

// 장소 검색 (주소, 역, 학교, 건물명 등)
function searchAddress() {
    const searchBox = document.getElementById('searchBox');
    const keyword = searchBox.value.trim();
    
    if (!keyword) return;
    
    // 장소 검색 서비스 사용
    const places = new kakao.maps.services.Places();
    
    places.keywordSearch(keyword, function(result, status) {
        if (status === kakao.maps.services.Status.OK) {
            const place = result[0];
            const coords = new kakao.maps.LatLng(place.y, place.x);
            
            // 지도 중심 이동
            map.setCenter(coords);
            map.setLevel(4);
            
            // 현재 위치 업데이트
            updateCurrentLocation(coords.getLat(), coords.getLng());
            
            // 검색 결과 마커 추가
            const searchMarker = new kakao.maps.Marker({
                position: coords
            });
            
            // 검색 마커 스타일 설정
            const searchCanvas = document.createElement('canvas');
            searchCanvas.width = 30;
            searchCanvas.height = 30;
            const searchCtx = searchCanvas.getContext('2d');
            
            // 파란색 원 그리기
            searchCtx.beginPath();
            searchCtx.arc(15, 15, 12, 0, 2 * Math.PI);
            searchCtx.fillStyle = '#007bff';
            searchCtx.fill();
            searchCtx.strokeStyle = '#fff';
            searchCtx.lineWidth = 2;
            searchCtx.stroke();
            
            const searchImage = new kakao.maps.MarkerImage(
                searchCanvas.toDataURL(),
                new kakao.maps.Size(30, 30)
            );
            
            searchMarker.setImage(searchImage);
            searchMarker.setMap(map);
            
            // 검색 결과 정보창
            const content = `
                <div style="padding:10px;min-width:200px;position:relative;">
                    <button onclick="closeInfoWindow()" style="position:absolute;top:5px;right:5px;background:none;border:none;color:#999;font-size:16px;cursor:pointer;padding:0;width:20px;height:20px;line-height:1;">×</button>
                    <h4 style="margin:0 0 5px 0;color:#333;padding-right:20px;">📍 ${place.place_name}</h4>
                    <p style="margin:5px 0;font-size:12px;">
                        <strong>주소:</strong> ${place.address_name}<br>
                        <strong>전화번호:</strong> ${place.phone || '정보없음'}
                    </p>
                </div>
            `;
            
            const infowindow = new kakao.maps.InfoWindow({
                content: content
            });
            
            infowindow.open(map, searchMarker);
            
            // 10초 후 마커와 정보창 제거
            setTimeout(() => {
                searchMarker.setMap(null);
                infowindow.close();
            }, 10000);
            
        } else {
            // 장소 검색 실패 시 주소 검색 시도
            const geocoder = new kakao.maps.services.Geocoder();
            
            geocoder.addressSearch(keyword, function(result, status) {
                if (status === kakao.maps.services.Status.OK) {
                    const coords = new kakao.maps.LatLng(result[0].y, result[0].x);
                    
                    // 지도 중심 이동
                    map.setCenter(coords);
                    map.setLevel(4);
                    
                    // 현재 위치 업데이트
                    updateCurrentLocation(coords.getLat(), coords.getLng());
                    
                    // 검색 결과 마커 추가
                    const marker = new kakao.maps.Marker({
                        position: coords
                    });
                    
                    marker.setMap(map);
                    
                    // 5초 후 마커 제거
                    setTimeout(() => {
                        marker.setMap(null);
                    }, 5000);
                } else {
                    alert('검색 결과를 찾을 수 없습니다. 다른 키워드로 시도해보세요.');
                }
            });
        }
    });
}

// 필터 변경
function changeFilter(filterType) {
    currentFilter = filterType;
    
    // 필터 버튼 상태 업데이트
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-type="${filterType}"]`).classList.add('active');
    
    // 비상벨 다시 표시
    displayAllBells();
}

// 반경 변경
function changeRadius(radius) {
    currentRadius = radius;
    
    // 반경 버튼 상태 업데이트
    document.querySelectorAll('.radius-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-radius="${radius}"]`).classList.add('active');
    
    // 비상벨 다시 표시
    displayAllBells();
}

// 이벤트 리스너 등록
document.addEventListener('DOMContentLoaded', function() {
    // 지도 초기화
    initMap();
    
    // 비상벨 데이터 로드
    loadEmergencyBells();
    
    // 검색 이벤트
    const searchBox = document.getElementById('searchBox');
    searchBox.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchAddress();
        }
    });
    
    // 필터 버튼 이벤트
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const filterType = this.getAttribute('data-type');
            changeFilter(filterType);
        });
    });
    
    // 반경 버튼 이벤트
    document.querySelectorAll('.radius-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const radius = parseFloat(this.getAttribute('data-radius'));
            changeRadius(radius);
        });
    });
});

// 키보드 단축키
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.key === 'f') {
        e.preventDefault();
        document.getElementById('searchBox').focus();
    }
});
