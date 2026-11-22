"""UC-02 Autenticar: valida e-mail e senha e emite o token de acesso."""

from raizes.application.errors import AuthenticationError
from raizes.application.ports.security import IssuedToken, PasswordHasher, TokenService
from raizes.application.ports.users import UserRepository
from raizes.application.principal import Principal

MENSAGEM_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."


class Login:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        dummy_hash: str | None = None,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        # Hash fictício verificado quando o usuário não existe: iguala o tempo de resposta
        # e evita enumeração de e-mails por medição de tempo. A composição pode reaproveitá-lo.
        self._dummy_hash = dummy_hash or hasher.hash("senha-ficticia-para-igualar-tempo")

    def execute(self, email: str, password: str) -> IssuedToken:
        credentials = self._users.get_credentials_by_email(email)
        if credentials is None:
            self._hasher.verify(password, self._dummy_hash)
            raise AuthenticationError(MENSAGEM_CREDENCIAIS_INVALIDAS)
        password_ok = self._hasher.verify(password, credentials.password_hash)
        if not credentials.is_active or not password_ok:
            raise AuthenticationError(MENSAGEM_CREDENCIAIS_INVALIDAS)
        return self._tokens.issue(
            Principal(credentials.user_id, credentials.role, credentials.unit_id)
        )
