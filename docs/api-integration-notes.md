# API 연계 확인 메모

2026-07-15에 `D:\choongbuk_raw_db\API.txt`의 인증정보를 저장소에 복사하지 않고 프로세스 환경변수로만 사용해 API 응답을 확인했다.

## 확인된 요청 경로

- HIRA 기본목록: `https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList`
  - `ServiceKey`, `pageNo`, `numOfRows`, `sidoCd`, `_type=xml`
  - 충북 코드: `330000`
  - 확인 필드: `ykiho`, `yadmNm`, `addr`, `telno`, `XPos`, `YPos`, `clCd`, `clCdNm`
- HIRA 상세정보: `https://apis.data.go.kr/B551182/MadmDtlInfoService2.8`
  - 기본목록의 `ykiho`를 사용한다.
  - 우선 연계 대상: `getEqpInfo2.8`, `getSpclDiagInfo2.8`, `getSpcSbjtSdrInfo2.8`, `getDgsbjtInfo2.8`, `getDtlInfo2.8`
- 국립중앙의료원 실시간 응급실 정보: `https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEmrrmRltmUsefulSckbdInfoInqire`
  - 확인 필드: `hpid`, `dutyName`, `hvidate` 및 원본 상태 필드
  - 상태 코드 의미는 추측하지 않고 raw payload로 보존한다.
- 네이버 Directions 5: `https://maps.apigw.ntruss.com/map-direction/v1/driving`
  - `start`, `goal`, `option=traoptimal`
  - `summary.distance`는 m, `summary.duration`은 ms이다.
  - 지도용 배치 경로는 화면 후보 최대 10곳까지 조회한다. `NAVER_DIRECTIONS_MAX_CALLS`가 비어 있으면 애플리케이션 상한 없이 provider quota와 429 응답을 따른다.
- 네이버 Geocoding: `https://maps.apigw.ntruss.com/map-geocode/v2/geocode`
  - 채팅 주소 입력을 좌표로 바꿀 때만 호출한다.

## 실제 호출 결과

- HIRA 충북 기본목록: HTTP 200, 페이지 메타데이터와 샘플 파싱 성공
- 국립중앙의료원 실시간 응급실 정보: HTTP 200, 샘플 파싱 성공
- 네이버 Directions: 현재 인증정보로 HTTP 401. 코드에서는 인증오류를 그대로 표시하고 이동시간을 생성하지 않는다.

## 현재 구현 원칙

- 음성 AI는 보류하고 `chat-intake/manual-v1` 환자 이벤트를 사용한다.
- 충북 기본 범위는 `CHUNGBUK_SIDO_CODE=330000`이다.
- 후보 병원 반경은 `CANDIDATE_RADIUS_KM`으로 5~10km 사이에서 설정한다.
- 추천 정책과 가중치가 없으면 후보 병원만 표시하고 순위·점수를 만들지 않는다.
- 운영 API 키, 실병원 seed, 실제 환자 데이터는 저장소에 넣지 않는다.
