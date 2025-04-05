const std = @import("std");
const Allocator = std.mem.Allocator;

const decoder = std.base64.standard.Decoder;

pub fn decode_base64(encoded: []u8, allocator: Allocator) ![]u8 {
    const b64_len = try decoder.calcSizeForSlice(encoded);
    const b64_dest = try allocator.alloc(u8, b64_len);

    defer allocator.free(b64_dest);

    try decoder.decode(b64_dest, encoded);

    var fbs = std.io.fixedBufferStream(b64_dest[4..]);
    const reader = fbs.reader();
    var decompressor = std.compress.zlib.decompressor(reader);

    var final = std.ArrayList(u8).init(allocator);
    defer final.deinit();

    while (true) {
        const decompressed = try decompressor.get(0);
        if (decompressed.len == 0) {
            break;
        }
        try final.appendSlice(decompressed);
    }
    return try final.toOwnedSlice();
}

pub fn decode_zstd(encoded: []u8, allocator: Allocator) ![]u8 {
    var stream = std.io.fixedBufferStream(encoded);

    const window_len = std.compress.zstd.DecompressorOptions.default_window_buffer_len;
    const window_buffer = try allocator.alloc(u8, window_len);
    defer allocator.free(window_buffer);

    var decompressor = std.compress.zstd.decompressor(stream.reader(), .{ .window_buffer = window_buffer });
    return try decompressor.reader().readAllAlloc(allocator, std.math.maxInt(usize));
}
