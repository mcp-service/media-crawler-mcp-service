# -*- coding: utf-8 -*-

from __future__ import annotations

import warnings
import uvicorn
from app.api_service import main_asgi
from app.config.settings import global_settings

# Suppress websockets deprecation warnings until uvicorn fully migrates to new API
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="websockets.legacy",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="uvicorn.protocols.websockets.websockets_impl",
)


if __name__ == "__main__":
    uvicorn.run(main_asgi, host="0.0.0.0", port=global_settings.app.port)
