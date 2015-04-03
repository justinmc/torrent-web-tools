import argparse
import ctypes
import os
from pprint import pprint
import re
import urllib
from bencode import bencode
import time
from hashlib import sha1
from base64 import b32encode


GENERATOR_VERSION = '0.0.1'


def common_path_for_files(file_paths):
    # Note: os.path.commonprefix works on a per-char basis, not per path element
    common_prefix = os.path.commonprefix(file_paths)

    if not os.path.isdir(common_prefix):
        common_prefix = os.path.split(common_prefix)[0]  # break off invalid trailing element of path

    print("Common path prefix: %s" % common_prefix)
    return common_prefix


def relativize_file_path(file_path, common_path):
    return file_path.replace("%s%s" % (common_path.rstrip(os.sep), os.sep), '')


def split_path_components(file_path):
    return file_path.split(os.sep)


def join_path_component_list(path_components_list):
    joined = os.path.join(*path_components_list)
    if path_components_list[0] == '':
        joined = os.sep + joined

    return joined


def collect_child_file_paths(path):
    return [os.path.join(dirpath, filename) for dirpath, dirname, filenames in os.walk(path) for filename in filenames]


def filter_hidden_files(file_paths):
    # If any element of the path starts with a '.' or is hidden, exclude it.

    split_paths = [split_path_components(path) for path in file_paths]
    filtered_paths = [join_path_component_list(split_path) for split_path in split_paths
                      if True not in
                      [os.path.basename(os.path.abspath(element)).startswith('.') or has_hidden_attribute(element)
                      for element in split_path]]

    return filtered_paths


def has_hidden_attribute(filepath):
    try:
        attrs = ctypes.windll.kernel32.GetFileAttributesW(unicode(filepath))
        assert attrs != -1
        result = bool(attrs & 2)
    except (AttributeError, AssertionError):
        result = False
    return result


def sha1_hash_for_generator(gen):
    for data in gen:
        yield sha1(data).digest()


def read_in_pieces(file_paths, piece_length):
    data = ''
    for path in file_paths:
        with open(path, 'rb') as file_handle:
            while True:
                data += file_handle.read(piece_length - len(data))
                if len(data) < piece_length:
                    break
                yield data
                data = ''
    yield data


def hash_pieces_for_file_paths(file_paths, piece_length):
    print("Hashing pieces...")
    return ''.join(sha1_hash_for_generator(read_in_pieces(file_paths, piece_length)))


def build_file_detail_dict(file_path, common_path):
    rel_path = relativize_file_path(file_path, common_path)
    rel_path_components = split_path_components(rel_path)

    return {
        'name': rel_path_components[-1],
        'full_path': file_path,
        'rel_path': rel_path,
        'file_length': os.path.getsize(file_path),
        'rel_path_components': rel_path_components,
    }


def sort_files(file_details):
    # sort files in root of torrent to front
    file_details.sort(key=lambda item: len(item['rel_path_components']))

    # Sort files referenced in index.html to front. This is really naive.
    index_contents = ''
    for item in file_details:
        if len(item['rel_path_components']) == 1 and item['name'] == 'index.html':
            with open(item['full_path'], 'r') as f:
                index_contents = f.read()
            break

    # TODO: Will probably only work on Mac/Linux due to path separator
    if len(index_contents):
        file_details.sort(key=lambda item: html_position_sort(index_contents, item['rel_path']))

    # sort index.html to front
    file_details.sort(key=lambda item: len(item['rel_path_components']) == 1 and item['name'] == 'index.html', reverse=True)

    return file_details


def html_position_sort(in_str, sub_str):
    """Behaves like a normal String.find(), but if not found, returns the length of the in_str"""
    position = in_str.find(sub_str)
    if position < 0:
        position = len(in_str)

    return position


def process_files(file_paths, piece_length, include_hidden, optimize_file_order):
    common_path = common_path_for_files(file_paths)

    # Deal with user specifying directory by collecting all children
    subpaths = []
    dirs = []
    for path in file_paths:
        if os.path.isdir(path):
            subpaths.extend(collect_child_file_paths(path))
            dirs.append(path)
    file_paths.extend(subpaths)
    for directory in dirs:
        file_paths.remove(directory)

    if not include_hidden:
        file_paths = filter_hidden_files(file_paths)

    file_details = [build_file_detail_dict(file_path, common_path) for file_path in file_paths]

    if optimize_file_order:
        file_details = sort_files(file_details)

    pieces = hash_pieces_for_file_paths(file_paths, piece_length)

    return file_details, common_path, pieces


def build_torrent_dict(file_paths, name=None, trackers=None, webseeds=None, piece_length=16384, include_hidden=False,
                       optimize_file_order=True):
    if trackers is None:
        trackers = []

    if webseeds is None:
        webseeds = []

    file_details, common_path, pieces = process_files(file_paths, piece_length, include_hidden, optimize_file_order)

    if name is None:
        if len(file_paths) == 1:
            # Single file mode
            name = os.path.basename(file_paths[0])
        else:
            # Multi file mode
            name = os.path.basename(common_path.rstrip(os.sep))

    torrent_dict = {
        'created by': 'TWT-Gen/%s' % GENERATOR_VERSION,
        'creation date': int(time.time()),
        'encoding': 'UTF-8',

        'info': {
            'name': name,
            'piece length': piece_length,
            'pieces': pieces,
        }
    }

    if len(trackers):
        torrent_dict['announce'] = trackers[0]
        torrent_dict['announce-list'] = [[tracker for tracker in trackers]]

    if len(webseeds):
        torrent_dict['url-list'] = webseeds

    if len(file_paths) == 1:
        # Single file mode
        torrent_dict['info']['length'] = file_details[0]['file_length']
    else:
        # Multi file mode
        torrent_dict['info']['files'] = [{'length': details['file_length'], 'path': details['rel_path_components']}
                                         for details in file_details]

    return torrent_dict


