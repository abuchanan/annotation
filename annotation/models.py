from __future__ import absolute_import

from interval.closed import Interval
from more_itertools import pairwise

import sequence_utils

from annotation import sequences
from annotation.builders.gff import DefaultGFFBuilder


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


class PositionHelpers(object):
    '''Some basic helpers for genomic positions.'''

    @property
    def five_prime(self):
        return self.end if self.strand == '-' else self.start

    @property
    def three_prime(self):
        return self.start if self.strand == '-' else self.end


# TODO Region should have a reference
class Region(Interval, PositionHelpers, sequences.RegionSequencesMixin): pass

class Reference(TreeNode, sequences.ReferenceSequencesMixin):
    '''Model representing a reference feature, e.g. a chromosome.'''

    def __init__(self, name, size):
        super(Reference, self).__init__()
        self.name = name
        self.size = size

    @classmethod
    def from_GFF(cls, record):
        return cls(record.ID, record.end)


class Gene(Region, TreeNode):
    '''Model representing a gene feature.'''

    def __init__(self, strand):
        TreeNode.__init__(self)
        self.strand = strand

    @classmethod
    def from_GFF(cls, record):
        return cls(record.strand)

    @property
    def start(self):
        return min(t.start for t in self.transcripts)

    @property
    def end(self):
        return max(t.end for t in self.transcripts)


class Intron(Region, TreeNode):

    def __init__(self, start, end, transcript):
        TreeNode.__init__(self)
        Region.__init__(self, start, end)
        self.transcript = transcript

    @property
    def strand(self):
        return self.transcript.strand

    @property
    def reference(self):
        return self.transcript.gene.reference

    @property
    def donor(self):
        return self.five_prime

    @property
    def acceptor(self):
        return self.three_prime

    def __repr__(self):
        return 'Intron({}, {}, {})'.format(self.start, self.end, self.transcript)


class Transcript(TreeNode, sequences.TranscriptSequencesMixin):

    Intron = Intron

    @classmethod
    def from_GFF(cls, record):
        return cls()

    @property
    def strand(self):
        return self.gene.strand

    # TODO move this sort of stuff to post_transform?
    @property
    def start(self):
        return min(e.start for e in self.exons)

    @property
    def end(self):
        return max(e.end for e in self.exons)

    @property
    def exons(self):
        reverse = self.strand == '-'
        return sorted(self._exons, key=lambda exon: exon.five_prime,
                      reverse=reverse)

    @property
    def introns(self):
        # TODO
        pass

    def build_introns(self):
        for a, b in pairwise(self.exons):
            if self.strand == '-':
                self.Intron(b.five_prime + 1, a.three_prime - 1, self)
            else:
                self.Intron(a.three_prime + 1, b.five_prime - 1, self)

    @property
    def length(self):
        return sum(exon.length for exon in self.exons)

    def rel_to_abs(self, rel):
        if rel < 1 or rel > self.length:
            # TODO better exception and/or message here
            raise IndexError()

        l = 0
        for exon in self.exons:
            if l <= rel <= l + exon.length:
                if self.strand == '-':
                    return exon.five_prime - (rel - l - 1)
                else:
                    return exon.five_prime + (rel - l - 1)

            l += exon.length


class Exon(Region, TreeNode):

    def __init__(self, start, end):
        TreeNode.__init__(self)
        Region.__init__(self, start, end)
        self.start = start
        self.end = end

    @classmethod
    def from_GFF(cls, record):
        return cls(record.start, record.end)

    @property
    def strand(self):
        return self.transcript.strand

    @property
    def reference(self):
        return self.transcript.gene.reference


class Annotation(TreeNode):
    builder = DefaultGFFBuilder(Reference.from_GFF, Gene.from_GFF,
                                Transcript.from_GFF, Exon.from_GFF)
        
    @classmethod
    def _build_from(cls, build, records, *args, **kwargs):
        anno = cls(*args, **kwargs)
        return build(records, root=anno)
        
    @classmethod
    def from_GFF_records(cls, records, *args, **kwargs):
        return cls._build_from(cls.builder.from_records, records, *args, **kwargs)

    @classmethod
    def from_GFF_file(cls, path, *args, **kwargs):
        return cls._build_from(cls.builder.from_file, path, *args, **kwargs)
