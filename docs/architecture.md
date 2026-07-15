# 아키텍처

## 경계

```text
speech-ai --patient-event.schema.json--> backend API
backend API -> patient service -> patient repository -> PostgreSQL
hospital sync -> integration clients -> raw_ingestion_event -> hospital repositories
recommendation service -> policy/repository/provider interfaces -> recommendation result
frontend -> backend API + configured Naver Maps SDK
```

`main.py`는 앱과 router 등록만 담당합니다. router는 입력 검증과 service 호출만 수행하고, DB 쿼리·점수 계산·외부 HTTP 호출을 직접 수행하지 않습니다.

## 안전한 실패

- 환경변수가 없으면 서버 시작은 허용하되 기능 호출 시 `EXTERNAL_SERVICE_NOT_CONFIGURED` 계열 503을 반환합니다.
- DB 연결이 없으면 health는 200, ready와 DB 기능은 설정/연결 오류를 반환합니다.
- 활성 정책·가중치가 없으면 추천을 만들지 않고 `RECOMMENDATION_POLICY_NOT_CONFIGURED`를 반환합니다.
- 병원/경로/실시간 상태가 오래되었거나 없으면 결과를 추측하지 않고 오류 또는 stale 경고를 반환합니다.

## 데이터 출처

원본 payload는 `raw_ingestion_event`에 보존하고, 정규화된 레코드에는 source name, record id, fetched/source updated time, schema version, raw payload id를 연결합니다.

