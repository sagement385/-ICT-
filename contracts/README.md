# 팀 간 JSON 계약

계약 파일은 팀 간 연결점입니다. 계약 변경은 담당자 간 합의 후 별도 PR로 진행하며, API 응답 형식이 바뀌면 `docs/api-contract.md`와 관련 JSON Schema를 함께 수정합니다.

## 계약 목록

- `patient-event.schema.json`: 음성 AI가 백엔드로 전달하는 환자 상태 이벤트
- `hospital-candidate.schema.json`: 추천 후보로 교환하는 병원 역량·출처 구조
- `recommendation-request.schema.json`: 추천 실행 요청
- `recommendation-result.schema.json`: 프론트엔드가 표시하는 추천 결과

운영 데이터가 없는 상태에서 Schema 예시에는 실제 병원·환자 정보를 넣지 않습니다. 테스트 값은 각 팀의 fixture 경로에서만 사용합니다.

