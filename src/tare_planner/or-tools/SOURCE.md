# Vendored OR-Tools

This directory contains the `include`, `lib`, `bin`, and `share` directories
from the official **9.8.3296 / Linux x86_64 / Ubuntu 22.04** C++ release.
It was downloaded and built against on Ubuntu 24.04 / ROS 2 Jazzy during
the CMU simulation validation on 2026-09-14.

- Archive: https://github.com/google/or-tools/releases/download/v9.8/or-tools_amd64_ubuntu-22.04_cpp_v9.8.3296.tar.gz
- Archive SHA256: `2a332e95897ac6fc2cfd0122bcbc07cfd286d0f579111529cc99ac3076f5421a`
- Release notes: https://github.com/google/or-tools/releases/tag/v9.8
- Protobuf: 25.0; Abseil: 20230802.1 (dependencies of this release).

The build uses `ortools::ortools` from this release's CMake config. Linking
only the shared object drops dependencies needed by `mutable_time_limit()`
in the directed HT route solver. Keep the headers, libraries, CMake files,
and imported executables from the same release together. Preserve symlinks.

This binary distribution is for x86_64. ARM requires a matching ARM release;
this validation does not establish ARM compatibility.
