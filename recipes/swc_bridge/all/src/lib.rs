use std::ffi::CStr;
use std::os::raw::c_char;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::path::Path;
use std::ptr;
use std::slice;

use swc::config::{Config, Options};
use swc::{try_with_handler, Compiler, HandlerOpts};
use swc_common::errors::ColorConfig;
use swc_common::sync::Lrc;
use swc_common::{FileName, SourceMap, GLOBALS};

#[repr(C)]
pub struct SsrSwcBuffer {
    ptr: *mut u8,
    len: usize,
    cap: usize,
}

#[repr(C)]
pub struct SsrSwcTransformOutput {
    code: SsrSwcBuffer,
    map: SsrSwcBuffer,
    error: SsrSwcBuffer,
}

impl SsrSwcBuffer {
    fn empty() -> Self {
        Self {
            ptr: ptr::null_mut(),
            len: 0,
            cap: 0,
        }
    }

    fn from_string(value: String) -> Self {
        let mut bytes = value.into_bytes();
        let buffer = Self {
            ptr: bytes.as_mut_ptr(),
            len: bytes.len(),
            cap: bytes.capacity(),
        };
        std::mem::forget(bytes);
        buffer
    }
}

impl SsrSwcTransformOutput {
    fn empty() -> Self {
        Self {
            code: SsrSwcBuffer::empty(),
            map: SsrSwcBuffer::empty(),
            error: SsrSwcBuffer::empty(),
        }
    }

    fn error(message: String) -> Self {
        Self {
            error: SsrSwcBuffer::from_string(message),
            ..Self::empty()
        }
    }
}

#[no_mangle]
pub extern "C" fn ssr_swc_free_buffer(buffer: SsrSwcBuffer) {
    if buffer.ptr.is_null() || buffer.cap == 0 {
        return;
    }

    unsafe {
        drop(Vec::from_raw_parts(buffer.ptr, buffer.len, buffer.cap));
    }
}

#[no_mangle]
pub extern "C" fn ssr_swc_transform_ts(
    source_ptr: *const u8,
    source_len: usize,
    filename: *const c_char,
    swcrc_json: *const c_char,
    output: *mut SsrSwcTransformOutput,
) -> i32 {
    if output.is_null() {
        return -1;
    }

    let result = catch_unwind(AssertUnwindSafe(|| {
        transform_ffi(source_ptr, source_len, filename, swcrc_json)
    }));

    let final_output = match result {
        Ok(Ok((code, map))) => SsrSwcTransformOutput {
            code: SsrSwcBuffer::from_string(code),
            map: map.map(SsrSwcBuffer::from_string).unwrap_or_else(SsrSwcBuffer::empty),
            error: SsrSwcBuffer::empty(),
        },
        Ok(Err(message)) => SsrSwcTransformOutput::error(message),
        Err(_) => SsrSwcTransformOutput::error("SWC transform panicked".to_string()),
    };

    let status = if final_output.error.ptr.is_null() { 0 } else { 1 };
    unsafe {
        *output = final_output;
    }
    status
}

fn transform_ffi(
    source_ptr: *const u8,
    source_len: usize,
    filename: *const c_char,
    swcrc_json: *const c_char,
) -> Result<(String, Option<String>), String> {
    if source_ptr.is_null() {
        return Err("source_ptr is null".to_string());
    }

    let source_bytes = unsafe { slice::from_raw_parts(source_ptr, source_len) };
    let source = std::str::from_utf8(source_bytes)
        .map_err(|err| format!("TypeScript source is not UTF-8: {err}"))?;

    let filename = cstr_to_string(filename).unwrap_or_else(|| "input.ts".to_string());
    let swcrc = cstr_to_string(swcrc_json);
    transform_ts(source, &filename, swcrc.as_deref())
}

fn cstr_to_string(value: *const c_char) -> Option<String> {
    if value.is_null() {
        return None;
    }

    unsafe { CStr::from_ptr(value) }
        .to_str()
        .ok()
        .map(|value| value.to_string())
}

fn transform_ts(
    source: &str,
    filename: &str,
    swcrc_json: Option<&str>,
) -> Result<(String, Option<String>), String> {
    let cm: Lrc<SourceMap> = Default::default();
    let compiler = Compiler::new(cm.clone());

    let mut options = Options::default();
    options.filename = filename.to_string();
    options.swcrc = false;
    options.config = match swcrc_json {
        Some(json) if !json.trim().is_empty() => serde_json::from_str::<Config>(json)
            .map_err(|err| format!("Failed to parse SWC config JSON: {err}"))?,
        _ => default_ts_config()?,
    };
    options.config.adjust(Path::new(filename));

    let file_name = if filename.is_empty() {
        FileName::Anon.into()
    } else {
        FileName::Real(filename.into()).into()
    };
    let source_file = cm.new_source_file(file_name, source.to_string());

    try_with_handler(
        cm,
        HandlerOpts {
            color: ColorConfig::Never,
            skip_filename: false,
        },
        |handler| {
            GLOBALS.set(&Default::default(), || {
                compiler.process_js_file(source_file, handler, &options)
            })
        },
    )
    .map(|output| (output.code, output.map))
    .map_err(|err| err.to_pretty_error().to_string())
}

fn default_ts_config() -> Result<Config, String> {
    serde_json::from_str::<Config>(
        r#"{
            "jsc": {
                "parser": {
                    "syntax": "typescript",
                    "tsx": false,
                    "decorators": true,
                    "dynamicImport": true
                },
                "target": "es2022",
                "transform": {
                    "legacyDecorator": true,
                    "decoratorMetadata": true
                }
            },
            "module": {
                "type": "es6"
            },
            "sourceMaps": true,
            "inlineSourcesContent": false
        }"#,
    )
    .map_err(|err| format!("Failed to build default SWC config: {err}"))
}
