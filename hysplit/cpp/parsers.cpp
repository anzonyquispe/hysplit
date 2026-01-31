/**
 * High-performance C++ parsers for HYSPLIT output files.
 *
 * This module provides optimized parsing for trajectory and dispersion
 * output files, significantly faster than pure Python implementations.
 *
 * Build with: python setup.py build_ext --inplace
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <numpy/arrayobject.h>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

// Maximum columns for trajectory data
constexpr int MAX_STANDARD_COLS = 9;
constexpr int MAX_EXTENDED_COLS = 18;

// Fast string to double conversion
inline double fast_atof(const char* str) {
    double result = 0.0;
    double sign = 1.0;
    double fraction = 0.0;
    int divisor = 1;
    bool in_fraction = false;
    bool in_exponent = false;
    int exponent = 0;
    int exp_sign = 1;

    // Skip whitespace
    while (*str == ' ' || *str == '\t') str++;

    // Handle sign
    if (*str == '-') {
        sign = -1.0;
        str++;
    } else if (*str == '+') {
        str++;
    }

    while (*str) {
        if (*str >= '0' && *str <= '9') {
            if (in_exponent) {
                exponent = exponent * 10 + (*str - '0');
            } else if (in_fraction) {
                fraction = fraction * 10.0 + (*str - '0');
                divisor *= 10;
            } else {
                result = result * 10.0 + (*str - '0');
            }
        } else if (*str == '.') {
            in_fraction = true;
        } else if (*str == 'e' || *str == 'E') {
            in_exponent = true;
            str++;
            if (*str == '-') {
                exp_sign = -1;
                str++;
            } else if (*str == '+') {
                str++;
            }
            continue;
        } else {
            break;
        }
        str++;
    }

    result = sign * (result + fraction / divisor);
    if (in_exponent) {
        result *= std::pow(10.0, exp_sign * exponent);
    }
    return result;
}

// Split string by whitespace, reusing buffer
class FastSplitter {
public:
    std::vector<std::string> parts;

    void split(const std::string& line) {
        parts.clear();
        std::istringstream iss(line);
        std::string token;
        while (iss >> token) {
            parts.push_back(std::move(token));
        }
    }
};

/**
 * Parse a HYSPLIT trajectory output file.
 *
 * Returns a 2D numpy array with trajectory data.
 */
static PyObject* parse_trajectory_file(PyObject* self, PyObject* args) {
    const char* filepath;

    if (!PyArg_ParseTuple(args, "s", &filepath)) {
        return NULL;
    }

    std::ifstream file(filepath);
    if (!file.is_open()) {
        PyErr_SetString(PyExc_FileNotFoundError, "Cannot open file");
        return NULL;
    }

    // Read entire file
    std::vector<std::string> lines;
    std::string line;
    bool extended = false;
    int header_idx = -1;

    while (std::getline(file, line)) {
        // Check for header
        if (line.find("PRESSURE") != std::string::npos) {
            header_idx = static_cast<int>(lines.size());
        }
        // Check for extended meteorology
        if (line.find("AIR_TEMP") != std::string::npos) {
            extended = true;
        }
        lines.push_back(line);
    }
    file.close();

    if (header_idx < 0) {
        // Return empty array
        npy_intp dims[2] = {0, 0};
        return PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    }

    // Determine output columns
    int n_cols = extended ? MAX_EXTENDED_COLS : MAX_STANDARD_COLS;

    // Count valid data lines
    int n_data_lines = static_cast<int>(lines.size()) - header_idx - 1;
    if (n_data_lines <= 0) {
        npy_intp dims[2] = {0, n_cols};
        return PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    }

    // Pre-allocate data storage
    std::vector<double> data;
    data.reserve(n_data_lines * n_cols);

    FastSplitter splitter;

    // Column indices for extraction
    std::vector<int> col_indices;
    if (extended) {
        col_indices = {2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21};
    } else {
        col_indices = {2, 3, 4, 5, 8, 9, 10, 11, 12};
    }

    int valid_rows = 0;

    // Parse data lines
    for (int i = header_idx + 1; i < static_cast<int>(lines.size()); i++) {
        const std::string& data_line = lines[i];
        if (data_line.empty()) continue;

        splitter.split(data_line);

        if (splitter.parts.size() < 13) continue;

        bool valid = true;
        std::vector<double> row_data;
        row_data.reserve(n_cols);

        for (int idx : col_indices) {
            if (idx >= static_cast<int>(splitter.parts.size())) {
                valid = false;
                break;
            }
            try {
                double val = fast_atof(splitter.parts[idx].c_str());
                row_data.push_back(val);
            } catch (...) {
                valid = false;
                break;
            }
        }

        if (valid && !row_data.empty()) {
            // Pad with zeros if needed
            while (row_data.size() < static_cast<size_t>(n_cols)) {
                row_data.push_back(0.0);
            }
            for (double v : row_data) {
                data.push_back(v);
            }
            valid_rows++;
        }
    }

    if (valid_rows == 0) {
        npy_intp dims[2] = {0, n_cols};
        return PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    }

    // Create numpy array
    npy_intp dims[2] = {valid_rows, n_cols};
    PyObject* array = PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    if (!array) {
        return NULL;
    }

    // Copy data to numpy array
    double* array_data = static_cast<double*>(PyArray_DATA(reinterpret_cast<PyArrayObject*>(array)));
    std::memcpy(array_data, data.data(), valid_rows * n_cols * sizeof(double));

    return array;
}

