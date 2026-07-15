# 개발 런북

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

상세 API에서 확인되지 않은 시설·병상·인력 필드는 임의로 병원 테이블에 채우지 않고 `raw_ingestion_event`의 원본 payload로 보존합니다.

## DB 없이 외부 API 확인

HIRA와 NEMC의 키·endpoint·응답 파서를 확인할 때는 다음 명령을 사용합니다. 이 명령은 DB에 쓰지 않습니다.

```powershell
python scripts/validate_data_sources.py --source all
```

Naver Directions는 `POST /api/v1/routing/test` 또는 지도용 `POST /api/v1/routing/batch`로 실제 거리와 소요시간을 확인합니다. `NAVER_DIRECTIONS_MAX_CALLS`가 비어 있으면 애플리케이션 자체 제한 없이 provider quota와 429 응답만 따릅니다. 지도 배치는 한 번에 최대 10개 목적지만 요청합니다.
