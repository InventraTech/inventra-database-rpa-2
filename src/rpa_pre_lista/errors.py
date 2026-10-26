class RpaError(Exception):
    """Erro esperado de execução; o CLI o mostra sem stack trace."""


class ConfigError(RpaError):
    pass


class AlreadyRunningError(RpaError):
    pass


class TargetWriteError(RpaError):
    """Falha ao gravar uma pré-lista no destino (a transação foi revertida)."""
