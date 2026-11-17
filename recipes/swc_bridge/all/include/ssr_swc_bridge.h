#pragma once

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ssr_swc_buffer {
    uint8_t* ptr;
    size_t len;
    size_t cap;
} ssr_swc_buffer;

typedef struct ssr_swc_transform_output {
    ssr_swc_buffer code;
    ssr_swc_buffer map;
    ssr_swc_buffer error;
} ssr_swc_transform_output;

int ssr_swc_transform_ts(
    const uint8_t* source_ptr,
    size_t source_len,
    const char* filename,
    const char* swcrc_json,
    ssr_swc_transform_output* output);

void ssr_swc_free_buffer(ssr_swc_buffer buffer);

#ifdef __cplusplus
}
#endif

