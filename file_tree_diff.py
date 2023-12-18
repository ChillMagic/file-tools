from . import new_filecmp as filecmp
from pathlib import Path, PurePath
from typing import List, Optional
from collections import OrderedDict


DumpScan = False

def analyze_dir_diffs(base_dir1: Path, base_dir2: Path, filter_list: Optional[List[str]] = None):
    record_dir1 = []
    record_dir2 = []
    record_diff = []
    def analyze_dir_diffs_base(dir1: Path, dir2: Path):
        pure_path = Path(dir1).relative_to(base_dir1)
        if DumpScan:
            print('Scaning', pure_path)  # Debug
        assert(pure_path == Path(dir2).relative_to(base_dir2))
        pure_path = str(pure_path)
        if filter_list and pure_path in filter_list:
            return
        dcmp = filecmp.dircmp(dir1, dir2)
        if dcmp.left_only:
            record_dir1.append((pure_path, dcmp.left_only))
        if dcmp.right_only:
            record_dir2.append((pure_path, dcmp.right_only))
        if dcmp.diff_files:
            record_diff.append((pure_path, dcmp.diff_files))
        for sub_dcmp in dcmp.subdirs.values():
            analyze_dir_diffs_base(sub_dcmp.left, sub_dcmp.right)

    analyze_dir_diffs_base(base_dir1, base_dir2)
    return record_dir1, record_dir2, record_diff


def do_diff(old_dir: Path, new_dir: Path, filter_list: Optional[List[str]] = None, extra_sig_map: Optional[dict] = None):
    record_old_dir, record_new_dir, record_diff = analyze_dir_diffs(old_dir, new_dir, filter_list)

    def get_sig_map(base_dir: Path, record_list):
        sig_map = {}
        for (dir, file_list) in record_list:
            for file in file_list:
                def _traverse(p):
                    if p.is_dir():
                        for subp in p.iterdir():
                            _traverse(subp)
                    elif p.is_file():
                        sig = (p.stat().st_size, p.stat().st_mtime)
                        if sig not in sig_map:
                            sig_map[sig] = []
                        sig_map[sig].append(p.relative_to(base_dir))
                _traverse(base_dir / dir / file)

        return sig_map

    def print_list(record_list, prefix, filter_set: set = None):
        for (dir, file_list) in record_list:
            for file in file_list:
                path = Path(dir) / file
                if (not filter_set) or (path not in filter_set):
                    print(prefix + str(path) + '\033[0m')

    # Analysis moved
    old_sig_map = get_sig_map(old_dir, record_old_dir)
    new_sig_map = get_sig_map(new_dir, record_new_dir)
    move_record_list = []
    move_record_map = {}
    old_moved = set()
    new_moved = set()
    for sig, paths in old_sig_map.items():
        if sig in new_sig_map:
            old, new = paths, new_sig_map[sig]
            for old_item in old:
                old_moved.add(old_item)
            for new_item in new:
                new_moved.add(new_item)

            move_record_list.append((old, new))
            for old_item in old:
                move_record_map[old_item] = new
        if extra_sig_map and sig in extra_sig_map:
            old, extra = paths, extra_sig_map[sig]
            for old_item in old:
                old_moved.add(old_item)
            move_record_list.append((old, extra))
            for old_item in old:
                move_record_map[old_item] = extra

    filter_old_files = set()
    for (dir, file_list) in record_old_dir:
        dir_path = old_dir / dir
        for file in file_list:
            path = dir_path / file
            if path.is_dir():
                files = []
                def _traverse(p):
                    if p.is_dir():
                        for pp in p.iterdir():
                            _traverse(pp)
                    elif p.is_file():
                        files.append(p)
                _traverse(path)

                move_to_dirs = OrderedDict()
                will_filter_old_files = set()
                for f in files:
                    will_filter_old_files.add(f.relative_to(old_dir))
                    current_dir_path_str = str(f.relative_to(path).parent)
                    current_dir_path_str = '' if current_dir_path_str == '.' else current_dir_path_str
                    if f.relative_to(old_dir) not in move_record_map:
                        continue
                    move_to_list = move_record_map[f.relative_to(old_dir)]
                    if len(move_to_list) == 1:
                        move_to_path_str = str(move_to_list[0].parent)
                        if move_to_path_str.endswith(current_dir_path_str):
                            move_to_dirs[PurePath(move_to_path_str[:len(move_to_path_str)-len(current_dir_path_str)])] = True
                if move_to_dirs:
                    old_moved.add(Path(dir) / file)
                    move_record_list.append(([Path(dir) / file],list(move_to_dirs.keys())))
                    filter_old_files.update(will_filter_old_files)

    print('-' * 100)
    print(f"Only in `{old_dir}`:")
    print_list(record_old_dir, '\033[31m- ', old_moved)
    print('-' * 100)
    print(f"Only in `{new_dir}`:")
    print_list(record_new_dir, '\033[32m+ ', new_moved)
    print('-' * 100)
    print(f"Modified:")
    print_list(record_diff, '\033[33m* ')
    print('-' * 100)
    print(f'Moved:')
    for old, new in move_record_list:
        if isinstance(old, list):
            new_old = []
            for old_item in old:
                if old_item not in filter_old_files:
                    new_old.append(old_item)
            old = new_old
        if not old:
            continue
        if isinstance(old, list) and len(old) == 1:
            old = old[0]
        if isinstance(new, list) and len(new) == 1:
            new = new[0]
        print(f'\033[34mM {old} -> {new}\033[0m')
