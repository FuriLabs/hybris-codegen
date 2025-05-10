#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import shutil
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate code for AIDL interfaces'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-s', '--service',
                       help='Service name (e.g., android.hardware.vibrator)')
    group.add_argument('-d', '--directory',
                       help='Directory containing AIDL files to process directly')
    parser.add_argument(
        '-p', '--path',
        help='Base path for searching (default: aidl/interfaces)',
    )
    parser.add_argument(
        '-c', '--cpp-out',
        default='cpp',
        help='Directory for generated C++ files (absolute or relative; default: cpp)'
    )
    parser.add_argument(
        '-i', '--include-out',
        default='include',
        help='Directory for generated headers (absolute or relative; default: include)'
    )
    return parser.parse_args()

def get_base_path(path_arg):
    return path_arg if path_arg else os.path.join(os.getcwd(), 'aidl/interfaces')

def collect_aidl_files_in_directory(directory):
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return None, None
    aidl_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith('.aidl'):
                full = os.path.join(root, f)
                rel  = os.path.relpath(full, directory)
                aidl_files.append(rel)
    if not aidl_files:
        print(f"Error: No .aidl files found in '{directory}'.")
        return None, None
    return aidl_files, os.path.abspath(directory)

def collect_aidl_files_by_service(base_path, service_name):
    parts = service_name.split('.')
    last = parts[-1]
    api_current = os.path.join(base_path, last,
                               'aidl/aidl_api', service_name, 'current')
    subpath = os.path.join(*parts)
    svc_dir = os.path.join(api_current, subpath)
    if not os.path.isdir(svc_dir):
        print(f"Error: Service path '{svc_dir}' not found.")
        return None, None, None
    aidl_files = [f for f in os.listdir(svc_dir) if f.endswith('.aidl')]
    if not aidl_files:
        print(f"Error: No .aidl files found in '{svc_dir}'.")
        return None, None, None

    # we want them relative to svc_dir
    aidl_files = [os.path.join(subpath, f) for f in aidl_files]
    return aidl_files, api_current, service_name

def generate_code(aidl_files, api_directory, service_name, cpp_out, include_out):
    cpp_path = Path(cpp_out)
    inc_path = Path(include_out)
    if not cpp_path.is_absolute():
        cpp_path = Path(api_directory) / cpp_path
    if not inc_path.is_absolute():
        inc_path = Path(api_directory) / inc_path

    shutil.rmtree(str(cpp_path), ignore_errors=True)
    shutil.rmtree(str(inc_path), ignore_errors=True)
    cpp_path.mkdir(parents=True, exist_ok=True)
    inc_path.mkdir(parents=True, exist_ok=True)

    cwd = os.getcwd()
    os.chdir(api_directory)
    cmd = [
        'aidl',
        '--lang=ndk',
        '--stability=vintf',
        '--structured',
        f'--out={cpp_path}',
        f'--header_out={inc_path}',
        '-I.',
    ] + aidl_files

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: AIDL command failed (exit {e.returncode})\n{e.stderr}")
        os.chdir(cwd)
        return False, None
    except Exception as e:
        print(f"Error: {e}")
        os.chdir(cwd)
        return False, None
    finally:
        os.chdir(cwd)

    # Walk the generated tree to list all .cpp files
    search_root = cpp_path
    if service_name:
        svc_sub = service_name.replace('.', '/')
        search_root = cpp_path / svc_sub
    if not search_root.exists():
        print(f"Error: Expected output directory '{search_root}' not found.")
        return False, None

    cpp_files = []
    for root, _, files in os.walk(str(search_root)):
        for f in files:
            if f.endswith('.cpp'):
                full = Path(root) / f
                rel = full.relative_to(cpp_path)
                cpp_files.append(str(rel))

    if not cpp_files:
        print(f"Error: No .cpp files generated under '{cpp_path}'.")
        return False, None

    return True, cpp_files

def service_flow(service, base_path, cpp_out, include_out):
    aidl_files, api_dir, svc = collect_aidl_files_by_service(base_path, service)
    if not aidl_files:
        return False, None
    return generate_code(aidl_files, api_dir, svc, cpp_out, include_out)

def directory_flow(directory, cpp_out, include_out):
    aidl_files, api_dir = collect_aidl_files_in_directory(directory)
    if not aidl_files:
        return False, None
    return generate_code(aidl_files, api_dir, None, cpp_out, include_out)

def main():
    args = parse_arguments()
    if args.service:
        base = get_base_path(args.path)
        if not os.path.isdir(base):
            print(f"Error: Base path '{base}' not found.")
            sys.exit(1)
        success, cpp_files = service_flow(args.service,
                                          base,
                                          args.cpp_out,
                                          args.include_out)
    else:
        success, cpp_files = directory_flow(args.directory,
                                            args.cpp_out,
                                            args.include_out)

    if not success:
        sys.exit(1)

    for f in cpp_files:
        print(os.path.join(args.cpp_out, f))

    sys.exit(0)

if __name__ == '__main__':
    main()
