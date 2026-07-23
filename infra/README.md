# 인프라

Docker Compose와 PostgreSQL 개발 환경을 관리합니다. 운영 배포에는 비밀 관리, TLS, 네트워크 정책, 백업, 모니터링을 별도로 설계해야 합니다.

Compose 시작 순서는 `postgres healthcheck → migrate → backend healthcheck → frontend`입니다.
`speech-ai`는 `speech` profile에서만 선택 실행됩니다. Frontend 개발 이미지는 Vite를 사용하고,
production target은 `npm ci`와 `vite build` 후 nginx에서 정적 파일을 제공합니다.

저장소의 PostgreSQL 기본 계정은 로컬 개발 전용입니다. 운영에서는 `POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB`를 배포 환경의 비밀 관리 기능으로 설정하고, DB volume의
주기적 백업·복구 시험과 Alembic 적용 전 snapshot을 운영 절차에 포함해야 합니다.
