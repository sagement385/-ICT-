# 충북 119 AI 기반 응급환자 병원 추천 및 이송 경로 지원 시스템

충북 지역 응급환자에 대해 사람이 확인한 환자 상태, 출처가 확인된 병원 정보, 실시간 데이터의 가용 여부, 실제 자동차 이동시간을 한 화면에서 확인하도록 돕는 의사결정 지원 MVP입니다. 음성 AI가 준비되기 전에는 단계별 채팅 입력을 사용합니다.

이 프로젝트는 의료진이나 구급대원의 판단을 대체하지 않습니다. 실제 의료 기준·병원 수용 상태·운전 판단을 시스템이 대신 결정하지 않으며, 데이터가 없거나 오래된 경우 추천을 생성하지 않고 오류 또는 경고를 표시합니다.

## 데이터 흐름

```text
신고자/구급대원 입력(현재: 채팅, 향후: 검증된 speech-ai)
  -> 사람 검토를 거친 구조화 patient-event
  -> POST /api/v1/patients
  -> raw_ingestion_event + patient_case + patient_symptom
  -> 병원 공공데이터/HIRA 동기화
  -> 실시간 수용 상태 및 네이버 Directions 조회
  -> DB 정책/가중치 기반 추천 실행
  -> recommendation-result JSON
  -> 지도·환자 상태·추천 근거 UI
```

모듈은 공통 JSON Schema와 API 계약을 통해 연결합니다. 다른 팀의 내부 모듈을 직접 import하지 않고 API, repository, provider 인터페이스 경계를 사용합니다.

## 저장소 구조와 팀 담당

| 팀원 | 담당 경로 | 책임 |
| --- | --- | --- |
| 1. AI 음성처리 | `speech-ai/`, `contracts/patient-event.schema.json` | STT, 음성 전처리, 환자 이벤트 생성 |
| 2. 환자·병원·추천 | `backend/app/modules/patient/`, `hospital/`, `recommendation/`, HIRA·공공데이터·병원 동기화, 추천 테스트 | 저장·정규화·후보·정책 기반 순위 |
| 3. 지도·프론트엔드 | `frontend/`, `backend/app/modules/routing/`, Naver Maps·ITS | 지도, 경로, 결과 화면 |
| 4. 통합·배포 | `backend/app/main.py`, `core/`, `api/`, `contracts/`, `infra/`, Docker, CI, docs | 공통 오류·설정·API·배포 |

상세 경계와 충돌 방지 규칙은 [`docs/team-ownership.md`](docs/team-ownership.md)를 참고합니다.

## 빠른 시작

### 1. 환경변수

```powershell
Copy-Item .env.example .env
```

실제 키와 토큰은 `.env` 또는 비밀 저장소에만 넣고 커밋하지 않습니다. 필수 변수 목록은 [`.env.example`](.env.example)에 있습니다.

### 2. 로컬 백엔드

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

`GET /api/v1/health`는 DB 없이도 서버 상태를 확인할 수 있습니다. `ready` 및 DB를 사용하는 API는 DB 연결 설정이 없으면 명확한 오류를 반환합니다.

Windows에서 Docker Desktop 가상화가 지원되지 않아도 위 방식으로 실행할 수 있습니다. PostgreSQL은 Windows 서비스로 실행하고 `DATABASE_URL`만 로컬 인스턴스에 맞게 설정합니다. 프론트엔드는 별도 PowerShell에서 실행합니다.

```powershell
cd frontend
npm ci
npm run dev
```

### 3. Docker Compose

```powershell
docker compose up --build
```

서비스:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

Compose는 PostgreSQL healthcheck 후 `migrate` 서비스가 Alembic을 적용하고, 그다음 Backend와 Frontend를 시작합니다. `speech-ai`는 기본 실행에서 제외하며 `docker compose --profile speech up --build`로 선택 실행합니다. 기본 PostgreSQL 계정은 로컬 개발 편의를 위한 값이므로 운영 환경에서는 `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`를 비밀 저장소에서 반드시 재설정합니다.

