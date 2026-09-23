/**
 * SWC Native - TypeScript Compiler C FFI Interface
 *
 * Provides C-compatible functions for compiling TypeScript to JavaScript
 * with source map support using SWC (Speedy Web Compiler).
 *
 * Usage:
 *   SwcCompileResult result = swc_compile_typescript(source, filename);
 *   if (result.success) {
 *       // Use result.code and result.source_map
 *   } else {
 *       // Handle error in result.error
 *   }
 *   swc_free_result(result); // Always free the result
 */

#ifndef SWC_NATIVE_H
#define SWC_NATIVE_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

/**
 * Result structure returned from TypeScript compilation.
 * 
 * All string pointers are heap-allocated and must be freed by calling
 * swc_free_result(). Do not free individual fields manually.
 */
typedef struct SwcCompileResult {
    /** Compiled JavaScript code (null-terminated UTF-8 string) */
    char* code;
    
    /** Source map JSON (null-terminated UTF-8 string) */
    char* source_map;
    
    /** Error message if compilation failed (null-terminated UTF-8 string) */
    char* error;
    
    /** Non-zero if compilation succeeded, zero on failure */
    int32_t success;
} SwcCompileResult;

/**
 * Compile TypeScript source code to JavaScript.
 *
 * @param source TypeScript source code (null-terminated UTF-8 string)
 * @param filename Source filename for source maps (null-terminated UTF-8 string)
 * @return SwcCompileResult containing compiled code and source map, or error message
 *
 * @note The caller MUST call swc_free_result() on the returned result to free memory.
 *
 * Example:
 *   const char* ts_source = "const x: number = 42;";
 *   SwcCompileResult result = swc_compile_typescript(ts_source, "example.ts");
 *   if (result.success) {
 *       printf("JS: %s\n", result.code);
 *       printf("Map: %s\n", result.source_map);
 *   } else {
 *       fprintf(stderr, "Error: %s\n", result.error);
 *   }
 *   swc_free_result(result);
 */
SwcCompileResult swc_compile_typescript(const char* source, const char* filename);

/**
 * Free memory allocated by swc_compile_typescript.
 *
 * @param result The result structure to free
 *
 * @note This function is safe to call multiple times with the same result,
 *       but the result should not be used after being freed.
 */
void swc_free_result(SwcCompileResult result);

/**
 * Get the version string of the SWC native library.
 *
 * @return Null-terminated version string (do NOT free this pointer)
 */
const char* swc_get_version(void);

#ifdef __cplusplus
}
#endif

#endif /* SWC_NATIVE_H */
