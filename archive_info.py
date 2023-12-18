import dataclasses
import datetime
import functools
import locale
import re
import shutil
import subprocess
from pathlib import Path, PurePath
from typing import Optional, Union


@dataclasses.dataclass
class ArchiveFileInfo:
    path: PurePath
    st_size: int
    st_mtime: float

    @property
    def name(self) -> str:
        return self.path.name


class ArchiveFileReader:
    _specify_7z_program = None

    @classmethod
    @functools.cache
    def _find_7z_program(cls) -> Path:
        seven_zip = shutil.which('7z') or shutil.which('7za') or shutil.which('7zz')
        return Path(seven_zip) if seven_zip else None

    @classmethod
    def _7z_program(cls) -> Path:
        return cls._specify_7z_program if cls._specify_7z_program else cls._find_7z_program()

    @classmethod
    def specify_7z_program(cls, path: Optional[Union[Path, str, bytes]]):
        cls._specify_7z_program = Path(path) if path else None

    def __init__(self, file: Path):
        self.file = file

    @property
    def filelist(self):
        return self.infolist

    @property
    @functools.cache
    def infolist(self):
        process = subprocess.Popen([self._7z_program(), 'l', '-ba', '-slt', self.file], stdout=subprocess.PIPE)
        output, _ = process.communicate()
        assert process.wait() == 0
        infos = []
        for line in output.splitlines():
            mat = re.match(rb'(\w+) = (.*)', line)
            if mat:
                field_name, value = mat[1].decode(), mat[2].decode(locale.getpreferredencoding())
                if field_name == 'Path':
                    infos.append({})
                current_info = infos[-1]
                if field_name == 'Path':
                    current_info['path'] = PurePath(value)
                elif field_name == 'Size':
                    current_info['st_size'] = int(value)
                elif field_name == 'Attributes':
                    current_info['is_file'] = 'A' in value
                elif field_name == 'Modified':
                    datetime_part, nanoseconds_str = value.split('.')
                    nanoseconds = float('0.' + nanoseconds_str)
                    timestamp = datetime.datetime.fromisoformat(datetime_part).timestamp() + nanoseconds
                    current_info['st_mtime'] = timestamp
        return list(filter(None, map(lambda info: (info.pop('is_file'), ArchiveFileInfo(**info))[1] if info[
            'is_file'] else None, infos)))
