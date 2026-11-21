#include <stdio.h>
#include <lua.h>
#include <lauxlib.h>
#include <lualib.h>
#include <lua_cjson.h>

int main(int argc, char **argv)
{
    lua_State *l = luaL_newstate();
    int result;
    if (!l || argc < 2)
        return 1;
    luaL_openlibs(l);
    lua_getglobal(l, "package");
    lua_getfield(l, -1, "preload");
    lua_pushcfunction(l, luaopen_cjson);
    lua_setfield(l, -2, "cjson");
    lua_pushcfunction(l, luaopen_cjson_safe);
    lua_setfield(l, -2, "cjson.safe");
    lua_pop(l, 2);
    if (argc > 2 && luaL_dostring(l, "jit.off()")) {
        fprintf(stderr, "%s\n", lua_tostring(l, -1));
        lua_close(l);
        return 1;
    }
    result = luaL_dofile(l, argv[1]);
    if (result)
        fprintf(stderr, "%s\n", lua_tostring(l, -1));
    lua_close(l);
    return result ? 1 : 0;
}
