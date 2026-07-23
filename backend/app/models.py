"""Import every SQLAlchemy model so Alembic sees the complete metadata graph."""

from app.modules.hospital import models as hospital_models  # noqa: F401
from app.modules.patient import models as patient_models  # noqa: F401
from app.modules.recommendation import models as recommendation_models  # noqa: F401
from app.modules.routing import models as routing_models  # noqa: F401
