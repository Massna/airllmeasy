"""Ajusta sys.path para localizar o pacote Python airllm quando instalado fora do interpretador atual."""
from __future__ import annotations

import glob
import platform
import sys
from pathlib import Path
from typing import Optional, Tuple

_last_inserted: Optional[str] = None
_configured_packages_path: Optional[str] = None


def resolve_airllm_site_packages(user_path: str) -> Optional[Path]:
    """
    Converte uma pasta escolhida pelo usuário no diretório site-packages
    onde existe o subpacote 'airllm'.

    Aceita:
    - .../site-packages (com pasta airllm dentro)
    - .../site-packages/airllm (usa o pai)
    - Raiz de um venv (procura Lib/site-packages no Windows ou lib/python*/site-packages no Unix)
    """
    raw = (user_path or "").strip()
    if not raw:
        return None

    p = Path(raw).expanduser().resolve()
    if not p.is_dir():
        return None

    if p.name == "airllm" and p.parent.is_dir():
        parent = p.parent
        if (parent / "airllm").is_dir():
            return parent

    if (p / "airllm").is_dir():
        return p

    if platform.system() == "Windows":
        cand = p / "Lib" / "site-packages"
        if (cand / "airllm").is_dir():
            return cand
    else:
        for lib in p.glob("lib/python*/site-packages"):
            if (lib / "airllm").is_dir():
                return lib
        alt = list(glob.glob(str(p / "lib" / "python*" / "site-packages")))
        for lib in alt:
            lp = Path(lib)
            if (lp / "airllm").is_dir():
                return lp

    return None


def apply_airllm_packages_path(user_path: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Insere no início do sys.path o diretório site-packages onde está o airllm.
    Remove o caminho anterior registrado por esta função.

    Retorna (ok, caminho_resolvido_ou_None).
    """
    global _last_inserted

    if _last_inserted:
        try:
            while _last_inserted in sys.path:
                sys.path.remove(_last_inserted)
        except ValueError:
            pass
        _last_inserted = None

    if not user_path or not str(user_path).strip():
        return False, None

    resolved = resolve_airllm_site_packages(str(user_path))
    if not resolved:
        return False, None

    s = str(resolved)
    if s not in sys.path:
        sys.path.insert(0, s)
    _last_inserted = s
    return True, s


def set_airllm_packages_path(user_path: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Define o caminho salvo e aplica em sys.path (chamar ao iniciar e ao salvar configurações)."""
    global _configured_packages_path
    _configured_packages_path = (user_path or "").strip() or None
    return apply_airllm_packages_path(_configured_packages_path)


def ensure_airllm_path() -> None:
    """Garante que o path configurado está aplicado antes de importar airllm."""
    apply_airllm_packages_path(_configured_packages_path)
