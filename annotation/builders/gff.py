# TODO handle multipe parents when linking
from __future__ import absolute_import

import logging

from annotation import models
from annotation.builders.core import Builder as BuilderBase
from annotation.builders.linker import Linker as LinkerBase


log = logging.getLogger(__name__)


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


class Builder(BuilderBase):

    Linker = Linker

    def add_decoder(self, decode_fn, types):
        def fn(record):
            if record.type in types:
                return decode_fn(record)
        self.transform.append(fn)

    def add_linker(self, *args, **kwargs):
        linker = self.Linker(*args, **kwargs)
        self.add_handler(linker)


class CodingSequenceHandler(object):

    class NotResolved(Exception): pass

    def __init__(self, CodingSequence, types, Transcript):
        self.CodingSequence = CodingSequence
        self.types = types
        self.Transcript = Transcript
        self.transcripts = {}
        self.deferred = []

    def CodingSequence_from_GFF(self, record):
        return self.CodingSequence(record.start, record.end)

    def transform(self, record):
        if record.type in self.types:
            try:
                self.resolve(record)
            except self.NotResolved:
                self.deferred.append(record)

    def post_transform(self, node, record):
        if isinstance(node, self.Transcript):
            self.transcripts[node.ID] = node

            for record in self.deferred:
                try:
                    self.resolve(record)
                    self.deferred.remove(record)
                except self.NotResolved:
                    pass

    def resolve(self, record):
        parent_ID = record.parent_ID
        try:
            transcript = self.transcripts[parent_ID]
        except KeyError:
            raise self.NotResolved()
        else:
            if not transcript.coding_sequence:
                cds = self.CodingSequence_from_GFF(record)
                cds.transcript = transcript
            else:
                cds = transcript.coding_sequence
                cds.start = min(cds.start, record.start)
                cds.end = max(cds.end, record.end)

    def finalize(self):
        for record in self.deferred:
            try:
                self.resolve(record)
            except self.NotResolved:
                log.warning('Never resolved: {}'.format(record))


class Reader(object):

    Reference_types = {
        'reference',
        'chromosome',
        'contig',
    }

    Gene_types = {
        'gene',
        'pseudogene',
        'transposable_element_gene',
    }

    Transcript_types = {
        'mRNA',
        'snRNA', 
        'rRNA',
        'snoRNA',
        'mRNA_TE_gene',
        'miRNA',
        'tRNA',
        'ncRNA',
        'pseudogenic_transcript',
    }

    Exon_types = {
        'exon',
        'pseudogenic_exon',
    }

    CodingSequence_types = {'CDS'}

    Reference = models.Reference
    Gene = models.Gene
    Transcript = models.Transcript
    Exon = models.Exon
    CodingSequence = models.CodingSequence

    Builder = Builder
    CodingSequenceHandler = CodingSequenceHandler

    def Reference_from_GFF(self, record):
        return self.Reference(record.ID, record.end)

    def Gene_from_GFF(self, record):
        return self.Gene(record.ID, record.strand)

    def Transcript_from_GFF(self, record):
        return self.Transcript(record.ID)

    def Exon_from_GFF(self, record):
        return self.Exon(record.start, record.end)

    def GFF_reference_ID(self, feature, record):
        return record.parent_ID or record.seqid

    def _init_builder(self, builder):
        builder.add_decoder(self.Reference_from_GFF, self.Reference_types)
        builder.add_decoder(self.Gene_from_GFF, self.Gene_types)
        builder.add_decoder(self.Transcript_from_GFF, self.Transcript_types)
        builder.add_decoder(self.Exon_from_GFF, self.Exon_types)

        builder.add_linker(self.Reference, self.Gene, 'reference',
                           self.GFF_reference_ID)
        builder.add_linker(self.Gene, self.Transcript, 'gene')
        builder.add_linker(self.Transcript, self.Exon, 'transcript')

        cds_handler = self.CodingSequenceHandler(self.CodingSequence,
                                                 self.CodingSequence_types,
                                                 self.Transcript)
        builder.add_handler(cds_handler)

    def read(self, records):
        builder = self.Builder()
        self._init_builder(builder)

        references = []
        def collect_references(node, record):
            if isinstance(node, self.Reference):
                references.append(node)

        builder.post_transform.append(collect_references)

        builder.build(records)
        return references
