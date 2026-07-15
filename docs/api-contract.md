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
| POST | `/patients` | `patient-event.schema.json` 기반 환자 이벤트 저장 |
| POST | `/patients/assist` | Gemini로 사용자 문장에서 명시된 사실만 구조화. 진단·중증도 판단·병원 추천을 수행하지 않으며 항상 사람 확인이 필요함 |
| GET | `/patients/{incident_id}` | 환자 이벤트 조회 |
| GET | `/locations/geocode?address=...` | Naver Geocoding으로 주소를 좌표로 변환 |
| GET | `/hospitals?latitude=...&longitude=...&radius_km=5..10` | 저장된 병원 중 정확한 반경 후보 조회 |
| GET | `/hospitals/{hospital_id}` | 출처가 있는 병원 조회 |
| GET | `/routing/status` | Naver Directions 설정 및 프로세스 호출 한도 확인 |
| POST | `/routing/test` | DB 없이 Naver Directions 5 실제 경로 1건 확인 |
| POST | `/routing/batch` | 환자 위치와 화면에 표시할 병원 최대 10곳의 실제 경로를 조회. 실패 병원은 `errors`에 기록 |
| POST | `/recommendations/{incident_id}/run` | 정책·병원·경로·상태가 모두 준비된 경우에만 실행 |
| GET | `/recommendations/{incident_id}/latest` | 최근 저장 결과 조회 |

추천 결과 구조는 [`contracts/recommendation-result.schema.json`](../contracts/recommendation-result.schema.json)을 기준으로 합니다. 실제 결과가 없을 때는 빈 결과를 위조하지 않고 오류 또는 `RECOMMENDATION_RESULT_NOT_FOUND`를 반환합니다.

`/patients/assist`는 `GEMINI_API_KEY`가 없거나 유효하지 않으면 각각 `EXTERNAL_SERVICE_NOT_CONFIGURED` 또는 `GEMINI_API_ERROR`를 반환합니다. Gemini 결과는 환자 등록을 자동 확정하지 않습니다.
