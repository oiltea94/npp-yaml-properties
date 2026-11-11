#pragma once

#include <stdexcept>
#include <string>
#include <string_view>
#include <optional>

namespace yp {
enum class KeyMode { Hierarchical, Literal };
enum class Format { Yaml, Properties };
struct ConversionResult { Format output_format; std::string text; };
class ConversionError : public std::runtime_error {
public:
    using std::runtime_error::runtime_error;
};
std::string to_properties(std::string_view input, KeyMode mode = KeyMode::Hierarchical);
std::string to_yaml(std::string_view input, KeyMode mode = KeyMode::Hierarchical);
ConversionResult auto_convert(std::string_view input, KeyMode mode = KeyMode::Hierarchical,
                              std::optional<Format> source_hint = std::nullopt);
}
