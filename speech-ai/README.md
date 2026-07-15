# Speech AI

AI-Hub 음성 데이터 전처리, STT, 증상·의식·호흡·출혈·위치·긴급도 추출을 담당하는 경계입니다.

현재는 실제 모델과 음성 데이터를 포함하지 않습니다. `PatientEvent`를 생성하는 provider를 구현한 뒤 `BackendClient`로 백엔드 계약을 호출합니다. 테스트 음성/전사 데이터는 `tests/fixtures/`에서만 관리합니다.

