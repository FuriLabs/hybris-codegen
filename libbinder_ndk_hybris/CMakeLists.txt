add_library(binder_ndk_hybris OBJECT binder_ndk_hybris.cpp)

target_include_directories(binder_ndk_hybris PUBLIC
    include_ndk/
    include_platform/
    include_cpp/
)

target_compile_options(binder_ndk_hybris PRIVATE
    # Workaround HYBRIS_DLSYSM() macro forcing (void *) cast from android_dlsym()
    -fpermissive
)

target_link_libraries(binder_ndk_hybris PRIVATE
    # Note: no pkg-config, for some reason.
    hybris-common
)
