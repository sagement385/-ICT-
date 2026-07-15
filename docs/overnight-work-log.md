# 안전한 MVP 보완 작업 기록

기준일: 2026-07-16

## 완료한 구현

- 환자 중복 등록을 409 `PATIENT_ALREADY_EXISTS`로 처리하고 원본 입력 출처를 보존했다.
- 공통 오류 envelope와 DB·외부 provider 예외 처리를 안정화했다.
- 활성 DB 정책만 해석하는 특징값·점수·순위·저장·최근 결과 파이프라인을 연결했다.
- 정책 factor의 source field, 방향, 정규화, 누락/오래된 데이터 처리, hard exclusion 메타데이터를 migration으로 추가했다.
- 실제 Naver 경로를 `route_snapshot`에 저장하고 거리·시간·path·provider·시각·출처를 추적한다.
- freshness를 `fresh`, `stale`, `unknown`, `unavailable`로 구분한다.
- HIRA 실제 샘플로 확인된 의료장비 필드만 parser와 동기화에 추가했다.
- HTTP 200 provider 오류 envelope를 빈 성공으로 오인하지 않도록 HIRA/NEMC validator를 보완했다.
- `data_source_registry`를 HIRA/NEMC 동기화 성공·실패 흐름에 연결했다.
- 채팅 입력에 AI 추출 결과 확인 단계를 추가하고, 후보 병원과 승인된 추천 결과를 화면에서 분리했다.
- Naver Maps JavaScript SDK 인증 파라미터를 `ncpKeyId`로 수정하고 콘솔 origin 안내를 추가했다.

## 실제 DB 보존 확인

작업 전 확인값은 병원 2,213건, 환자 5건, 환자 증상 5건, 원본 이벤트 69건, 진료과 96건, 실시간 상태 16건이었다. 기존 row를 삭제하거나 DB를 초기화하지 않았다.

제어된 HIRA 의료장비 API 1건 검증 후 원본 이벤트는 70건, 의료장비는 1건, 데이터 소스 레지스트리는 1건이 되었다. Naver 경로 1건 스모크 테스트 후 `route_snapshot`은 1건이다. 추천 정책과 가중치는 계속 0건이다. 정책 미설정 API 스모크 테스트는 추천 결과를 만들지 않고 실패 실행 감사 row 1건만 기록했다. `recommendation_result`는 0건이다.

## 현재 fail-closed 상태

- 활성 추천 정책: 없음
- 추천 가중치: 없음
- 실제 추천 결과: 생성하지 않음
- 추천 실행 응답: HTTP 503 `RECOMMENDATION_POLICY_NOT_CONFIGURED`
- 반경 내 병원과 실제 경로: 후보 정보로만 표시
- NEMC 수용 상태·가용병상: 공식 의미 검증 전까지 null/unknown

## 외부 차단 또는 수동 작업

- 의료진·응급의료협의체가 후보 제외 기준, factor 정의, 정규화 경계, 가중치와 근거 문서를 승인해야 한다.
- Naver Web Dynamic Map은 콘솔에 `http://localhost`와 필요 시 `http://127.0.0.1`을 등록한 후 브라우저에서 재확인해야 한다.
- ITS 표준 노드·링크 파일과 국토교통부 교통 API의 실제 샘플·endpoint를 확보해야 한다.
- NEMC 상태 코드와 병상 필드의 공식 코드표를 확보해야 한다.
- AI-Hub 음성 데이터 문제 해결 전까지 실제 STT·음성 학습은 보류한다.
- 운영 전 사용자 인증, 권한, 비밀 저장소, 감사 로그 보존 정책, HTTPS 및 개인정보 영향 검토가 필요하다.

## 검증 기준

- 테스트 fixture는 `TEST_*` 데이터만 사용한다.
- `.env`, API key, 운영 raw payload는 Git에 포함하지 않는다.
- migration은 schema/index만 변경하며 seed나 정책 자동 활성화를 하지 않는다.
- Dynamic Map 또는 provider 실패 시 가짜 경로·마커·추천을 생성하지 않는다.

## 실행한 검증

- `python -m pytest -q`: 43 passed
- `python -m ruff check app tests scripts migrations`: 통과
- `python -m mypy app`: 90개 source file 통과
- `npm run build`: TypeScript 및 Vite production build 통과
- `python -m alembic upgrade head`: `0003_model_indexes` head 유지
- `python -m alembic check`: 새 upgrade 작업 없음
- `GET /health`: 200 `ok`
- `GET /ready`: 200 `ready`
- 잘못된 환자 등록: 422 `REQUEST_VALIDATION_ERROR`
- 없는 환자 조회: 404 `PATIENT_NOT_FOUND`
- 반경 후보 조회: 200, 실제 DB 후보 존재
- Naver 배치 경로 1건: 200, 성공 1건·오류 0건 및 snapshot 저장
- 정책 미설정 추천 실행: 503 `RECOMMENDATION_POLICY_NOT_CONFIGURED`, 추천 결과 미생성
