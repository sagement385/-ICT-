# API 계약

Base path: `/api/v1`

## 공통 오류

```json
{
  "error": {
    "code": "RECOMMENDATION_POLICY_NOT_CONFIGURED",
    "message": "활성화된 추천 정책이 없습니다.",
    "details": {},
    "request_id": "generated-request-id"
  }
}
```

## 엔드포인트

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/health` | 프로세스 상태. 외부 데이터가 없어도 응답 |
| GET | `/ready` | DB 및 필수 서비스 연결 상태 |
| GET | `/status` | DB 커버리지, 외부 연동 설정 여부, 기능 준비도와 운영 경고 |
| GET | `/data-sources` | API 키·원본 payload를 제외한 데이터 소스 수집 성공/실패·최신성 상태 |
| POST | `/patients` | `patient-event.schema.json` 기반 환자 이벤트 저장 |
| POST | `/patients/assist` | Gemini로 사용자 문장에서 명시된 사실만 구조화. 진단·중증도 판단·병원 추천을 수행하지 않으며 항상 사람 확인이 필요함 |
| GET | `/patients/{incident_id}` | 환자 이벤트 조회 |
| POST | `/locations/geocode` | body의 주소를 Naver Geocoding으로 변환. 주소를 access-log URL에 남기지 않음 |
| POST | `/hospitals/nearby-candidates` | 저장된 `incident_id`와 5~10km 반경으로 공식 응급기관 상세 후보 조회 |
| GET | `/locations/geocode`, `/hospitals`, `/hospitals/nearby-candidates` | 이전 호환용 deprecated API. 신규 프론트에서는 사용하지 않음 |
| GET | `/hospitals/{hospital_id}` | 출처가 있는 병원 조회 |
| GET | `/routing/status` | Naver Directions 설정 및 프로세스 호출 한도 확인 |
| POST | `/routing/test` | DB 없이 Naver Directions 5 실제 경로 1건 확인 |
| POST | `/routing/batch` | 환자 위치와 화면에 표시할 병원 최대 10곳의 실제 경로를 조회. 실패 병원은 `errors`에 기록 |
| POST | `/recommendations/{incident_id}/run` | 정책·병원·경로·상태가 모두 준비된 경우에만 실행. body는 선택적 `limit`만 포함 |
| GET | `/recommendations/{incident_id}/latest` | 최근 저장 결과 조회 |

추천 결과 구조는 [`contracts/recommendation-result.schema.json`](../contracts/recommendation-result.schema.json)을 기준으로 합니다. 실제 결과가 없을 때는 빈 결과를 위조하지 않고 오류 또는 `RECOMMENDATION_RESULT_NOT_FOUND`를 반환합니다.

병원 단건·반경 조회 응답은 [`contracts/hospital-summary.schema.json`](../contracts/hospital-summary.schema.json), 추천 평가용 상세 후보는 [`contracts/hospital-candidate.schema.json`](../contracts/hospital-candidate.schema.json)을 사용합니다. 추천 실행의 `incident_id`는 URL path가 단일 기준이며 body에서 반복하지 않습니다.

`/patients/assist`는 `GEMINI_API_KEY`가 없거나 유효하지 않으면 각각 `EXTERNAL_SERVICE_NOT_CONFIGURED` 또는 `GEMINI_API_ERROR`를 반환합니다. Gemini 결과는 환자 등록을 자동 확정하지 않습니다.
응답은 `extracted_by_ai=true`, `needs_human_review=true`, provider가 보정된 신뢰도를 제공하지 않을 때 `confidence=null`, 그리고 model source를 명시합니다. 사람이 확인한 뒤 등록하면 환자 event source에 Gemini 보조 사용 여부가 기록됩니다.

`POST /locations/geocode`는 장소 검색이 아니라 주소 좌표 변환입니다. 기관명·상호만 입력해
Naver가 주소를 반환하지 않으면 404 `ADDRESS_NOT_FOUND`이며 좌표를 추정하지 않습니다. 정확한
도로명/지번 주소 또는 프론트가 지원하는 `위도,경도` 직접 입력을 사용합니다.

`/routing/batch`에 `incident_id`를 보내면 성공한 실제 경로만 `route_snapshot`에 저장합니다. 환자가 없으면 404 `PATIENT_NOT_FOUND`, provider 일부 실패는 HTTP 성공 응답의 `errors` 배열에 병원별 코드로 기록합니다. 실패 경로는 저장하지 않습니다.

## 주요 오류와 상태 코드

| HTTP | code | 의미 |
| --- | --- | --- |
| 404 | `PATIENT_NOT_FOUND`, `HOSPITAL_NOT_FOUND`, `RECOMMENDATION_RESULT_NOT_FOUND` | 요청한 저장 데이터가 없음 |
| 409 | `PATIENT_ALREADY_EXISTS` | 같은 `incident_id`가 이미 등록됨 |
| 422 | `REQUEST_VALIDATION_ERROR` 계열 | 좌표·반경·계약 입력이 유효하지 않음 |
| 503 | `DATABASE_NOT_CONFIGURED`, `DATABASE_CONNECTION_FAILED` | DB 설정 또는 연결 실패 |
| 503 | `EXTERNAL_SERVICE_NOT_CONFIGURED` | `details.missing_settings`의 환경변수가 누락됨 |
| 503 | `EXTERNAL_SERVICE_HTTP_ERROR` | provider가 401/403/429/5xx를 반환함 |
| 503 | `RECOMMENDATION_POLICY_NOT_CONFIGURED` | 활성 정책 또는 가중치가 없음 |
| 503 | `RECOMMENDATION_POLICY_INVALID` | 활성 정책 factor가 불완전하거나 지원되지 않음 |

예상하지 못한 서버 오류도 동일 envelope와 `request_id`를 반환하며, 원본 외부 응답이나 비밀키를 오류 응답에 포함하지 않습니다.

## 응급의료기관 후보 계약

`POST /hospitals/nearby-candidates`는 반경 안의 모든 의료기관이 아니라 NEMC 공식 응급의료기관 목록과
고유하게 연결된 병원만 반환합니다. 각 항목의 `emergency_profile`에는 NEMC 분류,
전화, 출처 ID, raw payload ID, 매칭 방식, 사람 검증 여부, 좌표 경고와 독립적인 freshness가 포함됩니다.
자동 이름 매칭은 `identity_verified=false`로 표시되며 확정된 동일 기관으로 가장하지 않습니다.

| HTTP | code | 의미 |
| --- | --- | --- |
| 503 | `EMERGENCY_INSTITUTION_DATA_NOT_SYNCED` | NEMC 공식 목록이 아직 DB에 동기화되지 않음 |
| 503 | `EXTERNAL_SERVICE_REQUEST_FAILED` | 외부 API가 재시도 후에도 타임아웃 또는 네트워크 오류 |

추천 실행도 같은 공식 후보 집합을 사용하며, profile이 없으면 가짜 추천을 생성하지 않습니다.
