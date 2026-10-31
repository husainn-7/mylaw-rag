"""Stub the heavy libraries so the tests run without downloading models."""
import sys
import types


class _Unavailable:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("stub: install the real library to use this")


def _stub(name, **attrs):
    try:
        __import__(name)
    except ImportError:
        module = types.ModuleType(name)
        for key, value in attrs.items():
            setattr(module, key, value)
        sys.modules[name] = module


_stub("faiss")
_stub("sentence_transformers", SentenceTransformer=_Unavailable, CrossEncoder=_Unavailable)
