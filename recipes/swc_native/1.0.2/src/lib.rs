//! SWC TypeScript Compiler - C FFI Interface
//!
//! Provides C-compatible functions for compiling TypeScript to JavaScript
//! with source map support.

use std::ffi::{CStr, CString};
use std::fs;
use std::os::raw::c_char;
use std::path::Path;

use serde::{Deserialize, Serialize};
use swc_common::{
    comments::SingleThreadedComments,
    sync::Lrc,
    FileName, Globals, Mark, SourceMap, GLOBALS,
};
use swc_ecma_ast::{EsVersion, Program, Pass};
use swc_ecma_codegen::{text_writer::JsWriter, Emitter, Config as CodegenConfig};
use swc_ecma_parser::{lexer::Lexer, Parser, StringInput, Syntax, TsSyntax, EsSyntax};
use swc_ecma_transforms_typescript::typescript;

/// SWC Configuration from .swcrc file
#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SwcConfig {
    #[serde(default)]
    pub jsc: JscConfig,
    #[serde(default)]
    pub source_maps: Option<bool>,
    #[serde(default)]
    pub minify: Option<bool>,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct JscConfig {
    #[serde(default)]
    pub parser: Option<ParserConfig>,
    #[serde(default)]
    pub target: Option<String>,
    #[serde(default)]
    pub minify: Option<MinifyConfig>,
    #[serde(default)]
    pub transform: Option<TransformConfig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "syntax", rename_all = "lowercase")]
pub enum ParserConfig {
    #[serde(rename = "typescript")]
    Typescript(TsParserConfig),
    #[serde(rename = "ecmascript")]
    Ecmascript(EsParserConfig),
}

