/**
 * SWC Native Library C Interface
 * 
 * This header defines the C interface for the SWC (Speedy Web Compiler) native library.
 * These functions should be implemented in the SWC native library (e.g., swc_native.dll or libswc_native.so)
 */

#ifndef SWC_NATIVE_H
#define SWC_NATIVE_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================================
 * Type Definitions
 * ============================================================================ */

/**
 * Opaque handle for SWC configuration
 * 
 * This handle holds a parsed and validated SWC configuration that can be
 * reused across multiple compilation calls for better performance.
 */
typedef struct SwcConfigHandleImpl* SwcConfigHandle;

/**
 * Result structure for SWC compilation
 */
typedef struct {
    int success;              // 1 if successful, 0 if failed
    const char* code;         // Compiled JavaScript code (NULL on failure)
    const char* source_map;   // Source map JSON (NULL if not generated)
    const char* error;        // Error message (NULL if successful)
} SwcCompileResult;

/* ============================================================================
 * Configuration Handle API (Recommended)
 * 
 * Use these functions for optimal performance when compiling multiple files
 * with the same configuration. The config is parsed once and reused.
 * ============================================================================ */

/**
 * Create a configuration handle from JSON string
 * 
 * @param config_json JSON string containing SWC configuration
 * @return Configuration handle, or NULL on failure
 * 
 * Example config_json:
 *   {"jsc":{"target":"es2020","parser":{"syntax":"typescript","tsx":true}},"minify":false}
 * 
 * Note: The caller must call swc_config_free() to release the handle
 */
SwcConfigHandle swc_config_create(const char* config_json);

/**
 * Create a configuration handle from .swcrc file
 * 
 * @param config_path Path to .swcrc configuration file
 * @return Configuration handle, or NULL on failure
 * 
 * Note: The caller must call swc_config_free() to release the handle
 */
SwcConfigHandle swc_config_create_from_file(const char* config_path);

/**
 * Create a configuration handle by searching for .swcrc in a directory
 * 
 * @param dir_path Directory path where .swcrc file is located
 * @return Configuration handle, or NULL on failure
 * 
 * Note: The caller must call swc_config_free() to release the handle
 */
SwcConfigHandle swc_config_create_from_dir(const char* dir_path);

/**
 * Create a default configuration handle for TypeScript compilation
 * 
 * Uses sensible defaults:
 *   - target: ES2020
 *   - parser: typescript
 *   - source maps: enabled
 * 
 * @return Configuration handle, or NULL on failure
 * 
 * Note: The caller must call swc_config_free() to release the handle
 */
SwcConfigHandle swc_config_create_default(void);

/**
 * Get the last error message from config creation
 * 
 * Call this after swc_config_create*() returns NULL to get the error details.
 * 
 * @return Error message string (valid until next swc_config_create*() call)
 */
const char* swc_config_get_last_error(void);

/**
 * Get the configuration as JSON string
 * 
 * @param handle Configuration handle
 * @return JSON string representation of the config (valid while handle exists)
 */
const char* swc_config_to_json(SwcConfigHandle handle);

/**
 * Free a configuration handle
 * 
 * @param handle Configuration handle to free (safe to pass NULL)
 */
void swc_config_free(SwcConfigHandle handle);

/**
 * Compile TypeScript to JavaScript using a configuration handle
 * 
 * This is the recommended compilation function for best performance.
 * 
 * @param handle Configuration handle (created via swc_config_create*())
 * @param source TypeScript source code
 * @param filename Source filename (used in source maps and error messages)
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile(SwcConfigHandle handle, const char* source, const char* filename);

/* ============================================================================
 * Simple API (Convenience functions)
 * 
 * These functions are convenient for one-off compilations but less efficient
 * for batch processing since they parse the config on each call.
 * ============================================================================ */

/**
 * Compile TypeScript to JavaScript with default settings
 * 
 * @param source TypeScript source code
 * @param filename Source filename (used in source maps and error messages)
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile_typescript(const char* source, const char* filename);

/**
 * Compile TypeScript to JavaScript with configuration from JSON string
 * 
 * @param source TypeScript source code
 * @param filename Source filename (used in source maps and error messages)
 * @param config_json JSON string containing SWC configuration
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Note: For multiple files with same config, use swc_config_create() + swc_compile() instead
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile_typescript_with_config(
    const char* source, 
    const char* filename,
    const char* config_json
);

/**
 * Compile TypeScript using .swcrc config file
 * 
 * @param source TypeScript source code
 * @param filename Source filename (used in source maps and error messages)
 * @param config_path Path to .swcrc configuration file
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Note: For multiple files with same config, use swc_config_create_from_file() + swc_compile() instead
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile_typescript_with_config_file(
    const char* source,
    const char* filename,
    const char* config_path
);

/* ============================================================================
 * Memory Management
 * ============================================================================ */

/**
 * Free the memory allocated for SwcCompileResult
 * 
 * @param result The result structure to free
 */
void swc_free_result(SwcCompileResult result);

/* ============================================================================
 * Utility Functions
 * ============================================================================ */

/**
 * Get SWC version string
 * 
 * @return Version string (e.g., "1.3.0")
 */
const char* swc_get_version(void);

/**
 * Get swc_native library version string
 * 
 * @return Version string (e.g., "1.0.1")
 */
const char* swc_native_get_version(void);

/* ============================================================================
 * Deprecated API (for backward compatibility)
 * ============================================================================ */

/**
 * @deprecated Use swc_compile_typescript_with_config() instead
 */
SwcCompileResult swc_compile_typescript_with_options(
    const char* source, 
    const char* filename,
    const char* options
);

/**
 * @deprecated Use swc_config_create_from_file() + swc_config_to_json() instead
 */
typedef struct {
    int success;
    const char* config_json;
    const char* error;
} SwcConfigResult;

/**
 * @deprecated Use swc_config_create_from_file() instead
 */
SwcConfigResult swc_load_config(const char* config_path);

/**
 * @deprecated Use swc_config_create_from_dir() instead
 */
SwcConfigResult swc_load_config_from_dir(const char* dir_path);

/**
 * @deprecated Use swc_config_create() instead
 */
SwcConfigResult swc_parse_config_json(const char* json_str);

/**
 * @deprecated Use swc_config_free() for handles
 */
void swc_free_config_result(SwcConfigResult result);

#ifdef __cplusplus
}
#endif

#endif // SWC_NATIVE_H
