class User:
    """Mimics github.NamedUser."""

    def __init__(self, login, user_id):
        self.login = login
        self.id = user_id


class PaginatedList(list):
    """Mimics github.PaginatedList."""

    @property
    def reversed(self):
        copy = self.copy()
        copy.reverse()
        return PaginatedList(copy)

    @property
    def totalCount(self):
        return len(self)
