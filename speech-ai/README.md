# Speech AI

AI-Hub 음성 데이터 전처리, STT, 증상·의식·호흡·출혈·위치·긴급도 추출을 담당하는 경계입니다.

현재는 실제 모델과 음성 데이터를 포함하지 않습니다. 승인된 provider가 없어도 서비스는 시작되며
`GET /health`는 프로세스 상태, `GET /status`는 누락된 `SPEECH_STT_PROVIDER`와
`SPEECH_ENTITY_EXTRACTOR`를 명확히 반환합니다. provider 미설정 상태에서는 가짜 전사나 환자
이벤트를 만들지 않습니다.

`SpeechPipeline`은 파일 존재 여부, 허용 확장자, 최대 크기, 선택적 데이터 루트 경계를 먼저
검증하고 빈 전사 결과를 차단합니다. 승인된 extractor가 `PatientEvent`를 만든 뒤
`BackendClient`가 `Idempotency-Key`와 bounded retry로 백엔드에 전달합니다. transcript와 환자
내용은 기본 로그에 출력하지 않습니다.

```powershell
pip install -e ".[dev]"
uvicorn app.main:app --port 8100
python -m pytest tests
```

테스트 음성/전사 데이터는 `tests/fixtures/`에서만 관리합니다.
