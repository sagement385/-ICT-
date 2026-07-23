# HIRA 상세 응답 필드 확인 결과

2026-07-15에 승인된 개발계정으로 충북 병원 기본목록의 한 기관을 조회한 뒤, 실제 응답에 존재하는 필드만 기록했다.

| endpoint | 확인된 필드 | 현재 처리 |
| --- | --- | --- |
| `getSpcSbjtSdrInfo2.8` | `dgsbjtCd`, `dgsbjtCdNm`, `dtlSdrCnt` | `hospital_department`로 정규화 |
| `getDgsbjtInfo2.8` | `dgsbjtCd`, `dgsbjtCdNm`, `dgsbjtPrSdrCnt`, `cdiagDrCnt` | `hospital_department`로 정규화 |
| `getSpclDiagInfo2.8` | `srchCd`, `srchCdNm` | `hospital_capability`로 저장하되 `available`은 null |
| `getMedOftInfo2.8` | `oftCd`, `oftCdNm`, `oftCnt` | `hospital_equipment`로 정규화 |
| `getSpclHospAsgFldList2.8` | 실제 정상 응답 확인, 조회 기관에 항목 없음 | 항목이 있는 민감정보 제거 샘플 확보 전 raw 이벤트로 보존 |
| `getEqpInfo2.8` | 시설·병상 수치 필드 | 전용 병상/시설 스키마가 없어 raw 이벤트로 보존 |
| `getDtlInfo2.8` | 진료시간·주차·응급실 전화 필드 | raw 이벤트로 보존 |
| `getNursigGrdInfo2.8` | 간호등급 필드 | raw 이벤트로 보존 |
| `getEtcHstInfo2.8` | 기타 인력 필드 | raw 이벤트로 보존 |
| `getTrnsprtInfo2.8` | 정상 응답, 조회 기관에 항목 없음 | raw 이벤트로 보존 |

문서에서 확인되지 않았거나 404를 반환한 유사 endpoint 이름은 추측해 호출하지 않는다. 의료장비는 실제 응답으로 확인된 `getMedOftInfo2.8`만 사용한다.
