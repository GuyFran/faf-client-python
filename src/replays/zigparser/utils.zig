const std = @import("std");

pub fn cast_float32(buffer: *const [4]u8) f32 {
    return @as(f32, @bitCast(cast_int(u32, buffer)));
}
pub fn cast_int(comptime T: type, buffer: *const [@divExact(@typeInfo(T).int.bits, 8)]u8) T {
    return std.mem.readInt(T, buffer, .little);
}
