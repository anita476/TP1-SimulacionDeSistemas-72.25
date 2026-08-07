cmake_minimum_required(VERSION 3.16)

project(CIM-TP1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

include(FetchContent)

FetchContent_Declare(
    argparse
    GIT_REPOSITORY https://github.com/p-ranav/argparse.git
    GIT_TAG v3.2
)

FetchContent_MakeAvailable(argparse)

add_executable(CIM-TP1
    src/main.cpp
)

target_link_libraries(CIM-TP1 PRIVATE argparse)