### 4. 마이그레이션

```powershell
cd backend
alembic upgrade head
```

마이그레이션은 스키마만 변경합니다. 운영 병원·환자·정책·가중치 데이터는 자동 삽입하지 않습니다.

### 5. 테스트와 품질 검사

```powershell
python -m pytest backend/tests
python -m ruff check backend
python -m mypy backend/app
```

프론트엔드는 다음을 사용합니다.

```powershell
cd frontend
npm ci
npm test -- --run
npm run build
npm audit --omit=dev
```

음성 경계는 다음을 사용합니다.

```powershell
python -m pytest speech-ai/tests
python -m ruff check speech-ai
python -m mypy speech-ai/app
```

## 현재 구현된 기능

- FastAPI health/ready 및 기본 도메인 API 라우터
- Pydantic v2 요청 검증과 공통 오류 응답(`request_id` 포함)
- SQLAlchemy 2 모델과 additive Alembic migration(`0001`~`0006`)
- 환자·병원 repository/service 경계
- 중복 환자 409 처리, 원본 이벤트 및 입력 출처 보존
- HIRA 충북 병원 기본정보와 실제 샘플로 확인된 진료과·전문의·의료장비 일부 정규화
- NEMC 공식 응급의료기관 목록 기반 후보 필터와 `hpid` 실시간 상태 연결(의미 미확인 상태값은 null 유지)
- 검토 전 자동 source identity를 `verified=false`로 보존하고 NEMC 원본 시각 timezone을 추측하지 않는 구조
- DB 정책을 해석하는 특징값·점수·순위·저장·최근 결과 파이프라인
- 활성 정책 또는 가중치가 없을 때 503으로 닫히는 추천 API
- Naver Directions/Geocoding 연동, 부분 실패 처리, 경로 snapshot·출처 저장
- 사건·공식 응급기관 ID만 받는 개인정보 보호형 후보/경로 API와 최대 10개·동시 3개 경로 호출 제어
- 데이터 최신성 `fresh`/`stale`/`unknown`/`unavailable` 구분
- `/api/v1/status`, `/api/v1/data-sources` 기반 실시간 운영 준비도·수집 이력 표시
- 명시된 `NEMC_SYNC_INTERVAL_SECONDS`에서만 동작하는 선택형 실시간 수집 worker
- 외부 API 공통 클라이언트, 재시도·timeout·request id·raw 응답 저장 구조
- Gemini를 이용한 명시 사실 추출 보조와 사람 확인 단계
- AI-Hub/ITS 연동 인터페이스
- 팀 간 JSON Schema
- 후보 병원과 승인된 추천 결과를 구분하고 오류·재시도·지도 인증 안내를 제공하는 프론트엔드
- React Query 기반 주기적 상태 갱신, 지도 객체 재사용, 후보 선택·경로 연결 UI
- Speech AI health/status, 파일 경계 검증, 빈 전사 차단, 백엔드 재시도·멱등 전송 구조
- PostgreSQL migration·Backend·Frontend·Speech AI 테스트 및 GitHub Actions

## 아직 구현하지 않은 기능

- 실제 STT 모델과 의료 엔터티 추출 모델
- 승인된 AI-Hub 원본 데이터의 전처리 파이프라인
- 승인된 실제 STT/AI-Hub 데이터 처리
- ITS 표준 노드·링크 파일 및 국토교통부 교통 API parser
- HIRA 시설·병상 등 의미가 아직 확인되지 않은 상세 필드 정규화
- NEMC 상태 코드의 공식 의미를 반영한 수용 가능 여부·가용병상 정규화
- 의료진이 승인한 후보 제외 기준, 활성 추천 정책 및 가중치
- 운영용 인증/권한/감사 정책