impl Default for ParserConfig {
    fn default() -> Self {
        ParserConfig::Typescript(TsParserConfig::default())
    }
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TsParserConfig {
    #[serde(default)]
    pub tsx: bool,
    #[serde(default)]
    pub decorators: bool,
    #[serde(default)]
    pub dynamic_import: bool,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct EsParserConfig {
    #[serde(default)]
    pub jsx: bool,
    #[serde(default)]
    pub decorators: bool,
    #[serde(default)]
    pub dynamic_import: bool,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct MinifyConfig {
    #[serde(default)]
    pub compress: Option<bool>,
    #[serde(default)]
    pub mangle: Option<bool>,
}

#[derive(Debug, Default, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TransformConfig {
    #[serde(default)]
    pub legacy_decorator: bool,
    #[serde(default)]
    pub decorator_metadata: bool,
}

/// Result structure returned from compilation
/// Must match the C header definition exactly
#[repr(C)]
pub struct SwcCompileResult {
    pub success: i32,
    pub code: *mut c_char,
    pub source_map: *mut c_char,
    pub error: *mut c_char,
}

impl SwcCompileResult {
    fn success(code: String, source_map: String) -> Self {
        SwcCompileResult {
            success: 1,
            code: CString::new(code).unwrap_or_default().into_raw(),
            source_map: CString::new(source_map).unwrap_or_default().into_raw(),
            error: std::ptr::null_mut(),
        }
    }

    fn error(msg: String) -> Self {
        SwcCompileResult {
            success: 0,
            code: std::ptr::null_mut(),
            source_map: std::ptr::null_mut(),
            error: CString::new(msg).unwrap_or_default().into_raw(),
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn swc_compile_typescript(
    source: *const c_char,
    filename: *const c_char,
) -> SwcCompileResult {
    if source.is_null() {
        return SwcCompileResult::error("Source pointer is null".to_string());
    }
    if filename.is_null() {
        return SwcCompileResult::error("Filename pointer is null".to_string());
    }

    let source_str = match CStr::from_ptr(source).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in source: {}", e)),
    };

    let filename_str = match CStr::from_ptr(filename).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in filename: {}", e)),
    };

    match compile_typescript_internal(&source_str, &filename_str) {
        Ok((code, source_map)) => SwcCompileResult::success(code, source_map),
        Err(e) => SwcCompileResult::error(e.to_string()),
    }
}

#[no_mangle]
pub unsafe extern "C" fn swc_free_result(result: SwcCompileResult) {
    if !result.code.is_null() {
        drop(CString::from_raw(result.code));
    }
    if !result.source_map.is_null() {
        drop(CString::from_raw(result.source_map));
    }
    if !result.error.is_null() {
        drop(CString::from_raw(result.error));
    }
}

/// Result structure for loading config
/// Must match the C header definition exactly
#[repr(C)]
pub struct SwcConfigResult {
    pub success: i32,
    pub config_json: *mut c_char,
    pub error: *mut c_char,
}

impl SwcConfigResult {
    fn success(config_json: String) -> Self {
        SwcConfigResult {
            success: 1,
            config_json: CString::new(config_json).unwrap_or_default().into_raw(),
            error: std::ptr::null_mut(),
        }
    }

    fn error(msg: String) -> Self {
        SwcConfigResult {
            success: 0,
            config_json: std::ptr::null_mut(),
            error: CString::new(msg).unwrap_or_default().into_raw(),
        }
    }
}

/// Load and parse .swcrc configuration file
/// 
/// Returns the parsed configuration as JSON string
#[no_mangle]
pub unsafe extern "C" fn swc_load_config(config_path: *const c_char) -> SwcConfigResult {
    if config_path.is_null() {
        return SwcConfigResult::error("Config path is null".to_string());
    }

    let path_str = match CStr::from_ptr(config_path).to_str() {
        Ok(s) => s,
        Err(e) => return SwcConfigResult::error(format!("Invalid UTF-8 in path: {}", e)),
    };

    match load_config_internal(path_str) {
        Ok(config_json) => SwcConfigResult::success(config_json),
        Err(e) => SwcConfigResult::error(e.to_string()),
    }
}

/// Load .swcrc from a directory (searches for .swcrc file)
#[no_mangle]
pub unsafe extern "C" fn swc_load_config_from_dir(dir_path: *const c_char) -> SwcConfigResult {
    if dir_path.is_null() {
        return SwcConfigResult::error("Directory path is null".to_string());
    }

    let path_str = match CStr::from_ptr(dir_path).to_str() {
        Ok(s) => s,
        Err(e) => return SwcConfigResult::error(format!("Invalid UTF-8 in path: {}", e)),
    };

    let config_path = Path::new(path_str).join(".swcrc");
    
    if !config_path.exists() {
        return SwcConfigResult::error(format!(".swcrc not found in {}", path_str));
    }

    match load_config_internal(config_path.to_str().unwrap_or_default()) {
        Ok(config_json) => SwcConfigResult::success(config_json),
        Err(e) => SwcConfigResult::error(e.to_string()),
    }
}

/// Parse and validate configuration from JSON string
/// 
/// Returns the normalized configuration as JSON string
#[no_mangle]
pub unsafe extern "C" fn swc_parse_config_json(json_str: *const c_char) -> SwcConfigResult {
    if json_str.is_null() {
        return SwcConfigResult::error("JSON string is null".to_string());
    }

    let json = match CStr::from_ptr(json_str).to_str() {
        Ok(s) => s,
        Err(e) => return SwcConfigResult::error(format!("Invalid UTF-8 in JSON: {}", e)),
    };

    match parse_config_json_internal(json) {
        Ok(config_json) => SwcConfigResult::success(config_json),
        Err(e) => SwcConfigResult::error(e.to_string()),
    }
}

/// Free the config result
#[no_mangle]
pub unsafe extern "C" fn swc_free_config_result(result: SwcConfigResult) {
    if !result.config_json.is_null() {
        drop(CString::from_raw(result.config_json));
    }
    if !result.error.is_null() {
        drop(CString::from_raw(result.error));
    }
}

/// Compile TypeScript with configuration from JSON string (no file I/O required)
/// 
/// Both source code and config are passed as data, no file paths needed.
/// The filename parameter is only used for source map generation.
#[no_mangle]
pub unsafe extern "C" fn swc_compile_typescript_with_config(
    source: *const c_char,
    filename: *const c_char,
    config_json: *const c_char,
) -> SwcCompileResult {
    if source.is_null() {
        return SwcCompileResult::error("Source pointer is null".to_string());
    }
    if filename.is_null() {
        return SwcCompileResult::error("Filename pointer is null".to_string());
    }
    if config_json.is_null() {
        return SwcCompileResult::error("Config JSON pointer is null".to_string());
    }

    let source_str = match CStr::from_ptr(source).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in source: {}", e)),
    };

    let filename_str = match CStr::from_ptr(filename).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in filename: {}", e)),
    };

    let config_str = match CStr::from_ptr(config_json).to_str() {
        Ok(s) => s,
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in config: {}", e)),
    };

    let config: SwcConfig = match serde_json::from_str(config_str) {
        Ok(c) => c,
        Err(e) => return SwcCompileResult::error(format!("Failed to parse config: {}", e)),
    };

    match compile_typescript_with_config(&source_str, &filename_str, &config) {
        Ok((code, source_map)) => SwcCompileResult::success(code, source_map),
        Err(e) => SwcCompileResult::error(e.to_string()),
    }
}

/// Alias for swc_compile_typescript_with_config (backward compatibility)
#[no_mangle]
pub unsafe extern "C" fn swc_compile_typescript_with_options(
    source: *const c_char,
    filename: *const c_char,
    options: *const c_char,
) -> SwcCompileResult {
    swc_compile_typescript_with_config(source, filename, options)
}

/// Compile TypeScript using .swcrc config file
#[no_mangle]
pub unsafe extern "C" fn swc_compile_typescript_with_config_file(
    source: *const c_char,
    filename: *const c_char,
    config_path: *const c_char,
) -> SwcCompileResult {
    if source.is_null() {
        return SwcCompileResult::error("Source pointer is null".to_string());
    }
    if filename.is_null() {
        return SwcCompileResult::error("Filename pointer is null".to_string());
    }
    if config_path.is_null() {
        return SwcCompileResult::error("Config path is null".to_string());
    }

    let source_str = match CStr::from_ptr(source).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in source: {}", e)),
    };

