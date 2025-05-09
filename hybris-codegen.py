#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import glob
import shutil

def find_aidl_files_in_directory(directory):
    if not os.path.isdir(directory):
        print(f"Error: Directory '{directory}' not found.")
        return None, None

    aidl_files = glob.glob(os.path.join(directory, '*.aidl'))

    if not aidl_files:
        print(f"Error: No .aidl files found in '{directory}'.")
        return None, None

    return [os.path.basename(file) for file in aidl_files], os.path.abspath(directory)

def find_aidl_files(base_path, service_name):
    service_parts = service_name.split('.')

    # Get the last component of the service name for interfaces path
    last_component = service_parts[-1]

    api_current_dir = os.path.join(
        base_path, last_component,
        'aidl/aidl_api', service_name, 'current'
    )

    service_subpath = os.path.join(*service_parts)
    interfaces_service_path = os.path.join(api_current_dir, service_subpath)

    if not os.path.isdir(interfaces_service_path):
        print(f"Error: Service path '{interfaces_service_path}' not found.")
        return None, None, None

    aidl_files = []
    for file in os.listdir(interfaces_service_path):
        if file.endswith('.aidl'):
            aidl_files.append(os.path.join(service_subpath, file))

    if not aidl_files:
        print(f"Error: No .aidl files found in '{interfaces_service_path}'.")
        return None, None, None

    return aidl_files, api_current_dir, service_name

def run_aidl_command(aidl_files, api_directory, service_name=None):
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
    ]
    cmd.extend(aidl_files)

#    print(f"Executing command in directory: {api_directory}")
#    print(' '.join(cmd))

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
#        print("AIDL command completed successfully.")

        cpp_dir = os.path.join(api_directory, 'cpp')
        include_dir = os.path.join(api_directory, 'include')

        if os.path.exists(cpp_dir):
            cpp_dest = os.path.join(original_dir, 'cpp')
            if os.path.exists(cpp_dest):
                shutil.rmtree(cpp_dest)
            shutil.move(cpp_dir, original_dir)
#            print(f"Moved cpp/ to {original_dir}")

        if os.path.exists(include_dir):
            include_dest = os.path.join(original_dir, 'include')
            if os.path.exists(include_dest):
                shutil.rmtree(include_dest)
            shutil.move(include_dir, original_dir)
#            print(f"Moved include/ to {original_dir}")

        cpp_files = []
        cpp_path = os.path.join(original_dir, 'cpp')

        if service_name:
            # Convert service_name with dots to path with slashes
            service_path = service_name.replace('.', '/')
            search_path = os.path.join(cpp_path, service_path)

            if os.path.exists(search_path):
                for root, _, files in os.walk(search_path):
                    for file in files:
                        if file.endswith('.cpp'):
                            rel_path = os.path.relpath(os.path.join(root, file), cpp_path)
                            cpp_files.append(rel_path)
        else:
            # No service name, just walk the entire cpp directory
            for root, _, files in os.walk(cpp_path):
                for file in files:
                    if file.endswith('.cpp'):
                        rel_path = os.path.relpath(os.path.join(root, file), cpp_path)
                        cpp_files.append(rel_path)
        return True, cpp_files
    except subprocess.CalledProcessError as e:
        print(f"Error: AIDL command failed with exit code {e.returncode}")
        print(f"Error output:\n{e.stderr}")
        return False, None
    except Exception as e:
        print(f"Error: Failed to move or process generated files: {str(e)}")
        return False, None
    finally:
        os.chdir(original_dir)

def main():
    parser = argparse.ArgumentParser(
        description='Generate code for AIDL interfaces'
    )

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-s', '--service',
        help='Service name (e.g., android.hardware.vibrator)'
    )
    input_group.add_argument(
        '-d', '--directory',
        help='Directory containing AIDL files to process directly'
    )
    parser.add_argument(
        '-p', '--path',
        help='Base path for searching (default: aidl/interfaces)'
    )

    args = parser.parse_args()

    if args.path:
        base_path = args.path
    else:
        base_path = os.path.join(os.getcwd(), 'aidl/interfaces')

    if args.service and not os.path.isdir(base_path):
        print(f"Error: Base path '{base_path}' not found.")
        sys.exit(1)

    if args.directory:
        aidl_files, api_directory = find_aidl_files_in_directory(args.directory)
        if not aidl_files:
            sys.exit(1)
        service_name = None
    else:
        aidl_files, api_directory, service_name = find_aidl_files(base_path, args.service)
        if not aidl_files:
            sys.exit(1)

    success, cpp_files = run_aidl_command(aidl_files, api_directory, service_name)

    if not success:
        sys.exit(1)

    if cpp_files:
#        print("\nGenerated CPP files:")
        for file in cpp_files:
            print(f"cpp/{file}")

    sys.exit(0)

if __name__ == "__main__":
    main()
