cmake_minimum_required(VERSION 3.16)

project(CIM-TP1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

include(FetchContent)

FetchContent_Declare(
    argparse
    GIT_REPOSITORY https://github.com/p-ranav/argparse.git
    GIT_TAG v3.2
)

FetchContent_MakeAvailable(argparse)

add_executable(CIM-TP1
    src/main.cpp
    src/generator.cpp
    src/io.cpp
    src/neighbors.cpp
)

target_include_directories(CIM-TP1 PRIVATE src)
target_link_libraries(CIM-TP1 PRIVATE argparse)