2026-07-22 로컬 검증 시점에는 HIRA 병원 2,213건 중 NEMC 공식 충북 응급기관 21건이 연결됐고, 그중 실시간 원본 15개 기관, 진료과·장비 21개 기관, 특수진료 19개 기관의 데이터가 조회됐습니다. NEMC↔HIRA 자동 매칭 21건은 모두 `verified=false`이므로 운영 투입 전 사람의 검토가 필요합니다. 이 값은 고정 운영 데이터가 아니라 수집 시점의 검증 기록이며 화면에서는 DB 집계값을 실시간으로 표시합니다.

외부 API 키가 없으면 서버 자체는 시작할 수 있으나 해당 기능 호출 시 `EXTERNAL_SERVICE_NOT_CONFIGURED` 또는 기능별 설정 오류로 HTTP 503을 반환합니다. 추천 정책이 없으면 `RECOMMENDATION_POLICY_NOT_CONFIGURED`로 중단합니다.

## 설계 원칙

- 운영 데이터와 API 응답을 코드에 하드코딩하지 않습니다.
- 추천 가중치는 코드가 아니라 `recommendation_policy`, `recommendation_weight`에서 읽습니다.
- 외부 원본 payload와 출처·시각·스키마 버전을 추적합니다.
- 최신성을 확인하지 못한 데이터는 `unknown`, 데이터 자체가 없으면 `unavailable`로 표시합니다.
- 테스트 데이터는 각 프로젝트의 `tests/fixtures/` 아래에만 둡니다.
- 이 시스템은 의료 의사결정 보조 도구이며, 최종 판단은 의료진·구급대원이 합니다.

## 데이터 확인 순서

외부 API를 구현할 때는 공식 문서와 실제 샘플 응답을 먼저 확보하고, 확인된 필드만 parser/validator에 반영합니다. 현재 확인 결과와 TODO는 [`docs/data-sources.md`](docs/data-sources.md)에 기록했습니다.

## 채팅 입력과 Gemini 보조 추출

음성 AI 데이터가 준비되기 전에는 프론트엔드의 단계별 채팅 입력을 사용합니다. 증상 자유 입력만 `POST /api/v1/patients/assist`로 보내 Gemini가 사용자 문장에 명시한 사실을 구조화합니다. 이 기능은 진단, KTAS/Pre-KTAS 판단, 병원 추천, 수용 가능 여부 판단을 하지 않으며 결과에는 항상 사람 확인 필요 표시가 포함됩니다.

`GEMINI_API_KEY`가 없으면 `EXTERNAL_SERVICE_NOT_CONFIGURED`, 키가 유효하지 않거나 Gemini가 오류를 반환하면 `GEMINI_API_ERROR`로 HTTP 503을 반환합니다. 오류 시 프론트엔드는 사용자가 입력한 원문을 보존해 수동 확인 흐름으로 진행합니다. 키는 `.env`에만 저장하고 저장소에는 올리지 않습니다.

## NEMC 공식 응급의료기관 후보 필터

지도와 추천의 병원 후보는 HIRA 전체 의료기관을 그대로 사용하지 않습니다. 먼저 NEMC
`getEgytListInfoInqire`에서 공식 응급의료기관 목록을 수집하고, 충청북도 주소를 가진
기관을 기존 HIRA 병원과 고유한 정규화 이름으로 연결합니다. 연결되지 않거나 여러 병원과
중복 매칭되는 기관은 후보에 포함하지 않습니다. ITS 노드·링크 데이터는 이 자격 필터에
필요하지 않으며, 향후 자체 도로망 분석을 구현할 때 사용합니다.

```powershell
cd backend
python -m alembic upgrade head
python scripts/sync_hospital_data.py
python scripts/sync_emergency_institutions.py
python scripts/sync_realtime_status.py
```

공식 응급기관 목록이 동기화되지 않은 상태에서 반경 병원 조회 또는 추천을 실행하면
가짜 후보를 반환하지 않고 HTTP 503 `EMERGENCY_INSTITUTION_DATA_NOT_SYNCED`를 반환합니다.
NEMC 실시간 응답의 병상·수용 상태 코드 의미는 공식 코드표가 확보될 때까지 `null`로 유지합니다.
