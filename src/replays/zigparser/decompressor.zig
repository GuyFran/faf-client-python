const std = @import("std");
const Allocator = std.mem.Allocator;

const decoder = @import("decoder.zig");
const structs = @import("structs.zig");

pub fn decompress(compressed: []u8, allocator: Allocator) !structs.Preprocessed {
    var body_start: usize = 1;
    while (compressed[body_start - 1] != '\n') {
        body_start += 1;
    }

    const parse_options: std.json.ParseOptions = .{
        .allocate = .alloc_always,
        .ignore_unknown_fields = true,
    };
    const metadata = std.json.parseFromSlice(
        structs.ReplayMetadata,
        allocator,
        compressed[0..body_start],
        parse_options,
    ) catch {
        return structs.ParseError.InvalidReplay;
    };
    errdefer metadata.deinit();

    var data: []u8 = undefined;
    if (metadata.value.version == 1) {
        data = try decoder.decode_base64(compressed[body_start..], allocator);
    } else {
        data = try decoder.decode_zstd(compressed[body_start..], allocator);
    }
    return .{ .metadata = metadata, .data = data };
}

pub fn decompress_file(io: std.Io, path: []const u8, allocator: Allocator) !structs.Preprocessed {
    const replay = try std.Io.Dir.cwd().readFileAlloc(io, path, allocator, .limited(0x20000000));
    defer allocator.free(replay);
    return try decompress(replay, allocator);
}
