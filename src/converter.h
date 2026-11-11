#pragma once

#include <stdexcept>
#include <string>
#include <string_view>
#include <optional>

namespace yp {
enum class Format { Yaml, Properties };
struct ConversionResult { Format output_format; std::string text; };
class ConversionError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
std::string to_properties(std::string_view input, bool sort_keys = false);
std::string to_yaml(std::string_view input, bool sort_keys = false);
ConversionResult auto_convert(std::string_view input, std::optional<Format> source_hint = std::nullopt,
                              bool sort_keys = false);
}
