import datetime
import hashlib
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, List, Self

import anytree


def _to_bytes(item: Union[int, float, str]) -> bytes:
    if isinstance(item, int):
        return item.to_bytes(math.ceil(item.bit_length() / 8), byteorder='little')
    elif isinstance(item, float):
        return struct.pack('<d', item)
    elif isinstance(item, str):
        return item.encode()
    assert False, f'Unsupported type of {type(item)}.'


def _calc_hash(data_list: List[bytes]) -> bytes:
    return hashlib.sha256(b'\0'.join(data_list)).digest()


@dataclass
class FileTreeNode(anytree.Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FileNode(FileTreeNode):
    @dataclass
    class FileSigInfo:
        size: int
        modified_time: float

        def __hash__(self):
            return hash((self.size, self.modified_time))

        @classmethod
        def from_file(cls, file: Path):
            stat = file.stat()
            return cls(stat.st_size, stat.st_mtime)

    def __init__(self, sig_info, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sig_info = sig_info
        self.__sig = None

    @property
    def info_message(self) -> str:
        return f'{self.sig_info.size}B, {datetime.datetime.fromtimestamp(self.sig_info.modified_time)}'

    @property
    def sig(self) -> bytes:
        if self.__sig is None:
            # The reason for using str(x) is to ensure the accuracy of \0 as a delimiter.
            self.__sig = _calc_hash([_to_bytes(str(self.sig_info.size)), _to_bytes(str(self.sig_info.modified_time))])
        return self.__sig

    @sig.setter
    def sig(self, value: bytes):
        self.__sig = value

    @property
    def sig_name(self):
        return self.sig, self.name

    def to_dict(self):
        return {
            'name': self.name,
            'sig': self.sig.hex(),
            'sig_info': (self.sig_info.size, self.sig_info.modified_time),
            'type': 'file',
        }

    @classmethod
    def from_dict(cls, data: dict, parent: Optional[FileTreeNode]) -> Self:
        assert data['type'] == 'file'
        result = FileNode(name=data['name'], sig_info=FileNode.FileSigInfo(*data['sig_info']), parent=parent)
        result.sig = bytes.fromhex(data['sig'])
        return result


class EntryNode(FileTreeNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__sig = None
        self.__sig_name = None

    @property
    def sig(self) -> bytes:
        if self.__sig is None:
            self.__sig = _calc_hash([n.sig for n in self.children])
        return self.__sig

    @sig.setter
    def sig(self, value: bytes):
        self.__sig = value

    @property
    def sig_name(self):
        if self.__sig_name is None:
            self.__sig_name = _calc_hash([n.sig_name for n in self.children]), self.name
        return self.__sig_name

    def to_dict(self):
        return {
            'name': self.name,
            'sig': self.sig.hex(),
            'type': 'entry',
            'children': [n.to_dict() for n in self.children],
        }

    @classmethod
    def from_dict(cls, data: dict, parent: Optional[FileTreeNode]) -> Self:
        assert data['type'] == 'entry'
        result = EntryNode(name=data['name'], parent=parent)
        result.sig = bytes.fromhex(data['sig'])
        for d in data['children']:
            if d['type'] == 'file':
                FileNode.from_dict(d, parent=result)
            elif d['type'] == 'entry':
                EntryNode.from_dict(d, parent=result)
        return result


class FileTree:
    def __init__(self, root: EntryNode):
        self.root = root

    def dump(self):
        for pre, _, node in anytree.RenderTree(self.root):
            if isinstance(node, FileNode):
                info = f' <{node.info_message}>'
            else:
                info = ''
            print(f'{pre}[{node.sig.hex()[:8]}]{node.name}{info}')

    def to_dict(self) -> dict:
        return self.root.to_dict()

    @classmethod
    def from_dict(cls, data: dict):
        return FileTree(EntryNode.from_dict(data, parent=None))


def gen_file_tree(path: Path) -> Optional[FileTree]:
    def _traverse(p: Path, parent: Optional[FileTreeNode] = None) -> Optional[FileTreeNode]:
        node = None
        if p.is_file():
            node = FileNode(name=p.name, sig_info=FileNode.FileSigInfo.from_file(p), parent=parent)
        elif p.is_dir():
            node = EntryNode(name=p.name, parent=parent)
            for sub_p in p.iterdir():
                _traverse(sub_p, node)
        else:
            print('Ignore', p)
        return node
    root = _traverse(path)
    if isinstance(root, EntryNode):
        _ = root.sig  # Do sig calc
        return FileTree(root)
    else:
        return None
