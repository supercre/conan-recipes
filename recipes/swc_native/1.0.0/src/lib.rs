//! SWC TypeScript Compiler - C FFI Interface
//!
//! Provides C-compatible functions for compiling TypeScript to JavaScript
//! with source map support.

use std::ffi::{CStr, CString};
use std::os::raw::c_char;

use swc_common::{
    comments::SingleThreadedComments,
    sync::Lrc,
    FileName, Globals, Mark, SourceMap, GLOBALS,
};
use swc_ecma_ast::{EsVersion, Program, Pass};
use swc_ecma_codegen::{text_writer::JsWriter, Emitter, Config as CodegenConfig};
use swc_ecma_parser::{lexer::Lexer, Parser, StringInput, Syntax, TsSyntax};
use swc_ecma_transforms_typescript::typescript;

/// Result structure returned from compilation
#[repr(C)]
pub struct SwcCompileResult {
    pub code: *mut c_char,
    pub source_map: *mut c_char,
    pub error: *mut c_char,
    pub success: i32,
}

impl SwcCompileResult {
    fn success(code: String, source_map: String) -> Self {
        SwcCompileResult {
            code: CString::new(code).unwrap_or_default().into_raw(),
            source_map: CString::new(source_map).unwrap_or_default().into_raw(),
            error: std::ptr::null_mut(),
            success: 1,
        }
    }

    fn error(msg: String) -> Self {
        SwcCompileResult {
            code: std::ptr::null_mut(),
            source_map: std::ptr::null_mut(),
            error: CString::new(msg).unwrap_or_default().into_raw(),
            success: 0,
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

#[no_mangle]
pub extern "C" fn swc_get_version() -> *const c_char {
    static VERSION: &[u8] = b"1.0.0\0";
    VERSION.as_ptr() as *const c_char
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
