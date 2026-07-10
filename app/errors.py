"""도메인 예외. API 계층에서 HTTP 상태로 매핑한다."""


class PersonaNotFound(Exception):
    """해당 user_id 의 페르소나가 없음 (404)."""


class CharacterNotFound(Exception):
    """해당 user_id 의 캐릭터가 없음 (404). 먼저 생성해야 함."""


class EmptyBuildInput(Exception):
    """페르소나 구축 입력이 비어 있음 (400)."""
