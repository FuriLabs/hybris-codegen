# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025 Bardia Moshiri <bardia@furilabs.com>

import os
import subprocess
from pathlib import Path
from mesonbuild.mesonlib import MesonException
from mesonbuild.modules import ModuleInfo, ExtensionModule

class HybrisCodegenModule(ExtensionModule):
    INFO = ModuleInfo('hybris_codegen')

    def __init__(self, interpreter):
        super().__init__(interpreter)
        self.methods.update({
            'codegen': self.codegen,
            'include_dir': self.include_dir,
            'cpp_dir': self.cpp_dir,
        })
        self._out_cpp_rel = None
        self._out_inc_rel = None

    def _find_codegen(self):
        r = subprocess.run(['which', 'hybris-codegen'], capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            raise MesonException('Could not find "hybris-codegen" in PATH')
        return r.stdout.strip()

    def codegen(self, state, args, kwargs):
        # Expect exactly one positional: the AIDL directory
        if len(args) != 1:
            raise MesonException('hybris_codegen.codegen() requires exactly one argument: the AIDL directory')
        raw = args[0]

        # Resolve source-tree path
        if hasattr(raw, 'held_object') and hasattr(raw.held_object, 'absolute_path'):
            idl_path = raw.held_object.absolute_path(state.environment.source_dir)
        else:
            idl_path = str(raw)
            if not os.path.isabs(idl_path):
                idl_path = os.path.normpath(os.path.join(state.environment.source_dir, idl_path))
        if not os.path.isdir(idl_path):
            raise MesonException(f'AIDL directory "{idl_path}" does not exist')

        builddir = state.environment.get_build_dir()

        # Output subdirs under builddir/hybris_codegen/{cpp,include}
        self._out_cpp_rel = os.path.join('hybris_codegen', 'cpp')
        self._out_inc_rel = os.path.join('hybris_codegen', 'include')
        out_cpp = os.path.join(builddir, self._out_cpp_rel)
        out_inc = os.path.join(builddir, self._out_inc_rel)
        os.makedirs(out_cpp, exist_ok=True)
        os.makedirs(out_inc, exist_ok=True)

        cg = self._find_codegen()

        # Pull optional stability kwarg
        stability = None
        if 'stability' in kwargs:
            stability = kwargs.get('stability')
            if not stability or not isinstance(stability, str):
                raise MesonException('hybris_codegen.codegen(): stability must be a non-empty string')

        # Build the hybris-codegen command
        cmd = [cg]
        if stability:
            # Pass as --stability=<value>
            cmd.append(f'--stability={stability}')
        cmd += [
            '-d', idl_path,
            '-c', out_cpp,
            '-i', out_inc,
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode != 0:
            raise MesonException(
                f'hybris-codegen failed (exit {p.returncode})\n'
                f'Command: {" ".join(cmd)}\n\n'
                f'stdout:\n{p.stdout}\nstderr:\n{p.stderr}'
            )

        # Parse generated .cpp filenames from stdout
        generated = []
        for line in p.stdout.splitlines():
            line = line.strip()
            if not line.endswith('.cpp'):
                continue
            path = Path(line)
            full = path if path.is_absolute() else Path(out_cpp) / path
            generated.append(str(full))

        if not generated:
            raise MesonException(
                'hybris_codegen: no .cpp files generated\n'
                f'Output:\n{p.stdout}'
            )

        return generated

    def include_dir(self, state, args, kwargs):
        if not self._out_inc_rel:
            raise MesonException('hybris_codegen.include_dir() called before codegen()')
        return self._out_inc_rel

    def cpp_dir(self, state, args, kwargs):
        if not self._out_cpp_rel:
            raise MesonException('hybris_codegen.cpp_dir() called before codegen()')
        return self._out_cpp_rel

def initialize(interpreter):
    return HybrisCodegenModule(interpreter)
