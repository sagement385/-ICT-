# 데이터 소스 등록부

아래 표는 2026-07-15에 공식 페이지를 확인한 결과입니다. `실제 응답 샘플 확보 여부`는 공식 문서의 샘플/페이지 확인과 별개로, 팀이 민감정보 제거 후 테스트 fixture로 보관했는지를 구분합니다.

| 데이터 소스명 | URL | 데이터셋 ID | 제공기관 | 인증 방식 | API 키 환경변수명 | 실제 응답 샘플 확보 여부 | 파서 구현 여부 | 갱신 주기 | 마지막 수집 성공 시각 | 비고 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AI-Hub 위급상황 음성/음향 (고도화) - 119 지능형 신고접수 음성 인식 데이터 | [AI-Hub](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71768) | `71768` | 한국지능정보사회진흥원/AI-Hub 및 구축기관 | 신청·승인 후 다운로드/API 이용. 정확한 key 방식 TODO | `AIHUB_API_KEY` (승인 절차 확인 TODO), `AIHUB_DATA_ROOT` | 공식 페이지에 메타데이터와 라벨 JSON 예시 확인. 민감정보 제거 fixture는 아직 없음 | 아니오. 필드 확인 후 parser PR 예정 | 페이지 갱신 2024-10 표시. 운영 수집 주기 TODO | 없음 | 공개 페이지는 오디오·전사·긴급도·증상 구조와 예시를 제공하지만 원본 다운로드 승인 필요 |
| AI-Hub 의료 분야 음성 데이터 | [AI-Hub](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=566) | `566` | 한국지능정보사회진흥원/AI-Hub 및 구축기관 | 온라인 안심존·신청 승인 절차 | `AIHUB_API_KEY` (정확한 방식 TODO), `AIHUB_DATA_ROOT` | 페이지에 WAV/TXT/JSON 메타데이터 구조는 확인. 원본 응답 fixture 없음 | 아니오 | 갱신년월 2022-07 표시. 운영 수집 주기 TODO | 없음 | 의료 데이터 접근은 안심존/승인 절차 확인 필요 |
| Google Gemini generateContent (채팅 명시 사실 추출 보조) | [Gemini API 문서](https://ai.google.dev/gemini-api/docs) | 해당 없음 | Google | `x-goog-api-key` 헤더 | `GEMINI_API_KEY` | 유효하지 않은 후보 키의 400 오류 응답만 확인. 성공 payload fixture 없음 | 응답 envelope 및 구조화 JSON 검증 구현. 진단·분류·추천은 구현하지 않음 | 요청 시 | 2026-07-16 확인 | 키가 없거나 유효하지 않으면 HTTP 503으로 닫힘 |
| 건강보험심사평가원_병원정보서비스 | [공공데이터포털](https://www.data.go.kr/data/15001698/openapi.do) | `15001698` | 건강보험심사평가원 | 공공데이터포털 발급 서비스키 `ServiceKey` | `HIRA_API_KEY` 또는 `PUBLIC_DATA_API_KEY` | 충북 코드 `330000`으로 HTTP 200 실제 응답 확인. 저장소 fixture는 민감정보 방지를 위해 미등록 | 기본 목록 parser 구현. 상세 필드는 별도 parser 보류 | 포털에 실시간 표시 | 2026-07-15 확인 | `getHospBasisList`, `ykiho`, `yadmNm`, `addr`, `telno`, `XPos`, `YPos`, `clCd` 등 확인 |
| 건강보험심사평가원_의료기관별상세정보서비스 | [공공데이터포털](https://www.data.go.kr/data/15001699/openapi.do) | `15001699` | 건강보험심사평가원 | 공공데이터포털 발급 서비스키 `ServiceKey` | `HIRA_API_KEY` 또는 `PUBLIC_DATA_API_KEY` | 개발계정으로 실제 응답 필드 확인. 저장소에는 필드 구조를 재현한 `TEST_*` fixture만 등록 | 진료과·전문의, 특수진료 코드, 의료장비(`oftCd`, `oftCdNm`, `oftCnt`) parser 구현. 시설·병상·기타 상세는 raw-only | 포털에 실시간 표시 | 2026-07-16 제어된 1기관 의료장비 동기화 성공 | `getMedOftInfo2.8` 등 확인된 endpoint만 정규화하며, `getEqpInfo2.8`의 시설·병상 수치는 전용 검증 전까지 원본 보존 |
| 국립중앙의료원_응급의료기관 실시간 가용병상정보 | [공공데이터포털](https://www.data.go.kr/data/15000563/openapi.do) | `15000563` | 국립중앙의료원 중앙응급의료센터 | 공공데이터포털 발급 서비스키 `serviceKey` | `NEMC_API_KEY` 또는 `PUBLIC_DATA_API_KEY` | 실시간 endpoint HTTP 200 실제 응답 확인. 저장소 fixture는 `TEST_*` 합성 데이터만 등록 | raw payload 보존 및 식별자·기관명·갱신시각 parser 구현. 상태 코드 의미는 TODO | 실시간 | 2026-07-15 확인 | `getEmrrmRltmUsefulSckbdInfoInqire`; 충북 HIRA 병원과 정확한 기관명 매칭 시에만 상태 테이블 연결 |
| 국가교통정보센터 표준 노드·링크 | [ITS 표준노드링크](https://www.its.go.kr/nodelink/nodelinkRef) | TODO: 파일 기준일자/버전 | 국토교통부·국가교통정보센터 | 파일 조회/다운로드 절차 확인 TODO | TODO: 별도 키 필요 여부 확인 | 페이지에 파일 데이터와 제공기간은 확인. 실제 파일 fixture 없음 | 아니오 | 기준일자별 파일. 배포 주기 TODO | 없음 | 노드·링크·회전·중용 정보가 파일로 제공됨 |
| 국토교통부_교통소통정보 | [공공데이터포털](https://www.data.go.kr/data/15040463/openapi.do) | `15040463` | 국토교통부 | ITS Open API 신청/키 절차 확인 TODO | `MOLIT_TRAFFIC_API_KEY`, `MOLIT_TRAFFIC_BASE_URL` | 공식 ITS 오픈데이터 페이지에서 XML 응답 예시는 확인. 테스트 fixture 미등록 | raw client만 구현, parser 미구현 | 포털에 실시간 표시 | 없음 | endpoint base URL과 실제 응답 샘플이 확보될 때까지 호출 기능은 503으로 닫힘 |
| 네이버 지도 Directions 5 | [공식 Directions 문서](https://api.ncloud-docs.com/docs/application-maps-directions5) | TODO: 상품/콘솔 서비스 ID | NAVER Cloud Platform | `x-ncp-apigw-api-key-id`, `x-ncp-apigw-api-key` 헤더 | `NAVER_MAP_CLIENT_ID`, `NAVER_MAP_CLIENT_SECRET` | 실제 후보 경로 응답 확인. 저장소 fixture는 `TEST_*` 합성 데이터만 등록 | `summary.distance`/`summary.duration`/`path` parser와 route snapshot 저장 구현 | 요청 시 실시간 교통 반영 | 2026-07-16 확인 | 추천 실행은 설정된 후보 상한까지만 호출하며, 화면 배치는 최대 10곳·부분 성공을 지원 |
| 네이버 지도 Geocoding | [공식 Geocoding 문서](https://api.ncloud-docs.com/docs/ai-naver-mapsgeocoding-geocode) | TODO: 상품/콘솔 서비스 ID | NAVER Cloud Platform | Directions와 동일한 API Gateway 헤더 | `NAVER_MAP_CLIENT_ID`, `NAVER_MAP_CLIENT_SECRET` | 운영 응답은 저장소에 미등록 | `addresses[0].x/y`와 주소 필드만 검증하는 client/endpoint 구현 | 요청 시 | TODO: 별도 수집 성공 시각 기록 필요 | 채팅 주소 입력에만 사용하며 실패 시 좌표를 추정하지 않음 |

## 확인된 샘플과 구현 순서

AI-Hub 119 페이지에는 `audioPath`, `recordId`, 발화 배열, `urgencyLevel`, `address`, `symptom` 등의 구조가 표시되고 예시 라벨 JSON도 있습니다. AI-Hub 의료 분야 페이지에는 WAV/TXT/JSON 및 라벨링 유형이 표시됩니다. HIRA 기본 목록과 상세 endpoint, NEMC 실시간 endpoint는 인증된 환경에서 HTTP 응답을 확인했지만 실제 운영 payload는 저장소에 복사하지 않았고, fixture에는 합성 `TEST_*` 데이터만 둡니다. ITS는 공개 오픈데이터 소개에 XML 예시가 있고, Naver 공식 문서는 Directions/Geocoding 응답 필드를 제공합니다.

따라서 다음 순서를 지킵니다.

1. 승인·인증 후 민감정보를 제거한 원본 샘플을 `backend/tests/fixtures/` 또는 `speech-ai/tests/fixtures/`에 등록
2. 샘플의 schema version과 source record id 기록
3. parser와 validator를 fixture 기반으로 구현
4. 운영 수집 성공 시각과 raw payload id를 DB에 기록

페이지에서 확인되지 않은 인증·갱신·파일 버전은 TODO로 남겼습니다. 추측한 필드명으로 parser를 완성하지 않습니다.

## NEMC 응급의료기관 목록 확인 기록 (2026-07-16)

동일 데이터셋 `15000563`의 `getEgytListInfoInqire`를 실제 호출한 뒤 다음 필드가 있는
XML 응답을 확인했습니다: `hpid`, `dutyName`, `dutyAddr`, `dutyEmcls`,
`dutyEmclsName`, `dutyTel1`, `dutyTel3`, `wgs84Lat`, `wgs84Lon`.
전국 534건 중 주소가 `충청북도`로 시작하는 21건을 확인했으며, 21건 모두 기존 HIRA
병원과 고유 이름으로 연결됐습니다. 운영 payload는 저장소에 넣지 않고
`raw_ingestion_event`에만 저장하며, 테스트에는 `TEST_*` fixture만 사용합니다.

목록 parser와 동기화는 구현 완료입니다. 실시간 endpoint의 `hv*` 계열 필드에 대한
의료적 의미와 가용병상 변환은 공식 코드표 확보 전이므로 TODO이며 값을 추측하지 않습니다.
