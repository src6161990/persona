"""Databricks 프로바이더.

Databricks serving endpoint 는 OpenAI 호환이므로, OAuth M2M 토큰을 발급받아
LangChain ``ChatOpenAI`` 를 endpoint 에 연결한다 (경계 타입 BaseChatModel 유지).
"""

import os

import httpx
from langchain_core.language_models.chat_models import BaseChatModel


def get_databricks_token(
    workspace_url: str | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> str:
    """Databricks 워크스페이스에서 OAuth M2M 액세스 토큰을 발급한다."""
    workspace_url = workspace_url or os.environ["DATABRICKS_WORKSPACE_URL"]
    client_id = client_id or os.environ["DATABRICKS_CLIENT_ID"]
    client_secret = client_secret or os.environ["DATABRICKS_CLIENT_SECRET"]
    response = httpx.post(
        f"{workspace_url.rstrip('/')}/oidc/v1/token",
        data={"grant_type": "client_credentials", "scope": "all-apis"},
        auth=(client_id, client_secret),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


class DatabricksModelProvider:
    """serving endpoint(OpenAI 호환)에 연결된 ChatOpenAI 를 제공한다.

    자격증명은 Settings(=.env)에서 주입받는다. 값이 비면 get_databricks_token 이
    os.environ 로 폴백한다.
    """

    def __init__(
        self,
        model: str,
        max_tokens: int,
        workspace_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._model = model
        self._max_tokens = max_tokens
        self._workspace_url = workspace_url
        self._client_id = client_id
        self._client_secret = client_secret

    def get_chat_model(self) -> BaseChatModel:
        from langchain_openai import ChatOpenAI

        workspace_url = self._workspace_url or os.environ["DATABRICKS_WORKSPACE_URL"]
        # 토큰은 호출 시점에 발급 (모델을 캐시하지 않아 만료 대비). 운영에서 짧은 TTL 캐시/401 재발급 고려.
        token = get_databricks_token(
            workspace_url=workspace_url,
            client_id=self._client_id or None,
            client_secret=self._client_secret or None,
        )
        return ChatOpenAI(
            model=self._model,
            api_key=token,
            base_url=f"{workspace_url.rstrip('/')}/serving-endpoints",
            max_tokens=self._max_tokens,
        )
