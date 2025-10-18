const std = @import("std");
const Allocator = std.mem.Allocator;

const decoder = std.base64.standard.Decoder;

pub fn decode_base64(encoded: []u8, allocator: Allocator) ![]u8 {
    const b64_len = try decoder.calcSizeForSlice(encoded);
    const b64_dest = try allocator.alloc(u8, b64_len);

    defer allocator.free(b64_dest);

    try decoder.decode(b64_dest, encoded);

    var reader = std.Io.Reader.fixed(b64_dest[4..]);
    var decompress: std.compress.flate.Decompress = .init(&reader, .zlib, &.{});
    return try decompress.reader.allocRemaining(allocator, .unlimited);
}

pub fn decode_zstd(encoded: []u8, allocator: Allocator) ![]u8 {
    const window_len = std.compress.zstd.default_window_len;
    const window_buffer = try allocator.alloc(u8, window_len);
    defer allocator.free(window_buffer);

    var reader = std.Io.Reader.fixed(encoded);
    var decompress: std.compress.zstd.Decompress = .init(&reader, window_buffer, .{});
    return try decompress.reader.allocRemaining(allocator, .unlimited);
}
