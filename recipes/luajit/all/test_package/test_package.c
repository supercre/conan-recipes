/* 패키지의 정적 라이브러리를 소비자 실행 파일에 연결해 res/tests/compat.lua를 실행한다.
** 두 번째 인자가 --joff면 JIT를 끄고 실행한다. */
#include <stdio.h>
#include <string.h>

#include "lua.h"
#include "lauxlib.h"
#include "lualib.h"
#include "luajit.h"

int main(int argc, char **argv)
{
  lua_State *L = luaL_newstate();
  int status;
  if (L == NULL) {
    fprintf(stderr, "cannot create a Lua state\n");
    return 1;
  }
  luaL_openlibs(L);
  if (argc > 2 && strcmp(argv[2], "--joff") == 0)
    luaJIT_setmode(L, 0, LUAJIT_MODE_ENGINE | LUAJIT_MODE_OFF);
  status = argc > 1 ? luaL_dofile(L, argv[1]) : luaL_dostring(L, "print(jit.version)");
  if (status != 0) {
    fprintf(stderr, "%s\n", lua_tostring(L, -1));
    lua_close(L);
    return 1;
  }
  lua_close(L);
  return 0;
}
