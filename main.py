"""로컬 실행 편의 러너.

    uv run python main.py
로 개발 서버를 띄운다. (동등: uv run uvicorn app.main:app --reload)
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
