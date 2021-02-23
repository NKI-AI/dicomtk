# coding=utf-8
# Copyright (c) Jonas Teuwen
import os
import pathlib


def fast_scandir(dirname):
    """
    Find all folders and subdirectories.

    From: https://stackoverflow.com/a/40347279/576363

    Parameters
    ----------
    dirname : pathlib.Path

    Returns
    -------
    List of paths
    """
    subfolders = [pathlib.Path(f.path) for f in os.scandir(dirname) if f.is_dir()]
    for dirname in list(subfolders):
        subfolders.extend(fast_scandir(dirname))
    return subfolders


def sizeof_fmt(num, suffix="B"):
    # From: https://stackoverflow.com/a/1094933/576363
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"
