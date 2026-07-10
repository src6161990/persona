"""환경 설정.

값이 담기는 곳을 두 갈래로 나눈다 (혼동 방지 규칙):

- **우리 코드가 읽는 값 → `Settings`(타입)**: model_provider / model_name / max_tokens / databricks_*.
  타입·기본값·검증이 필요한 설정.
- **SDK가 관례로 읽는 값 → `os.environ`(load_dotenv)**: ANTHROPIC_API_KEY / AZURE_OPENAI_* / OPENAI_* 등.
  langchain 통합(init_chat_model 등)이 환경변수에서 직접 읽으므로 별도 필드 없이 동작한다.

`load_dotenv()` 는 `.env` 를 os.environ 으로 주입해 위 두 번째 갈래(SDK)가 값을 찾게 하는 부트스트랩이다.

원칙: 사용하는 **모델/프로바이더는 코드 수정 없이 `.env`(PERSONA_MODEL_PROVIDER / PERSONA_MODEL_NAME)만으로 교체**한다.
프로바이더 이름을 로직에 하드코딩하지 않는다. (프로바이더별 필수값 검증도 model_provider 의 '선언적 표'로 처리)
"""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# langchain-anthropic 은 os.environ 에서 ANTHROPIC_API_KEY 를 읽으므로
# 설정 로드 전에 .env 를 환경 변수로 주입한다.
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Claude 호출용 API 키 (프로바이더가 anthropic 일 때 사용)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    # LLM 프로바이더 (기본: databricks). 교체는 .env 만 바꾸면 됨 (anthropic / openai / azure_openai ...)
    model_provider: str = Field(default="databricks", alias="PERSONA_MODEL_PROVIDER")
    # 사용할 모델 = Databricks serving endpoint 이름 (프로바이더가 databricks 일 때)
    model_name: str = Field(default="databricks-claude-opus-4-6", alias="PERSONA_MODEL_NAME")
    # 모델 최대 출력 토큰 수
    max_tokens: int = Field(default=16000, alias="PERSONA_MAX_TOKENS")

    # Databricks (PERSONA_MODEL_PROVIDER=databricks 일 때 사용). serving endpoint 는 model_name 으로 지정.
    databricks_workspace_url: str = Field(default="", alias="DATABRICKS_WORKSPACE_URL")
    databricks_client_id: str = Field(default="", alias="DATABRICKS_CLIENT_ID")
    databricks_client_secret: str = Field(default="", alias="DATABRICKS_CLIENT_SECRET")

    # Azure OpenAI / OpenAI 자격증명은 LangChain 통합(init_chat_model)이 os.environ 에서 직접 읽는다
    # (AZURE_OPENAI_API_KEY / AZURE_OPENAI_ENDPOINT / OPENAI_API_VERSION / OPENAI_API_KEY).
    # load_dotenv() 로 .env 가 주입되므로 별도 필드 없이 동작한다.


@lru_cache
def get_settings() -> Settings:
    return Settings()
