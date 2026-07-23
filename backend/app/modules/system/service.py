"""Operational readiness workflow for the dashboard and runbook checks."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.freshness import evaluate_freshness
from app.modules.hospital.models import DataSourceRegistry
from app.modules.system.repository import SystemStatusRepository
from app.modules.system.schemas import (
    DataSourceStatusResponse,
    OperationalReadiness,
    OperationalServiceStatus,
    SystemStatusResponse,
)


class SystemStatusService:
    """Combine database evidence with non-secret configuration flags."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self.repository = SystemStatusRepository(session)
        self.settings = settings or get_settings()

    async def get_status(self) -> SystemStatusResponse:
        """Return feature readiness without making external API calls."""

        counts = await self.repository.load_counts()
        sources = await self.repository.list_data_sources()
        source_map = {row.source_name: row for row in sources}
        hira_configured = bool(self.settings.hira_api_key or self.settings.public_data_api_key)
        nemc_configured = bool(self.settings.nemc_api_key or self.settings.public_data_api_key)
        naver_configured = bool(
            self.settings.naver_map_client_id and self.settings.naver_map_client_secret
        )
        services = {
            "database": OperationalServiceStatus(configured=True, status="ok"),
            "hira": self._service_status(
                hira_configured,
                self._latest_source(source_map, ("hira-hospital-info", "hira-hospital-detail")),
            ),
            "nemc": self._service_status(
                nemc_configured,
                self._latest_source(
                    source_map,
                    ("nemc-emergency-institution-list", "nemc-emergency-medical"),
                ),
            ),
            "nemc_sync_worker": OperationalServiceStatus(
                configured=self.settings.nemc_sync_interval_seconds is not None,
                status=(
                    "configured"
                    if self.settings.nemc_sync_interval_seconds is not None
                    else "not_configured"
                ),
            ),
            "naver_maps": OperationalServiceStatus(
                configured=naver_configured,
                status="configured" if naver_configured else "not_configured",
            ),
            "gemini": OperationalServiceStatus(
                configured=bool(self.settings.gemini_api_key),
                status="configured" if self.settings.gemini_api_key else "not_configured",
            ),
            "speech_ai": OperationalServiceStatus(configured=False, status="not_configured"),
        }
        live_routes = naver_configured
        recommendation_ready = (
            counts.active_policies > 0
            and counts.emergency_institutions > 0
            and live_routes
        )
        warnings: list[str] = []
        if counts.active_policies == 0:
            warnings.append("RECOMMENDATION_POLICY_NOT_CONFIGURED")
        if counts.emergency_institutions_with_departments == 0:
            warnings.append("EMERGENCY_HOSPITAL_DETAIL_DATA_UNAVAILABLE")
        if counts.emergency_institutions_with_realtime < counts.emergency_institutions:
            warnings.append("HOSPITAL_REALTIME_STATUS_PARTIAL")
        if self.settings.nemc_sync_interval_seconds is None:
            warnings.append("NEMC_SYNC_INTERVAL_NOT_CONFIGURED")
        if counts.source_identities_unverified > 0:
            warnings.append("HOSPITAL_SOURCE_IDENTITIES_UNVERIFIED")
        if self.settings.hospital_status_max_age_seconds is None:
            warnings.append("HOSPITAL_STATUS_FRESHNESS_POLICY_NOT_CONFIGURED")
        if self.settings.route_data_max_age_seconds is None:
            warnings.append("ROUTE_FRESHNESS_POLICY_NOT_CONFIGURED")
        warnings.append("SPEECH_AI_NOT_CONFIGURED")
        mode = "operational" if recommendation_ready and not warnings else "limited"
        return SystemStatusResponse(
            generated_at=datetime.now(UTC),
            mode=mode,
            environment=self.settings.environment,
            services=services,
            data=counts,
            readiness=OperationalReadiness(
                chat_intake=True,
                voice_intake=False,
                hospital_candidates=counts.emergency_institutions > 0,
                live_routes=live_routes,
                policy_recommendation=recommendation_ready,
            ),
            warnings=sorted(set(warnings)),
        )

    async def list_data_sources(self) -> list[DataSourceStatusResponse]:
        """Return source collection state with configured freshness thresholds."""

        rows = await self.repository.list_data_sources()
        return [self._to_data_source_status(row) for row in rows]

    def _to_data_source_status(self, row: DataSourceRegistry) -> DataSourceStatusResponse:
        """Compute freshness without inventing a threshold when none is configured."""

        threshold = self._source_threshold(row.source_name)
        freshness = evaluate_freshness(row.last_success_at, threshold)
        status: str = freshness.status
        if row.last_failure_at is not None and (
            row.last_success_at is None or row.last_failure_at > row.last_success_at
        ):
            status = "error"
        return DataSourceStatusResponse(
            source_name=row.source_name,
            dataset_id=row.dataset_id,
            provider_name=row.provider_name,
            enabled=row.enabled,
            schema_version=row.schema_version,
            last_success_at=row.last_success_at,
            last_failure_at=row.last_failure_at,
            last_error=row.last_error,
            status=status,
            age_seconds=(
                int(freshness.age_seconds)
                if freshness.age_seconds is not None
                else None
            ),
            freshness_threshold_seconds=threshold,
            reason=freshness.reason,
        )

    def _source_threshold(self, source_name: str) -> int | None:
        """Map known sources to explicit environment freshness settings."""

        if source_name == "nemc-emergency-medical":
            return self.settings.hospital_status_max_age_seconds
        if source_name == "nemc-emergency-institution-list":
            return self.settings.emergency_institution_data_max_age_seconds
        if source_name.startswith("hira-"):
            return self.settings.hospital_data_max_age_seconds
        return None

    @staticmethod
    def _latest_source(
        sources: dict[str, DataSourceRegistry],
        names: tuple[str, ...],
    ) -> DataSourceRegistry | None:
        """Select the most recently attempted source row for a provider."""

        candidates = [sources[name] for name in names if name in sources]
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda row: max(
                row.last_success_at or datetime.min.replace(tzinfo=UTC),
                row.last_failure_at or datetime.min.replace(tzinfo=UTC),
            ),
        )

    @staticmethod
    def _service_status(
        configured: bool,
        source: DataSourceRegistry | None,
    ) -> OperationalServiceStatus:
        """Describe configuration and latest persisted collection outcome."""

        if not configured:
            return OperationalServiceStatus(configured=False, status="not_configured")
        if source is None:
            return OperationalServiceStatus(configured=True, status="configured")
        failed_last = source.last_failure_at is not None and (
            source.last_success_at is None or source.last_failure_at > source.last_success_at
        )
        return OperationalServiceStatus(
            configured=True,
            status="error" if failed_last else "ready",
            last_success_at=source.last_success_at,
            last_failure_at=source.last_failure_at,
            last_error=source.last_error if failed_last else None,
        )
