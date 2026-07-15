# 데이터베이스 스키마

Alembic `0001_initial_schema`, `0002_policy_route_snapshots`, `0003_model_indexes`가 다음 구조를 관리합니다. migration은 실제 환자·병원·정책·가중치 row를 삽입하지 않습니다.

| 영역 | 테이블 | 목적 |
| --- | --- | --- |
| 원본 | `raw_ingestion_event` | 외부/API·AI 원본 payload 보존 |
| 환자 | `patient_case`, `patient_symptom` | 환자 이벤트와 증상 |
| 병원 | `hospital`, `hospital_department`, `hospital_equipment`, `hospital_capability` | 병원 정규화 역량 |
| 실시간 | `hospital_realtime_status`, `route_snapshot` | 수용 상태·이동 경로 시점 기록 |
| 정책 | `recommendation_policy`, `recommendation_weight` | DB 관리 정책과 가중치 |
| 실행 | `recommendation_run`, `recommendation_result` | 추천 실행과 결과 감사 |
| 출처 | `data_source_registry` | 데이터 소스 상태와 마지막 성공/실패 |

정책 가중치는 애플리케이션 상수로 복제하지 않습니다. 가중치가 없으면 추천을 중단합니다.

`0002`는 정책 factor의 source field·방향·정규화·누락/오래된 데이터 처리 방식·제외 조건을 저장하고, `route_snapshot` 및 추천 결과 provenance를 추가합니다. `0003`은 모델에 선언된 조회 index만 추가합니다. 기존 테이블이나 운영 row를 삭제하지 않습니다.
