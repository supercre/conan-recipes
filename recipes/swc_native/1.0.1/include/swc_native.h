/**
 * SWC Native Library C Interface
 * 
 * This header defines the C interface for the SWC (Speedy Web Compiler) native library.
 * These functions should be implemented in the SWC native library (e.g., swc_native.dll or libswc_native.so)
 */

#ifndef SWC_NATIVE_H
#define SWC_NATIVE_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Result structure for SWC compilation
 */
typedef struct {
    int success;              // 1 if successful, 0 if failed
    const char* code;         // Compiled JavaScript code (NULL on failure)
    const char* source_map;   // Source map JSON (NULL if not generated)
    const char* error;        // Error message (NULL if successful)
} SwcCompileResult;

/**
 * Result structure for loading .swcrc configuration
 */
typedef struct {
    int success;              // 1 if successful, 0 if failed
    const char* config_json;  // Parsed configuration as JSON string (NULL on failure)
    const char* error;        // Error message (NULL if successful)
} SwcConfigResult;

/**
 * Compile TypeScript to JavaScript using SWC
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
 * No file I/O required - both source code and config are passed as data.
 * 
 * @param source TypeScript source code (data, not file path)
 * @param filename Logical filename for source maps (not read from disk)
 * @param config_json JSON string containing SWC configuration
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Example config_json:
 *   {"jsc":{"target":"es2020","parser":{"syntax":"typescript","tsx":true}},"minify":false}
 * 
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile_typescript_with_config(
    const char* source, 
    const char* filename,
    const char* config_json
);

/**
 * Alias for swc_compile_typescript_with_config (backward compatibility)
 */
SwcCompileResult swc_compile_typescript_with_options(
    const char* source, 
    const char* filename,
    const char* options
);

/**
 * Compile TypeScript using .swcrc config file
 * 
 * @param source TypeScript source code
 * @param filename Source filename (used in source maps and error messages)
 * @param config_path Path to .swcrc configuration file
 * @return SwcCompileResult structure containing the compilation result
 * 
 * Note: The caller must call swc_free_result() to free the returned structure
 */
SwcCompileResult swc_compile_typescript_with_config_file(
    const char* source,
    const char* filename,
    const char* config_path
);

/**
 * Load and parse .swcrc configuration file
 * 
 * @param config_path Path to .swcrc file
 * @return SwcConfigResult structure containing the parsed configuration
 * 
 * Note: The caller must call swc_free_config_result() to free the returned structure
 */
SwcConfigResult swc_load_config(const char* config_path);

/**
 * Load .swcrc from a directory (searches for .swcrc file in the given directory)
 * 
 * @param dir_path Directory path where .swcrc file is located
 * @return SwcConfigResult structure containing the parsed configuration
 * 
 * Note: The caller must call swc_free_config_result() to free the returned structure
 */
SwcConfigResult swc_load_config_from_dir(const char* dir_path);

/**
 * Parse and validate configuration from JSON string
 * 
 * @param json_str JSON string containing SWC configuration
 * @return SwcConfigResult structure containing the parsed/normalized configuration
 * 
 * Note: The caller must call swc_free_config_result() to free the returned structure
 */
SwcConfigResult swc_parse_config_json(const char* json_str);

/**
 * Free the memory allocated for SwcCompileResult
 * 
 * @param result The result structure to free
 */
void swc_free_result(SwcCompileResult result);

/**
 * Free the memory allocated for SwcConfigResult
 * 
 * @param result The config result structure to free
 */
void swc_free_config_result(SwcConfigResult result);

/**
 * Get SWC version string
 * 
 * @return Version string (e.g., "1.3.0")
 */
const char* swc_get_version(void);

#ifdef __cplusplus
}
#endif

#endif // SWC_NATIVE_H
