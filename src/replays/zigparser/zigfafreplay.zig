const std = @import("std");

const py = @import("cimport.zig").py;
const converter = @import("converter.zig");
const decompressor = @import("decompressor.zig");
const parser = @import("parser.zig");
const structs = @import("structs.zig");

fn parse_replaydata(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "y*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const body: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];
    var replay_parser = parser.parse(body, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_replaydata(replay_parser);
}

fn parse_compressed(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "y*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const compressed: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];

    const preprocessed = decompressor.decompress(compressed, allocator) catch return py.Py_BuildValue("");
    defer preprocessed.deinit(allocator);

    var replay_parser = parser.parse(preprocessed.data, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_full(replay_parser, preprocessed.metadata.value);
}

fn parse_file(_: [*c]py.PyObject, args: [*c]py.PyObject) callconv(.c) [*c]py.PyObject {
    var buf: py.Py_buffer = undefined;
    if (py.PyArg_ParseTuple(args, "s*", &buf) == 0) {
        return null;
    }
    defer py.PyBuffer_Release(&buf);

    const allocator = std.heap.c_allocator;

    const size: usize = @intCast(buf.len);
    const path: []u8 = @as([*]u8, @ptrCast(buf.buf))[0..size];

    const preprocessed = decompressor.decompress_file(path, allocator) catch return py.Py_BuildValue("");
    defer preprocessed.deinit(allocator);

    var replay_parser = parser.parse(preprocessed.data, allocator) catch |err| {
        switch (err) {
            error.Desync => {
                py.PyErr_SetString(py.PyExc_RuntimeError, "Replay is desynced");
                return null;
            },
            else => {
                return py.Py_BuildValue("");
            },
        }
    };
    defer replay_parser.deinit(allocator);
    return converter.convert_full(replay_parser, preprocessed.metadata.value);
}

var Methods = [_]py.PyMethodDef{
    py.PyMethodDef{
        .ml_name = "parse_file",
        .ml_meth = parse_file,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = "parse_compressed",
        .ml_meth = parse_compressed,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = "parse_replaydata",
        .ml_meth = parse_replaydata,
        .ml_flags = py.METH_VARARGS,
        .ml_doc = null,
    },
    py.PyMethodDef{
        .ml_name = null,
        .ml_meth = null,
        .ml_flags = 0,
        .ml_doc = null,
    },
};

var module = py.PyModuleDef{
    .m_base = py.PyModuleDef_Base{
        .ob_base = py.PyObject{
            .unnamed_0 = .{ .ob_refcnt = 1 },
            .ob_type = null,
        },
        .m_init = null,
        .m_index = 0,
        .m_copy = null,
    },
    .m_name = "zigfafreplay",
    .m_doc = null,
    .m_size = -1,
    .m_methods = &Methods,
    .m_slots = null,
    .m_traverse = null,
    .m_clear = null,
    .m_free = null,
};

pub export fn PyInit_zigfafreplay() [*c]py.PyObject {
    py.Py_Initialize();
    return py.PyModule_Create(&module);
}
