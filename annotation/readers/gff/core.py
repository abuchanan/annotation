from annotation.linker import Linker as LinkerBase


class Linker(LinkerBase):

    def __init__(self, parent_type, child_type, parent_attr,
                 parent_ID_func=None):

        super(Linker, self).__init__()
        self.parent_type = parent_type
        self.child_type = child_type
        self.parent_attr = parent_attr
        self.parent_ID_func = parent_ID_func

    def _get_ID(self, node, record):
        return node.ID

    def _get_parent_ID(self, node, record):
        if self.parent_ID_func:
            return self.parent_ID_func(node, record)
        else:
            return record.parent_ID

    def _link(self, child, parent):
        setattr(child, self.parent_attr, parent)

    def _index_parent(self, node, record):
        if isinstance(node, self.parent_type):
            super(Linker, self)._index_parent(node, record)

    def _try_link(self, node, record):
        if isinstance(node, self.child_type):
            super(Linker, self)._try_link(node, record)


class Handler(object):
    types = set()