    let filename_str = match CStr::from_ptr(filename).to_str() {
        Ok(s) => s.to_owned(),
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in filename: {}", e)),
    };

    let config_path_str = match CStr::from_ptr(config_path).to_str() {
        Ok(s) => s,
        Err(e) => return SwcCompileResult::error(format!("Invalid UTF-8 in config path: {}", e)),
    };

    let config = match load_and_parse_config(config_path_str) {
        Ok(c) => c,
        Err(e) => return SwcCompileResult::error(e.to_string()),
    };

    match compile_typescript_with_config(&source_str, &filename_str, &config) {
        Ok((code, source_map)) => SwcCompileResult::success(code, source_map),
        Err(e) => SwcCompileResult::error(e.to_string()),
    }
}

#[no_mangle]
pub extern "C" fn swc_get_version() -> *const c_char {
    static VERSION: &[u8] = b"1.0.0\0";
    VERSION.as_ptr() as *const c_char
}

fn load_config_internal(config_path: &str) -> Result<String, anyhow::Error> {
    let content = fs::read_to_string(config_path)
        .map_err(|e| anyhow::anyhow!("Failed to read config file: {}", e))?;

    // Parse to validate JSON
    let config: SwcConfig = serde_json::from_str(&content)
        .map_err(|e| anyhow::anyhow!("Failed to parse config: {}", e))?;

    // Return the normalized JSON
    serde_json::to_string(&config)
        .map_err(|e| anyhow::anyhow!("Failed to serialize config: {}", e))
}

fn load_and_parse_config(config_path: &str) -> Result<SwcConfig, anyhow::Error> {
    let content = fs::read_to_string(config_path)
        .map_err(|e| anyhow::anyhow!("Failed to read config file: {}", e))?;

    serde_json::from_str(&content)
        .map_err(|e| anyhow::anyhow!("Failed to parse config: {}", e))
}

fn parse_config_json_internal(json: &str) -> Result<String, anyhow::Error> {
    // Parse to validate JSON
    let config: SwcConfig = serde_json::from_str(json)
        .map_err(|e| anyhow::anyhow!("Failed to parse config JSON: {}", e))?;

    // Return the normalized JSON
    serde_json::to_string(&config)
        .map_err(|e| anyhow::anyhow!("Failed to serialize config: {}", e))
}

