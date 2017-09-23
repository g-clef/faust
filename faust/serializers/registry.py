import sys
from typing import Any, Optional, Tuple, Type, cast
from .codecs import CodecArg, dumps, loads
from ..exceptions import KeyDecodeError, ValueDecodeError
from ..types import K, ModelArg, ModelT, V
from ..types.serializers import RegistryT
from ..utils.compat import want_bytes, want_str
from ..utils.objects import cached_property

__all__ = ['Registry']

IsInstanceArg = Tuple[Type, ...]


class Registry(RegistryT):

    def __init__(self,
                 key_serializer: CodecArg = None,
                 value_serializer: CodecArg = 'json') -> None:
        self.key_serializer = key_serializer
        self.value_serializer = value_serializer

    def loads_key(self,
                  typ: Optional[ModelArg],
                  key: bytes,
                  *,
                  serializer: CodecArg = None) -> K:
        """Deserialize message key.

        Arguments:
            typ: Model to use for deserialization.
            key: Serialized key.

        Keyword Arguments:
            serializer: Codec to use for this value.  If not set
               the default will be used (:attr:`key_serializer`).
        """
        if key is None:
            return key
        serializer = serializer or self.key_serializer
        try:
            if isinstance(key, ModelT):
                k = self._loads_model(cast(Type[ModelT], typ), serializer, key)
            else:
                # assume bytes if no type set.
                k = self.Model._maybe_reconstruct(
                    self._loads(serializer, key))
                if typ is not None:
                    if typ is str:
                        k = want_str(k)
                    elif typ is bytes:
                        k = want_bytes(k)
                    elif not isinstance(k, ModelT):
                        k = typ(k)
            return cast(K, k)
        except MemoryError:
            raise
        except Exception as exc:
            raise KeyDecodeError(
                str(exc)).with_traceback(sys.exc_info()[2]) from exc

    def _loads_model(
            self,
            typ: Type[ModelT],
            default_serializer: CodecArg,
            data: bytes) -> Any:
        data = self._loads(
            typ._options.serializer or default_serializer, data)
        self_cls = self.Model._maybe_namespace(data)
        return self_cls(data) if self_cls else typ(data)

    def _loads(self, serializer: CodecArg, data: bytes) -> Any:
        return loads(serializer, data)

    def loads_value(self,
                    typ: Optional[ModelArg],
                    value: bytes,
                    *,
                    serializer: CodecArg = None) -> Any:
        """Deserialize value.

        Arguments:
            typ: Model to use for deserialization.
            value: Bytestring to deserialize.

        Keyword Arguments:
            serializer: Codec to use for this value.  If not set
               the default will be used (:attr:`value_serializer`).
        """
        if value is None:
            return None
        try:
            serializer = serializer or self.value_serializer
            if isinstance(value, ModelT):
                return self._loads_model(
                    cast(Type[ModelT], typ), serializer, value)
            else:
                # assume bytes if no type set.
                typ = bytes if typ is None else typ
                v = self.Model._maybe_reconstruct(
                    self._loads(serializer, value))
                if typ is not None:
                    if typ is str:
                        return want_str(v)
                    elif typ is bytes:
                        return want_bytes(v)
                    elif not isinstance(v, ModelT):
                        return typ(v)
                return v
        except MemoryError:
            raise
        except Exception as exc:
            raise ValueDecodeError(
                str(exc)).with_traceback(sys.exc_info()[2]) from exc

    def dumps_key(self, key: K,
                  serializer: CodecArg = None,
                  *,
                  skip: IsInstanceArg = (bytes,)) -> Optional[bytes]:
        """Serialize key.

        Arguments:
            key: The key to be serialized.
            serializer: Custom serializer to use if value is not a Model.
        """
        serializer = self.key_serializer
        is_model = False
        if isinstance(key, ModelT):
            is_model = True
            key = cast(ModelT, key)
            serializer = key._options.serializer or serializer
        if serializer and not isinstance(key, skip):
            if is_model:
                return cast(ModelT, key).dumps(serializer=serializer)
            return dumps(serializer, key)
        return want_bytes(cast(bytes, key)) if key is not None else None

    def dumps_value(self, value: V,
                    serializer: CodecArg = None,
                    *,
                    skip: IsInstanceArg = (bytes,)) -> Optional[bytes]:
        """Serialize value.

        Arguments:
            value: The value to be serialized.
            serializer: Custom serializer to use if value is not a Model.
        """
        serializer = serializer or self.value_serializer
        is_model = False
        if isinstance(value, ModelT):
            is_model = True
            value = cast(ModelT, value)
            serializer = value._options.serializer or serializer
        if serializer and not isinstance(value, skip):
            if is_model:
                return cast(ModelT, value).dumps(serializer=serializer)
            return dumps(serializer, value)
        return cast(bytes, value)

    @cached_property
    def Model(self) -> Type[ModelT]:
        from ..models.base import Model
        return Model


__flake8_Any_is_really_used: Any  # XXX flake8 bug
