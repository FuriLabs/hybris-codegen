#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import shutil

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Generate code for AIDL interfaces'
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '-s', '--service',
        help='Service name (e.g., android.hardware.vibrator)'
    )
    group.add_argument(
        '-d', '--directory',
        help='Directory containing AIDL files to process directly'
    )
    parser.add_argument(
        '-p', '--path',
        help='Base path for searching (default: aidl/interfaces)'
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
    last  = parts[-1]

    api_current = os.path.join(
        base_path, last,
        'aidl/aidl_api', service_name, 'current'
    )
    subpath = os.path.join(*parts)
    svc_dir = os.path.join(api_current, subpath)

    if not os.path.isdir(svc_dir):
        print(f"Error: Service path '{svc_dir}' not found.")
        return None, None, None

    aidl_files = [
        os.path.join(subpath, f)
        for f in os.listdir(svc_dir)
        if f.endswith('.aidl')
    ]
    if not aidl_files:
        print(f"Error: No .aidl files found in '{svc_dir}'.")
        return None, None, None

    return aidl_files, api_current, service_name

def cleanup_leftovers(api_directory):
    for subdir in ('cpp', 'include'):
        path = os.path.join(api_directory, subdir)
        if os.path.exists(path):
            shutil.rmtree(path)

def generate_code(aidl_files, api_directory, service_name=None):
    original_dir = os.getcwd()
    os.chdir(api_directory)

    cmd = [
        'aidl',
        '--lang=ndk',
        '--stability=vintf',
        '--structured',
        '--out=cpp/',
        '--header_out=include/',
        '-I.'
    ] + aidl_files

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Move generated output back to original directory
        for subdir in ('cpp', 'include'):
            src = os.path.join(api_directory, subdir)
            dst = os.path.join(original_dir, subdir)
            if os.path.exists(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)

        # Collect generated .cpp files
        cpp_root = os.path.join(original_dir, 'cpp')
        cpp_files = []
        if service_name:
            svc_path = service_name.replace('.', '/')
            search = os.path.join(cpp_root, svc_path)
            iterator = os.walk(search) if os.path.isdir(search) else []
        else:
            iterator = os.walk(cpp_root)

        for root, _, files in iterator:
            for f in files:
                if f.endswith('.cpp'):
                    rel = os.path.relpath(os.path.join(root, f), cpp_root)
                    cpp_files.append(rel)

        return True, cpp_files

    except subprocess.CalledProcessError as e:
        cleanup_leftovers(api_directory)
        print(f"Error: AIDL command failed (exit {e.returncode})\n{e.stderr}")
        return False, None

    except Exception as e:
        cleanup_leftovers(api_directory)
        print(f"Error: {e}")
        return False, None

    finally:
        os.chdir(original_dir)

def service_flow(service, base_path):
    aidl_files, api_dir, svc = collect_aidl_files_by_service(base_path, service)
    if not aidl_files:
        return False, None
    return generate_code(aidl_files, api_dir, svc)

def directory_flow(directory):
    aidl_files, api_dir = collect_aidl_files_in_directory(directory)
    if not aidl_files:
        return False, None
    return generate_code(aidl_files, api_dir)

def main():
    args      = parse_arguments()
    base_path = get_base_path(args.path)

    if args.service and not os.path.isdir(base_path):
        print(f"Error: Base path '{base_path}' not found.")
        sys.exit(1)

    if args.directory:
        success, cpp_files = directory_flow(args.directory)
    else:
        success, cpp_files = service_flow(args.service, base_path)

    if not success:
        sys.exit(1)

    for f in cpp_files:
        print(f"cpp/{f}")

    sys.exit(0)

if __name__ == "__main__":
    main()

