# Frontend

React + TypeScript + Vite 기반 초기 화면입니다. 실제 백엔드·Naver Maps 설정이 없으면 환자 대기, API 미설정, 지도 API 미설정, 추천 결과 없음 상태를 표시하고 임의 병원 마커나 추천 결과를 생성하지 않습니다.

환경변수:

- `VITE_API_BASE_URL`
- `VITE_NAVER_MAP_CLIENT_ID`

증상 자유 입력은 백엔드의 Gemini 보조 추출 API를 호출합니다. Gemini 오류가 발생하면 입력 원문을 `CHAT_SYMPTOM`으로 보존하고 사람 확인 흐름을 계속합니다. 모델 결과로 진단이나 추천을 자동 확정하지 않습니다.
