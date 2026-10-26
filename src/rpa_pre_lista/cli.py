"""Ponto de entrada: lê a configuração, liga os adaptadores ao caso de uso e executa."""

import argparse
import logging
from datetime import date

import psycopg
from dotenv import load_dotenv

from .application.import_pre_listas import ImportPreListas
from .config import DbSettings, load_settings
from .errors import RpaError
from .infrastructure.postgres_pre_list_target import PostgresPreListTarget
from .infrastructure.postgres_source import PostgresPreListaSource
from .infrastructure.rejection_report import write_rejections

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_WITH_REJECTIONS = 2

log = logging.getLogger("rpa_pre_lista")


def _connect(db: DbSettings, *, autocommit: bool = False) -> psycopg.Connection:
    return psycopg.connect(
        host=db.host,
        port=db.port,
        dbname=db.name,
        user=db.user,
        password=db.password,
        sslmode=db.sslmode,
        autocommit=autocommit,
    )


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rpa-pre-lista",
        description="Importa as pré-listas do banco do 1º ano para tb_pre_list e tb_pre_list_item.",
    )
    parser.add_argument("--since", type=date.fromisoformat, metavar="AAAA-MM-DD",
                        help="importa só pré-listas desta data em diante")
    parser.add_argument("--limit", type=int, metavar="N", help="processa no máximo N pré-listas")
    parser.add_argument("--dry-run", action="store_true",
                        help="executa tudo e desfaz a gravação no final")
    parser.add_argument("--allow-partial", action="store_true",
                        help="importa a pré-lista mesmo com itens rejeitados")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    load_dotenv()

    try:
        settings = load_settings()
        with (
            _connect(settings.source) as src,
            _connect(settings.target, autocommit=True) as dst,
        ):
            src.read_only = True
            source = PostgresPreListaSource(src, settings.fetch_size)
            target = PostgresPreListTarget(dst, dry_run=args.dry_run)
            use_case = ImportPreListas(
                source, target, allow_partial=args.allow_partial, limit=args.limit
            )
            with target.exclusive_lock():
                summary = use_case.execute(since=args.since)
    except RpaError as exc:
        log.error("%s", exc)
        return EXIT_FAILURE
    except psycopg.OperationalError as exc:
        log.error("Falha de conexão com o banco: %s", exc)
        return EXIT_FAILURE

    report_path = write_rejections(settings.report_dir, summary.rejections)
    log.info("Resumo%s:\n  %s", " (dry-run)" if args.dry_run else "", "\n  ".join(summary.lines()))
    if report_path:
        log.warning("Itens rejeitados listados em %s", report_path)

    if summary.lists_failed:
        return EXIT_FAILURE
    return EXIT_WITH_REJECTIONS if summary.rejections else EXIT_OK
