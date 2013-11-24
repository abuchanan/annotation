from __future__ import absolute_import

from annotation import sequences
from annotation.models import bases


__version__ = '2.0.0'

# TODO drop strand and use a boolean "reversed" or "reverse_strand" instead?


class TreeNode(object):
    '''Dead simple representation of a tree node.

    A tree node has one parent and multiple children.

    When a TreeNode's parent is set, the child is added to the parent's
    children automatically, and likewise if the parent is unset,
    the child is removed from the parent's children.

    Note, this does not (yet) handle the opposite, i.e. if you remove
    a child node from the parent, that child's parent is not unset.
    '''
    def __init__(self):
        self._parent = None
        self.children = []

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        # If this node already has a parent,
        # delete this node from that parent's children
        if self._parent:
            self._parent.children.remove(self)
        self._parent = value
        self._parent.children.append(self)


class Reference(bases.Reference, sequences.ReferenceSequencesMixin):

    @classmethod
    def from_GFF(cls, record):
        return cls(record.ID, record.end)


class Gene(bases.Gene):

    @classmethod
    def from_GFF(cls, record):
        return cls(record.ID, record.strand)

    def GFF_reference_ID(self, record):
        return record.parent_ID or record.seqid


class Transcript(bases.Transcript, sequences.TranscriptSequencesMixin):
    @classmethod
    def from_GFF(cls, record):
        return cls(record.ID)

class Exon(bases.Exon):
    @classmethod
    def from_GFF(cls, record):
        return cls(record.start, record.end)
