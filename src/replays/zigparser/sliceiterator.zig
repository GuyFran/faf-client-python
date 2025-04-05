// BSD 3-Clause License
//
// Copyright (c) 2023, Broch Web Solutions
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// 1. Redistributions of source code must retain the above copyright notice, this
//    list of conditions and the following disclaimer.
//
// 2. Redistributions in binary form must reproduce the above copyright notice,
//    this list of conditions and the following disclaimer in the documentation
//    and/or other materials provided with the distribution.
//
// 3. Neither the name of the copyright holder nor the names of its
//    contributors may be used to endorse or promote products derived from
//    this software without specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
// DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
// FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
// SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
// CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
// OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
// OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
const std = @import("std");
const mem = std.mem;
const utils = @import("utils.zig");

/// Works over memory owned by another function
pub const SliceIterator = struct {
    const Self = @This();

    ptr: [*]const u8,
    len: usize,

    /// Source of the slice MUST last for at least as long as the SliceIterator
    pub fn from_slice(slice: []const u8) Self {
        return Self{ .ptr = slice.ptr, .len = slice.len };
    }
    pub fn next(self: *Self) ?u8 {
        if (self.len >= 1) {
            const first = self.ptr[0];
            self.ptr += 1;
            self.len -= 1;
            return first;
        } else {
            return null;
        }
    }
    /// Does nothing if the iterator is empty
    pub fn ignoreNext(self: *Self) void {
        if (self.len >= 1) {
            self.ptr += 1;
            self.len -= 1;
        }
    }
    /// Does nothing if slice runs out
    pub fn ignoreMany(self: *Self, n: usize) void {
        if (n == 0) return;
        if (self.len >= n) {
            self.ptr += n;
            self.len -= n;
        } else {
            self.ptr += self.len;
            self.len = 0;
        }
    }

    pub fn read_int(self: *Self, comptime T: type) T {
        const leng = @divExact(@typeInfo(T).int.bits, 8);
        defer self.ignoreMany(leng);
        return utils.cast_int(T, self.ptr[0..leng]);
    }

    pub fn read_float32(self: *Self) f32 {
        defer self.ignoreMany(4);
        return utils.cast_float32(self.ptr[0..4]);
    }

    pub fn read_uint32(self: *Self) u32 {
        return self.read_int(u32);
    }

    pub fn read_string(self: *Self) []const u8 {
        var len: usize = 0;
        while (self.ptr[len] != '\x00') {
            len += 1;
        }
        const slice = self.ptr[0..len];
        self.ignoreMany(len + 1);
        return slice;
    }
};
