import itertools
from pathlib import Path

from file_tools.file_tree_info import EntryNode, FileNode, FileTree


class DirCmp:
    def __init__(self, n1: EntryNode, n2: EntryNode):
        self.left, self.right = n1.full_path, n2.full_path

        def _get_dict(node):
            c = sorted(node.children, key=lambda k: k.name)
            return dict(zip(map(lambda n: n.name, c), c))

        a, b = _get_dict(n1), _get_dict(n2)
        self.common = list(map(a.__getitem__, filter(b.__contains__, a)))
        self.left_only = list(map(lambda n: n.name, map(a.__getitem__, itertools.filterfalse(b.__contains__, a))))
        self.right_only = list(map(lambda n: n.name, map(b.__getitem__, itertools.filterfalse(a.__contains__, b))))

        self.same_files = []
        self.diff_files = []
        for x in self.common:
            aa, bb = a[x.name], b[x.name]
            if isinstance(aa, FileNode) and isinstance(bb, FileNode):
                if aa.sig == bb.sig:
                    self.same_files.append(x.name)
                else:
                    self.diff_files.append(x.name)
        self.same_files.sort()
        self.diff_files.sort()

        self.subdirs = {}
        for x in self.common:
            if isinstance(x, EntryNode):
                self.subdirs[x.name] = self.__class__(n1 / x.name, n2 / x.name)


class FileTreeCmp:
    def __init__(self, t1: FileTree, t2: FileTree, bp1: Path, bp2: Path):
        self.t1, self.t2 = t1, t2
        self.bp1, self.bp2 = bp1, bp2

    def __call__(self, d1: Path, d2: Path) -> DirCmp:
        p1, p2 = d1.relative_to(self.bp1), d2.relative_to(self.bp2)
        return DirCmp(self.t1.root / p1, self.t2.root / p2)
