import pandas as pd
import json
import numpy as np

# Excel 파일 읽기
df = pd.read_excel('안전비상벨정보.xlsx')

# NaN 값을 None으로 변환
df = df.replace({np.nan: None})

# 데이터를 JSON으로 변환
data = df.to_dict('records')

# JSON 파일로 저장
with open('emergency_bells.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'JSON 파일 생성 완료: {len(data):,}개의 비상벨 데이터')
print(f'파일 크기: {len(json.dumps(data, ensure_ascii=False)) / 1024 / 1024:.2f} MB')

# 데이터 검증
print('\n=== 데이터 검증 ===')
print(f'NaN 값이 있는 레코드 수: {df.isna().any(axis=1).sum()}')
print(f'부가기능 필드의 NaN 값 수: {df["부가기능"].isna().sum()}')
print('첫 번째 레코드 샘플:')
print(json.dumps(data[0], ensure_ascii=False, indent=2))
