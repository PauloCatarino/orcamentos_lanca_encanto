from sqlalchemy.types import TypeDecorator, Integer
from sqlalchemy import event

class TinyInt(TypeDecorator):
    impl = Integer
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return 1 if value else 0
        return 0

    def process_result_value(self, value, dialect):
        if value is not None:
            return bool(value)
        return False