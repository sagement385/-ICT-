# 개발 런북

## Windows native 실행

Docker Desktop 가상화가 없는 개발 PC에서는 PostgreSQL Windows 서비스, Python 3.12, Node.js를 직접 사용합니다.

```powershell
Copy-Item .env.example .env
cd backend
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

별도 PowerShell에서 다음을 실행합니다.

```powershell
cd frontend
npm install
npm run dev
```

## 서버가 뜨지 않을 때

- `.env`가 존재하는지 확인합니다.
- `GET /api/v1/health`로 프로세스 상태를 확인합니다.
- `GET /api/v1/ready`의 `details`에서 DB 설정·연결 상태를 확인합니다.

## 외부 연동이 503일 때

`EXTERNAL_SERVICE_NOT_CONFIGURED` 또는 source별 오류의 누락 설정명을 확인합니다. 실제 키를 로그에 출력하거나 커밋하지 않습니다.

## 추천이 실행되지 않을 때

- 환자 사건이 존재하는지 확인합니다.
- 병원 데이터가 비어 있지 않은지 확인합니다.
- 활성 정책과 가중치가 DB에 존재하는지 확인합니다.
- 경로와 실시간 상태의 `fetched_at`/`source_updated_at`를 확인합니다.

정책·병원·경로 데이터가 없는 경우 임의 결과를 수동으로 입력해 우회하지 않습니다.

## HIRA 병원 데이터 동기화

마이그레이션을 먼저 실행한 뒤 기본정보를 동기화합니다. 기본정보 API는 `CHUNGBUK_SIDO_CODE` 설정값으로 지역을 제한합니다.

```powershell
cd backend
alembic upgrade head
python scripts/sync_hospital_data.py --limit 1 --page-size 100
```

`--limit 1`은 API와 DB 연결을 확인하는 제어된 테스트용입니다. 전체 충북 병원 동기화가 확인된 뒤에만 `--limit`을 생략합니다.

상세정보는 기본정보가 적재된 병원을 대상으로 실행합니다. 상세 API는 병원별 여러 endpoint를 호출하므로 먼저 한 병원·한 endpoint로 확인합니다.

```powershell
python scripts/sync_hospital_detail_data.py --limit 1 --endpoint getDgsbjtInfo2.8
```

의료장비는 실제 필드를 확인한 endpoint로 다음처럼 제어된 검증을 할 수 있습니다.

```powershell
python scripts/sync_hospital_detail_data.py --limit 1 --endpoint getMedOftInfo2.8
```

상세 API에서 확인되지 않은 시설·병상·인력 필드는 임의로 병원 테이블에 채우지 않고 `raw_ingestion_event`의 원본 payload로 보존합니다.

## DB 없이 외부 API 확인

HIRA와 NEMC의 키·endpoint·응답 파서를 확인할 때는 다음 명령을 사용합니다. 이 명령은 DB에 쓰지 않습니다.

```powershell
python scripts/validate_data_sources.py --source all
```

Naver Directions는 `POST /api/v1/routing/test` 또는 지도용 `POST /api/v1/routing/batch`로 실제 거리와 소요시간을 확인합니다. `NAVER_DIRECTIONS_MAX_CALLS`가 비어 있으면 애플리케이션 자체 제한 없이 provider quota와 429 응답만 따릅니다. 지도 배치는 한 번에 최대 10개 목적지만 요청합니다.

## Naver Web Dynamic Map 인증 실패

프론트엔드 오류 안내에 표시된 현재 host를 Naver Cloud Maps 애플리케이션의 Web 서비스 URL에 등록합니다.

- Web Dynamic Map이 선택되어 있어야 합니다.
- `http://localhost`와 `http://127.0.0.1`은 서로 다른 등록값입니다.
- 공식 콘솔 안내에 따라 포트와 URI path는 제외합니다.
- 프론트엔드의 `VITE_NAVER_MAP_CLIENT_ID`가 해당 애플리케이션의 Key ID와 일치해야 합니다.
- 변경 후 개발 서버를 다시 시작하고 브라우저 캐시를 새로고침합니다.

SDK 인증 실패 시 코드는 가짜 지도나 마커를 표시하지 않습니다. JavaScript SDK는 현재 파라미터 `ncpKeyId`를 사용합니다.

## 추천 정책 문서 검증

정책 초안은 검증만 가능하며 자동 활성화되지 않습니다.

```powershell
cd backend
python scripts/create_policy.py --file ../docs/recommendation-policy-draft.json --validate-only
```

의료진 승인·근거 문서·모든 factor 값이 확보되기 전에는 `--insert --activate`를 실행하지 않습니다.

## NEMC 공식 응급의료기관 동기화

HIRA 기본 병원 데이터와 마이그레이션이 먼저 준비되어야 합니다.

```powershell
cd backend
python -m alembic upgrade head
python scripts/sync_emergency_institutions.py
python scripts/sync_realtime_status.py
```

