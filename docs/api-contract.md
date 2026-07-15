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
| GET | `/patients/{incident_id}` | 환자 이벤트 조회 |
| GET | `/hospitals/{hospital_id}` | 출처가 있는 병원 조회 |
| POST | `/recommendations/{incident_id}/run` | 정책·병원·경로·상태가 모두 준비된 경우에만 실행 |
| GET | `/recommendations/{incident_id}/latest` | 최근 저장 결과 조회 |

추천 결과 구조는 [`contracts/recommendation-result.schema.json`](../contracts/recommendation-result.schema.json)을 기준으로 합니다. 실제 결과가 없을 때는 빈 결과를 위조하지 않고 오류 또는 `RECOMMENDATION_RESULT_NOT_FOUND`를 반환합니다.

