"""ITS node-link file boundary; file layout is not guessed."""

from pathlib import Path

from app.core.config import get_settings
from app.core.errors import ApplicationError


class NodeLinkClient:
    """Read an approved local node-link file path without parsing it."""

    def __init__(self, data_root: str | None = None) -> None:
        self.data_root = data_root or get_settings().its_node_link_data_root

    def locate_file(self, relative_path: str) -> Path:
        """Return a configured path; a missing root is an explicit configuration error."""

        if not self.data_root:
            raise ApplicationError(
                code="EXTERNAL_SERVICE_NOT_CONFIGURED",
                message="ITS 표준노드링크 데이터 경로가 설정되지 않았습니다.",
                details={"source_name": "its-node-link", "missing_settings": ["NODE_LINK_DATA_ROOT"]},
            )
        return Path(self.data_root) / relative_path