첫 명령은 전국 공식 목록 원본을 보존한 뒤 주소가 `CHUNGBUK_REGION_NAME`으로 시작하는
기관만 HIRA 병원에 연결합니다. 이름이 없거나 중복되면 fail-closed로 제외하며 좌표 차이는
`NEMC_HIRA_COORDINATE_WARNING_METERS` 기준의 감사 경고로 남깁니다. 전체 수집이 성공한 뒤에만
이전 profile의 활성 상태를 갱신합니다.

실시간 수집은 profile의 `hpid`를 사용하므로 공식 목록 동기화 전에 실행하면
`EMERGENCY_INSTITUTION_DATA_NOT_SYNCED`로 중단됩니다. 공공데이터 API가 지연되면 bounded retry 후
`EXTERNAL_SERVICE_REQUEST_FAILED`가 발생하고 해당 실행의 DB 쓰기는 롤백됩니다.

정상 확인 항목:

- `GET /api/v1/hospitals?...` 결과에 `emergency_profile`이 존재함
- `data_source_registry`의 `nemc-emergency-institution-list` 최근 성공 시각이 존재함
- 실시간 병상 의미가 검증되기 전에는 `acceptance_status`, `available_beds`가 `null`임

NEMC 공식 문서에서 원본 timezone을 확인하기 전에는 `NEMC_SOURCE_TIMEZONE`을 비워 둡니다. 비어 있으면 `hvidate` 원문은 보존하지만 `source_updated_at`으로 변환하지 않습니다. 근거 확인 후에만 `Asia/Seoul`과 같은 IANA timezone 이름을 설정합니다.

## 최신 migration 확인

```powershell
cd backend
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

정상 상태는 `0006_child_provenance (head)`와 `No new upgrade operations detected.`입니다.

## 운영 상태와 DB 커버리지 확인

프론트엔드는 아래 두 API를 주기적으로 갱신합니다. 키와 원본 payload는 응답하지 않습니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/status
Invoke-RestMethod http://127.0.0.1:8000/api/v1/data-sources
```

PostgreSQL을 직접 확인할 때는 pgAdmin에서 `.env`의 `DATABASE_URL`과 같은 DB에 연결하거나,
`psql`에서 다음 읽기 전용 집계를 실행합니다. 환자 주소·좌표와 원본 payload는 일반 점검에서
조회하지 않습니다.

```sql
SELECT COUNT(*) AS hospitals FROM hospital;
SELECT COUNT(*) AS emergency_institutions
FROM hospital_emergency_profile WHERE active IS TRUE;
SELECT COUNT(DISTINCT hospital_id) AS realtime_coverage
FROM hospital_realtime_status;
SELECT source_name, verified, COUNT(*)
FROM hospital_source_identity
GROUP BY source_name, verified
ORDER BY source_name, verified;
SELECT source_name, last_success_at, last_failure_at, last_error
FROM data_source_registry
ORDER BY source_name;
SELECT COUNT(*) AS active_policies
FROM recommendation_policy WHERE enabled IS TRUE;
```

자동 이름 매칭은 `verified=false`로 남습니다. 운영자가 원본 HIRA/NEMC 기관 식별자와 주소를
대조해 검토하기 전에는 확정 매핑으로 표시하지 않습니다. 화면의 `기관 식별자 자동 매칭 ·
사람 검토 필요` 경고가 사라졌는지 확인합니다.

## 확인된 병원 상세정보 동기화

공식 응급기관에 한정해 실제 응답 구조가 검증된 상세 endpoint만 수집하려면 다음을 실행합니다.

```powershell
cd backend
python scripts/sync_hospital_detail_data.py --emergency-only --normalized-only
```

현재 정규화 대상은 확인된 진료과·전문의, 특수진료, 의료장비 endpoint입니다. 시설·병상처럼
의미가 확인되지 않은 필드는 원본만 보존하고 운영 컬럼을 임의로 채우지 않습니다.

## Speech AI 선택 서비스

실제 STT와 엔터티 모델이 정해지지 않아도 프로세스 health는 확인할 수 있습니다.

```powershell
cd speech-ai
pip install -e ".[dev]"
uvicorn app.main:app --port 8100
Invoke-RestMethod http://127.0.0.1:8100/health
Invoke-RestMethod http://127.0.0.1:8100/status
```

provider가 비어 있으면 `/status`는 `not_configured`를 반환합니다. 이는 정상적인 fail-closed
상태이며 가짜 전사나 환자 JSON을 생성하지 않습니다.

## NEMC 주기 수집 worker

수집 간격은 제공기관 정책과 팀 운영 기준을 확인한 뒤 `.env`의
`NEMC_SYNC_INTERVAL_SECONDS`에 명시합니다. 비어 있으면 임의 주기로 실행하지 않습니다.

```powershell
cd backend
python scripts/run_realtime_sync_worker.py --once
python scripts/run_realtime_sync_worker.py
```

Docker에서는 `docker compose --profile sync up --build`로 선택 실행합니다. 매 cycle은
`data_source_registry`의 성공/실패 시각을 갱신하며, 오류 메시지에는 키나 원본 응답을 넣지
않습니다. DB snapshot 보존 기간은 아직 운영 정책이 없으므로 별도 retention 작업을 자동
수행하지 않습니다.