fn parse_es_version(target: &str) -> EsVersion {
    match target.to_lowercase().as_str() {
        "es3" => EsVersion::Es3,
        "es5" => EsVersion::Es5,
        "es2015" | "es6" => EsVersion::Es2015,
        "es2016" => EsVersion::Es2016,
        "es2017" => EsVersion::Es2017,
        "es2018" => EsVersion::Es2018,
        "es2019" => EsVersion::Es2019,
        "es2020" => EsVersion::Es2020,
        "es2021" => EsVersion::Es2021,
        "es2022" => EsVersion::Es2022,
        "esnext" => EsVersion::EsNext,
        _ => EsVersion::Es2020,
    }
}

fn compile_typescript_with_config(
    source: &str,
    filename: &str,
    config: &SwcConfig,
) -> Result<(String, String), anyhow::Error> {
    GLOBALS.set(&Globals::new(), || {
        let cm: Lrc<SourceMap> = Default::default();
        let comments = SingleThreadedComments::default();

        let fm = cm.new_source_file(
            Lrc::new(FileName::Custom(filename.to_string())),
            source.to_string(),
        );

        // Determine syntax based on config
        let syntax = match &config.jsc.parser {
            Some(ParserConfig::Typescript(ts_config)) => {
                Syntax::Typescript(TsSyntax {
                    tsx: ts_config.tsx || filename.ends_with(".tsx"),
                    decorators: ts_config.decorators,
                    dts: filename.ends_with(".d.ts"),
                    no_early_errors: false,
                    disallow_ambiguous_jsx_like: false,
                })
            }
            Some(ParserConfig::Ecmascript(es_config)) => {
                Syntax::Es(EsSyntax {
                    jsx: es_config.jsx,
                    decorators: es_config.decorators,
                    ..Default::default()
                })
            }
            None => {
                // Default TypeScript config
                Syntax::Typescript(TsSyntax {
                    tsx: filename.ends_with(".tsx"),
                    decorators: true,
                    dts: filename.ends_with(".d.ts"),
                    no_early_errors: false,
                    disallow_ambiguous_jsx_like: false,
                })
            }
        };

        let target_version = config.jsc.target.as_ref()
            .map(|t| parse_es_version(t))
            .unwrap_or(EsVersion::Es2020);

        let lexer = Lexer::new(
            syntax,
            target_version,
            StringInput::from(&*fm),
            Some(&comments),
        );

        let mut parser = Parser::new_from(lexer);

        let module = parser
            .parse_module()
            .map_err(|e| anyhow::anyhow!("Failed to parse: {:?}", e))?;

        let errors = parser.take_errors();
        if !errors.is_empty() {
            return Err(anyhow::anyhow!("Parse errors: {:?}", errors));
        }

        // Apply TypeScript transform
        let unresolved_mark = Mark::new();
        let top_level_mark = Mark::new();

        let ts_config = typescript::Config {
            verbatim_module_syntax: false,
            ..Default::default()
        };

        let mut program = Program::Module(module);
        let mut pass = typescript::typescript(ts_config, unresolved_mark, top_level_mark);
        pass.process(&mut program);

        let module = match program {
            Program::Module(m) => m,
            Program::Script(_) => {
                return Err(anyhow::anyhow!("Expected module, got script"));
            }
        };

        // Generate JavaScript code with source map
        let should_minify = config.minify.unwrap_or(false);
        let mut src_map = vec![];
        let mut buf = vec![];

        {
            let wr = JsWriter::new(cm.clone(), "\n", &mut buf, Some(&mut src_map));

            let mut emitter = Emitter {
                cfg: CodegenConfig::default()
                    .with_minify(should_minify)
                    .with_target(target_version),
                cm: cm.clone(),
                comments: Some(&comments),
                wr: Box::new(wr),
            };

            emitter.emit_module(&module)?;
        }

        let code = String::from_utf8(buf)?;

        // Build source map
        let source_map_json = if config.source_maps.unwrap_or(true) {
            let mut sm_builder = sourcemap::SourceMapBuilder::new(Some(filename));

            let src_id = sm_builder.add_source(filename);
            sm_builder.set_source_contents(src_id, Some(source));

            for (byte_pos, line_col) in &src_map {
                let loc = cm.lookup_char_pos(*byte_pos);
                sm_builder.add_raw(
                    line_col.line,
                    line_col.col,
                    (loc.line - 1) as u32,
                    loc.col_display as u32,
                    Some(src_id),
                    None,
                    false,
                );
            }

            let sm = sm_builder.into_sourcemap();
            let mut sm_buf = vec![];
            sm.to_writer(&mut sm_buf)?;
            String::from_utf8(sm_buf)?
        } else {
            String::new()
        };

        Ok((code, source_map_json))
    })
}

