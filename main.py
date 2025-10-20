# -*- coding: utf-8 -*-

from __future__ import annotations

import uvicorn

from app.api_service import create_app
from app.config.settings import global_settings
asgi = create_app()


if __name__ == "__main__":
    uvicorn.run(asgi, host="0.0.0.0", port=global_settings.app.port)
