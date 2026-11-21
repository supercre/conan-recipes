cmake_minimum_required(VERSION 3.15)
project(lua_cjson_consumer C)
find_package(lua-cjson CONFIG REQUIRED)
# 소비자 호스트에 이미 있는 LuaJIT로 정적 라이브러리의 ABI와 실행을 검증한다.
find_package(PkgConfig REQUIRED)
pkg_check_modules(LUAJIT REQUIRED IMPORTED_TARGET luajit)
add_executable(test_package test_package.c)
target_link_libraries(test_package PRIVATE lua-cjson::lua-cjson PkgConfig::LUAJIT)
