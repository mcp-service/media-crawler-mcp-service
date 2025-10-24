# -*- coding: utf-8 -*-

from __future__ import annotations

import uvicorn

from app.api_service import main_asgi
from app.config.settings import global_settings


if __name__ == "__main__":
    uvicorn.run(main_asgi, host="0.0.0.0", port=global_settings.app.port)
