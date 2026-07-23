# 아키텍처

## 경계

```text
speech-ai --patient-event.schema.json--> backend API
backend API -> patient service -> patient repository -> PostgreSQL
hospital sync -> integration clients -> raw_ingestion_event -> hospital repositories
cross-source identity -> hospital_source_identity(verified=false until reviewed)
recommendation service -> active DB policy -> source-backed features -> score/rank -> audited result
frontend -> backend API + configured Naver Maps SDK
```

`main.py`는 앱과 router 등록만 담당합니다. router는 입력 검증과 service 호출만 수행하고, DB 쿼리·점수 계산·외부 HTTP 호출을 직접 수행하지 않습니다.

## 안전한 실패

- 환경변수가 없으면 서버 시작은 허용하되 기능 호출 시 `EXTERNAL_SERVICE_NOT_CONFIGURED` 계열 503을 반환합니다.
- DB 연결이 없으면 health는 200, ready와 DB 기능은 설정/연결 오류를 반환합니다.
- 활성 정책·가중치가 없으면 추천을 만들지 않고 `RECOMMENDATION_POLICY_NOT_CONFIGURED`를 반환합니다.
- 정책 factor가 불완전하면 `RECOMMENDATION_POLICY_INVALID`, 필수 데이터가 없거나 오래되면 정책에 선언된 방식으로 실패·후보 제외·경고 처리합니다.
- 병원/경로/실시간 상태의 timestamp나 기준 시간이 없으면 `fresh`로 간주하지 않고 `unknown`으로 표시합니다.

## 데이터 출처

원본 payload는 `raw_ingestion_event`에 보존하고, 정규화된 레코드에는 source name, record id, fetched/source updated time, schema version, raw payload id를 연결합니다.

화면의 반경 후보 목록은 승인된 의료 추천이 아닙니다. 최종 추천 섹션은 활성 정책으로 저장된 `recommendation_result`가 있을 때만 표시됩니다.
자동 매칭된 NEMC↔HIRA 식별자가 사람 검증 전이면 후보와 특징값에
`HOSPITAL_SOURCE_IDENTITY_UNVERIFIED` 경고를 남깁니다. 이 경고는 숨겨진 확정 매칭으로
변환되지 않으며 정책 승인 과정에서 제외 여부를 별도로 결정해야 합니다.

## 런타임 연결과 갱신

FastAPI lifespan이 외부 API용 `httpx.AsyncClient`를 한 번 생성해 Gemini, Naver Geocoding,
Naver Directions 호출에서 재사용합니다. 경로 조회는 저장된 사건과 공식 응급기관 ID만 입력으로
받고, 서버가 canonical 좌표를 로드합니다. 최대 후보 수와 동시 호출 수를 제한하며 유효한
`route_snapshot`만 재사용합니다.

프론트엔드는 React Query로 운영 상태·데이터 소스·현재 후보를 주기적으로 갱신합니다. 실제
경로는 API 비용과 호출 제한 때문에 사건 또는 후보가 바뀔 때와 사용자의 명시적 재조회 때만
호출합니다. 지도 객체는 재생성하지 않고 marker와 선택된 경로 overlay만 갱신합니다.

HIRA 기본 동기화의 단일 구현은 `app/pipelines/hospital_sync/pipeline.py`입니다. CLI 스크립트는
이 파이프라인만 호출하며, 원본 저장 전 정규화하거나 별도의 중복 parser를 사용하지 않습니다.

## 음성 경계

`speech-ai`는 Backend 내부 모듈을 import하지 않고 `patient-event` JSON 계약과 HTTP API로만
연결됩니다. 승인된 STT/엔터티 provider가 없으면 `/health`는 프로세스 상태를, `/status`는
`not_configured`를 반환합니다. 빈 전사·허용되지 않은 파일·데이터 루트 밖 경로는 환자 이벤트를
만들기 전에 중단합니다.
