
class Parent(object):
    def __init__(self, Parent_cls, name=None, related_name=None):
        self._name = name
        self.Parent_cls = Parent_cls
        self.related_name = related_name
        self._data = {}

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name
        if not self.related_name:
            self.related_name = name + '_set'

    def __get__(self, obj, cls=None):
        return self._data.get(obj, None)

    def __set__(self, obj, new_parent):
        current_parent = self.__get__(obj)
        if current_parent:
            related_set = getattr(current_parent, self.related_name)
            related_set.remove(obj)

        self._data[obj] = new_parent

        if new_parent:
            # TODO catch missing related attr on parent?
            related_set = getattr(new_parent, self.related_name)
            related_set.add(obj)
