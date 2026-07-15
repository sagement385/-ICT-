# 팀 소유권과 충돌 방지

## 담당 경계

- 팀원 1: `speech-ai/`, `contracts/patient-event.schema.json`
- 팀원 2: `backend/app/modules/patient/`, `hospital/`, `recommendation/`, `integrations/hira/`, `integrations/public_data/`, `pipelines/hospital_sync/`, `backend/migrations/`, `backend/scripts/sync_hospital_data.py`, `backend/tests/recommendation/`
- 팀원 3: `frontend/`, `backend/app/modules/routing/`, `backend/app/integrations/naver_maps/`, `backend/app/integrations/its/`
- 팀원 4: `backend/app/main.py`, `backend/app/core/`, `backend/app/api/`, `contracts/`, `infra/`, `docker-compose.yml`, `.github/`, `docs/`

## 규칙

- 다른 담당자의 폴더를 직접 수정하지 않습니다.
- 공통 계약 변경은 `contracts/` 수정 PR로 진행합니다.
- API 응답 형식 변경 시 `docs/api-contract.md`와 JSON Schema를 같이 수정합니다.
- DB 변경은 Alembic migration으로만 진행합니다.
- 외부 API 응답 샘플은 민감정보 제거 후 해당 `tests/fixtures/`에 저장합니다.
- `main.py`에서 비즈니스 로직을 작성하지 않습니다.
- router에서는 DB 쿼리나 점수 계산을 수행하지 않습니다.
- repository는 DB 조회·저장만 담당합니다.
- service는 업무 흐름을 담당합니다.
- integration client는 외부 API 통신만 담당합니다.

