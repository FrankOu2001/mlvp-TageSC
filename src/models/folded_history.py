from collections import namedtuple

__all__ = ['FoldedHistory']

FoldedHistory = namedtuple("FoldedHistory", ['idx_fh', 'tag_fh', 'all_tag_fh'])