def write_torrent_file(torrent_dict, output_file_path):
    with open(output_file_path, 'wb') as file_handle:
        file_handle.write(bencode(torrent_dict))


def get_info_hash(info_dict):
    return b32encode(sha1(bencode(info_dict)).digest())


def magnet_link_for_info_hash(info_hash, include_tracker=True):
    link_args = {'xt': 'urn:btih:%s' % info_hash}

    if include_tracker and 'announce' in torrent_dict:
        link_args['tr'] = torrent_dict['announce']

    return "magnet:?%s" % urllib.urlencode(link_args)


def browser_link_for_info_hash(info_hash, include_tracker=True):
    link_args = {}

    if include_tracker and 'announce' in torrent_dict:
        link_args['tr'] = torrent_dict['announce']

    return "bittorrent://%s?%s" % (info_hash, urllib.urlencode(link_args))


def warn_if_no_index_html(torrent_dict):
    file_list = [file_item['path'][0] for file_item in torrent_dict['info']['files'] if len(file_item['path']) == 1]
    if 'index.html' not in file_list:
        print("WARNING: No 'index.html' found in root directory of torrent.")


def file_or_dir(string):
    """
    For argparse: Takes a file or directory, makes sure it exists.
    """
    full_path = os.path.abspath(os.path.expandvars(os.path.expanduser(string)))

    if not os.path.exists(full_path):
        raise argparse.ArgumentTypeError("%r is not a file or directory." % string)

    print("Input file: %s" % full_path)
    return full_path


def valid_url(string):
    """
    For argparse: Validate passed url
    """
    regex = re.compile(
        r'^(?:https?|udp)://'  # http://, https://, or udp://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # ...or ipv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if not regex.match(string):
        raise argparse.ArgumentTypeError("%r is not a valid URL" % string)

    return string


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generates torrent files from static website files.')

    parser.add_argument('input', metavar='INPUT', type=file_or_dir, nargs='+',
                        help="One or more files or directories. 'index.html' MUST be present in the torrent for it to "
                             "be viewable in a browser.")
    parser.add_argument('--output', '-o', type=str, required=True,
                        help="REQUIRED: A torrent file to be output.")
    parser.add_argument('--name', type=str, default=None, help="Name of the torrent, not seen in the browser.")

    parser.add_argument('--tracker', type=valid_url, nargs="*", dest='trackers', metavar='TRACKER',
                        help="A tracker to include in the torrent. "
                             "Not including a tracker means that the torrent can only be shared via magnet-link.")
    parser.add_argument('--comment', type=str,
                        help="A description or comment about the torrent. Not seen in the browser.")

    parser.add_argument('--webseed', type=valid_url, nargs='*', dest='webseeds', metavar='URL',
                        help="A URL that contains the files present in the torrent. "
                             "Used if normal BitTorrent seeds are unavailable. "
                             "NOTE: Not compatible with magnet-links, must be used with a tracker.")

    # https://wiki.theory.org/BitTorrentSpecification#Info_Dictionary  <-- contains piece size recommendations
    parser.add_argument('--piece-length', type=int, default=16384, dest='piece_length',
                        help="Number of bytes in each piece of the torrent. "
                             "Smaller piece sizes allow web pages to load more quickly. Larger sizes hash more quickly."
                             " Default: 16384")
    parser.add_argument('--include-hidden-files', action='store_true',
                        help="Includes files whose names begin with a '.', or are marked hidden in the filesystem.")
    parser.add_argument('--no-optimize-file-order', action='store_false', dest='optimize_file_order',
                        help="Disables intelligent reordering of files.")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose mode.")

    args = parser.parse_args()

    torrent_dict = build_torrent_dict(file_paths=args.input,
                                      name=args.name,
                                      trackers=args.trackers,
                                      webseeds=args.webseeds,
                                      piece_length=args.piece_length,
                                      include_hidden=args.include_hidden_files,
                                      optimize_file_order=args.optimize_file_order)
    write_torrent_file(torrent_dict, args.output)

    warn_if_no_index_html(torrent_dict)

    if args.verbose:
        print("Built torrent with data:")
        smaller_dict = {key: value for key, value in torrent_dict.iteritems() if key != 'info'}
        smaller_dict['info'] = {key: value for key, value in torrent_dict['info'].iteritems() if key != 'pieces'}
        smaller_dict['info']['pieces'] = "<SNIP>"
        pprint(smaller_dict)

    info_hash = get_info_hash(torrent_dict['info'])
    if 'announce' in torrent_dict:
        print("Magnet link (with tracker):  %s" % magnet_link_for_info_hash(info_hash, include_tracker=True))

    print("Magnet link (trackerless):   %s" % magnet_link_for_info_hash(info_hash, include_tracker=False))

    if 'announce' in torrent_dict:
        print("Browser link (with tracker): %s" % browser_link_for_info_hash(info_hash, include_tracker=True))

    print("Browser link (trackerless):  %s" % browser_link_for_info_hash(info_hash, include_tracker=False))

    print("Output torrent: %s" % args.output)