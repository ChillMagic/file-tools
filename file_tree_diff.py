import filecmp
from pathlib import Path
from typing import List, Optional


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


def do_diff(old_dir: Path, new_dir: Path, filter_list: Optional[List[str]] = None):
    record_old_dir, record_new_dir, record_diff = analyze_dir_diffs(old_dir, new_dir, filter_list)

    def print_list(record_list, prefix):
        for (dir, file_list) in record_list:
            for file in file_list:
                print(prefix + str(Path(dir) / file) + '\033[0m')

    print('-' * 100)
    print(f"Only in `{old_dir}`:")
    print_list(record_old_dir, '\033[31m- ')
    print('-' * 100)
    print(f"Only in `{new_dir}`:")
    print_list(record_new_dir, '\033[32m+ ')
    print('-' * 100)
    print(f"Modified:")
    print_list(record_diff, '\033[33m* ')