fn compile_typescript_internal(
    source: &str,
    filename: &str,
) -> Result<(String, String), anyhow::Error> {
    GLOBALS.set(&Globals::new(), || {
        let cm: Lrc<SourceMap> = Default::default();
        let comments = SingleThreadedComments::default();

        let fm = cm.new_source_file(
            Lrc::new(FileName::Custom(filename.to_string())),
            source.to_string(),
        );

        let syntax = Syntax::Typescript(TsSyntax {
            tsx: filename.ends_with(".tsx"),
            decorators: true,
            dts: filename.ends_with(".d.ts"),
            no_early_errors: false,
            disallow_ambiguous_jsx_like: false,
        });

        let lexer = Lexer::new(
            syntax,
            EsVersion::Es2020,
            StringInput::from(&*fm),
            Some(&comments),
        );

        let mut parser = Parser::new_from(lexer);

        let module = parser
            .parse_module()
            .map_err(|e| anyhow::anyhow!("Failed to parse TypeScript: {:?}", e))?;

        let errors = parser.take_errors();
        if !errors.is_empty() {
            return Err(anyhow::anyhow!("Parse errors: {:?}", errors));
        }

        // Apply TypeScript transform using Pass trait
        let unresolved_mark = Mark::new();
        let top_level_mark = Mark::new();

        let ts_config = typescript::Config {
            verbatim_module_syntax: false,
            ..Default::default()
        };
        
        let mut program = Program::Module(module);
        let mut pass = typescript::typescript(ts_config, unresolved_mark, top_level_mark);
        pass.process(&mut program);

        let module = match program {
            Program::Module(m) => m,
            Program::Script(_) => {
                return Err(anyhow::anyhow!("Expected module, got script"));
            }
        };

        // Generate JavaScript code with source map
        let mut src_map = vec![];
        let mut buf = vec![];

        {
            let wr = JsWriter::new(cm.clone(), "\n", &mut buf, Some(&mut src_map));
            
            let mut emitter = Emitter {
                cfg: CodegenConfig::default()
                    .with_minify(false)
                    .with_target(EsVersion::Es2020),
                cm: cm.clone(),
                comments: Some(&comments),
                wr: Box::new(wr),
            };

            emitter.emit_module(&module)?;
        }

        let code = String::from_utf8(buf)?;

        // Build source map
        let source_map_json = {
            let mut sm_builder = sourcemap::SourceMapBuilder::new(Some(filename));
            
            let src_id = sm_builder.add_source(filename);
            sm_builder.set_source_contents(src_id, Some(source));

            for (byte_pos, line_col) in &src_map {
                let loc = cm.lookup_char_pos(*byte_pos);
                sm_builder.add_raw(
                    line_col.line,
                    line_col.col,
                    (loc.line - 1) as u32,
                    loc.col_display as u32,
                    Some(src_id),
                    None,
                    false,
                );
            }

            let sm = sm_builder.into_sourcemap();
            let mut sm_buf = vec![];
            sm.to_writer(&mut sm_buf)?;
            String::from_utf8(sm_buf)?
        };

        Ok((code, source_map_json))
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ffi::CString;

    #[test]
    fn test_compile_simple() {
        let source = CString::new("const x: number = 42;").unwrap();
        let filename = CString::new("test.ts").unwrap();

        unsafe {
            let result = swc_compile_typescript(source.as_ptr(), filename.as_ptr());
            assert_eq!(result.success, 1);
            assert!(!result.code.is_null());
            let code = CStr::from_ptr(result.code).to_str().unwrap();
            assert!(code.contains("const x = 42"));
            swc_free_result(result);
        }
    }

    #[test]
    fn test_null_source() {
        unsafe {
            let filename = CString::new("test.ts").unwrap();
            let result = swc_compile_typescript(std::ptr::null(), filename.as_ptr());
            assert_eq!(result.success, 0);
            assert!(!result.error.is_null());
            swc_free_result(result);
        }
    }
}
