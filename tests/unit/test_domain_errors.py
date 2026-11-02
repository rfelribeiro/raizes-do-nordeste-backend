from raizes.domain.shared.errors import BusinessRuleViolationError, DomainError, NotFoundError


def test_errors_share_domain_base_and_keep_message() -> None:
    for cls in (NotFoundError, BusinessRuleViolationError):
        error = cls("mensagem")
        assert isinstance(error, DomainError)
        assert error.message == "mensagem"
        assert str(error) == "mensagem"
