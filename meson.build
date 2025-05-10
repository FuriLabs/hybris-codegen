project('hybris-codegen', 'cpp',
  version : '1.0',
  default_options : ['warning_level=2']
)

inc_dirs = include_directories(
  'libbinder_ndk_hybris/include_ndk',
  'libbinder_ndk_hybris/include_platform',
  'libbinder_ndk_hybris/include_cpp',
)

hybris_common_dep = declare_dependency(
  link_args: ['-lhybris-common']
)

libbinder = shared_library(
  'binder_ndk_hybris',
  'libbinder_ndk_hybris/binder_ndk_hybris.cpp',
  include_directories: inc_dirs,
  dependencies: hybris_common_dep,
  cpp_args: ['-fpermissive'],
  install: true,
)

inc_install_dir = join_paths(get_option('includedir'), 'binder_ndk')
foreach sub : ['include_ndk', 'include_platform', 'include_cpp']
  install_subdir(
    'libbinder_ndk_hybris/' + sub,
    install_dir: inc_install_dir
  )
endforeach

py_mod_dir = join_paths(get_option('libdir'),
                        'python3/dist-packages/mesonbuild/modules')
install_data(
  'mesonbuild/hybris_codegen.py',
  install_dir: py_mod_dir
)

install_data(
  'hybris-codegen.py',
  install_dir: get_option('bindir'),
  rename: 'hybris-codegen'
)

prefix     = get_option('prefix')
libdir     = get_option('libdir')
includedir = get_option('includedir')

pc = configure_file(
  input:  'data/binder_ndk_hybris.pc.in',
  output: 'binder_ndk_hybris.pc',
  configuration: {
    'prefix':     prefix,
    'libdir':     libdir,
    'includedir': join_paths(includedir, 'binder_ndk'),
    'VERSION':    meson.project_version(),
  }
)
install_data(
  pc,
  install_dir: join_paths(libdir, 'pkgconfig')
)