/**
 * Parse a HYSPLIT PARDUMP (particle dump) file.
 *
 * Returns a 2D numpy array with particle positions.
 */
static PyObject* parse_pardump_file(PyObject* self, PyObject* args) {
    const char* filepath;

    if (!PyArg_ParseTuple(args, "s", &filepath)) {
        return NULL;
    }

    std::ifstream file(filepath);
    if (!file.is_open()) {
        PyErr_SetString(PyExc_FileNotFoundError, "Cannot open file");
        return NULL;
    }

    // PARDUMP can be binary or text format
    // Try text format first
    std::vector<double> data;
    FastSplitter splitter;
    std::string line;
    int valid_rows = 0;

    while (std::getline(file, line)) {
        if (line.empty()) continue;

        splitter.split(line);

        // Need at least: particle_id, lat, lon, height
        if (splitter.parts.size() >= 4) {
            try {
                double particle_id = fast_atof(splitter.parts[0].c_str());
                double lat = fast_atof(splitter.parts[1].c_str());
                double lon = fast_atof(splitter.parts[2].c_str());
                double height = fast_atof(splitter.parts[3].c_str());

                data.push_back(particle_id);
                data.push_back(lat);
                data.push_back(lon);
                data.push_back(height);
                valid_rows++;
            } catch (...) {
                continue;
            }
        }
    }
    file.close();

    if (valid_rows == 0) {
        npy_intp dims[2] = {0, 4};
        return PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    }

    // Create numpy array
    npy_intp dims[2] = {valid_rows, 4};
    PyObject* array = PyArray_SimpleNew(2, dims, NPY_DOUBLE);
    if (!array) {
        return NULL;
    }

    // Copy data
    double* array_data = static_cast<double*>(PyArray_DATA(reinterpret_cast<PyArrayObject*>(array)));
    std::memcpy(array_data, data.data(), valid_rows * 4 * sizeof(double));

    return array;
}

// Method definitions
static PyMethodDef ParserMethods[] = {
    {"parse_trajectory_file", parse_trajectory_file, METH_VARARGS,
     "Parse a HYSPLIT trajectory output file.\n\n"
     "Args:\n"
     "    filepath (str): Path to the trajectory file\n\n"
     "Returns:\n"
     "    numpy.ndarray: 2D array of trajectory data"},

    {"parse_pardump_file", parse_pardump_file, METH_VARARGS,
     "Parse a HYSPLIT PARDUMP file.\n\n"
     "Args:\n"
     "    filepath (str): Path to the PARDUMP file\n\n"
     "Returns:\n"
     "    numpy.ndarray: 2D array of particle positions"},

    {NULL, NULL, 0, NULL}
};

// Module definition
static struct PyModuleDef parsersmodule = {
    PyModuleDef_HEAD_INIT,
    "_parsers",
    "High-performance C++ parsers for HYSPLIT output files.",
    -1,
    ParserMethods
};

// Module initialization
PyMODINIT_FUNC PyInit__parsers(void) {
    import_array();  // Initialize NumPy
    return PyModule_Create(&parsersmodule);
}
