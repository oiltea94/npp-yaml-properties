#include "converter.h"
#include <yaml-cpp/yaml.h>
#include <algorithm>
#include <cstdint>
#include <map>
#include <memory>
#include <set>
#include <unordered_map>
#include <vector>

namespace yp {
namespace {
constexpr std::size_t max_input = 8 * 1024 * 1024;
constexpr std::size_t max_output = 16 * 1024 * 1024;
constexpr std::size_t max_nodes = 100000;
constexpr std::size_t max_depth = 64;
constexpr std::size_t max_index = 9999;

[[noreturn]] void fail(const std::string& message, std::size_t line = 0) {
    throw ConversionError(message + (line ? " (line " + std::to_string(line) + ")" : ""));
}
bool whitespace(char c) { return c == ' ' || c == '\t' || c == '\f'; }

std::string_view validated(std::string_view input) {
    if (input.size() > max_input) fail("Input exceeds 8 MiB.");
    if (input.substr(0, 3) == "\xef\xbb\xbf") input.remove_prefix(3);
    for (std::size_t i = 0; i < input.size();) {
        auto c = static_cast<unsigned char>(input[i++]);
        if (!c) fail("NUL bytes in source text are not accepted; use an escape instead.");
        if (c < 0x80) continue;
        int count = c >= 0xc2 && c <= 0xdf ? 1 : c >= 0xe0 && c <= 0xef ? 2 : c >= 0xf0 && c <= 0xf4 ? 3 : -1;
        if (count < 0 || i + static_cast<std::size_t>(count) > input.size()) fail("Invalid UTF-8 input.");
        std::uint32_t cp = c & (count == 1 ? 0x1f : count == 2 ? 0x0f : 0x07);
        for (int j = 0; j < count; ++j) {
            auto next = static_cast<unsigned char>(input[i++]);
            if ((next & 0xc0) != 0x80) fail("Invalid UTF-8 input.");
            cp = (cp << 6) | (next & 0x3f);
        }
        if ((count == 1 && cp < 0x80) || (count == 2 && cp < 0x800) || (count == 3 && cp < 0x10000) ||
            cp > 0x10ffff || (cp >= 0xd800 && cp <= 0xdfff)) fail("Invalid UTF-8 input.");
    }
    return input;
}
void append_utf8(std::string& out, std::uint32_t cp) {
    if (cp <= 0x7f) out += static_cast<char>(cp);
    else if (cp <= 0x7ff) {
        out += static_cast<char>(0xc0 | (cp >> 6));
        out += static_cast<char>(0x80 | (cp & 0x3f));
    } else if (cp <= 0xffff) {
        out += static_cast<char>(0xe0 | (cp >> 12));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3f));
        out += static_cast<char>(0x80 | (cp & 0x3f));
    } else {
        out += static_cast<char>(0xf0 | (cp >> 18));
        out += static_cast<char>(0x80 | ((cp >> 12) & 0x3f));
        out += static_cast<char>(0x80 | ((cp >> 6) & 0x3f));
        out += static_cast<char>(0x80 | (cp & 0x3f));
    }
}
std::uint32_t hex4(std::string_view text, std::size_t& i, std::size_t line) {
    if (i + 4 > text.size()) fail("Incomplete Unicode escape.", line);
    std::uint32_t value = 0;
    for (int j = 0; j < 4; ++j) {
        char c = text[i++];
        int n = c >= '0' && c <= '9' ? c-'0' : c >= 'a' && c <= 'f' ? c-'a'+10 : c >= 'A' && c <= 'F' ? c-'A'+10 : -1;
        if (n < 0) fail("Invalid Unicode escape.", line);
        value = value * 16 + static_cast<unsigned>(n);
    }
    return value;
}
std::string unescape(std::string_view text, std::size_t line) {
    std::string out;
    for (std::size_t i = 0; i < text.size();) {
        char c = text[i++];
        if (c != '\\') { out += c; continue; }
        if (i == text.size()) break;
        c = text[i++];
        switch (c) {
        case 't': out += '\t'; break;
        case 'n': out += '\n'; break;
        case 'r': out += '\r'; break;
        case 'f': out += '\f'; break;
        case 'u': {
            auto cp = hex4(text, i, line);
            if (cp >= 0xd800 && cp <= 0xdbff) {
                if (i+2 > text.size() || text.substr(i, 2) != "\\u") fail("Unpaired Unicode surrogate.", line);
                i += 2;
                auto low = hex4(text, i, line);
                if (low < 0xdc00 || low > 0xdfff) fail("Unpaired Unicode surrogate.", line);
                cp = 0x10000 + ((cp-0xd800) << 10) + low-0xdc00;
            } else if (cp >= 0xdc00 && cp <= 0xdfff) fail("Unpaired Unicode surrogate.", line);
            append_utf8(out, cp);
            break;
        }
        default: out += c;
        }
    }
    return out;
}
std::string escape(std::string_view text, bool key) {
    const char* hex = "0123456789abcdef";
    std::string out;
    for (std::size_t i = 0; i < text.size(); ++i) {
        auto c = static_cast<unsigned char>(text[i]);
        switch (c) {
        case '\\': out += "\\\\"; break;
        case '\n': out += "\\n"; break;
        case '\r': out += "\\r"; break;
        case '\t': out += "\\t"; break;
        case '\f': out += "\\f"; break;
        case ' ': if (key || i == 0) out += '\\'; out += ' '; break;
        case '=': case ':': case '#': case '!': if (key) out += '\\'; out += static_cast<char>(c); break;
        default:
            if (c < 0x20 || c == 0x7f) { out += "\\u00"; out += hex[c >> 4]; out += hex[c & 15]; }
            else out += static_cast<char>(c);
        }
    }
    return out;
}
struct Property { std::string key; std::string value; std::size_t line; };
std::vector<Property> parse_properties(std::string_view input) {
    std::vector<Property> result;
    std::set<std::string> keys;
    std::size_t pos = 0, physical = 0, start_line = 0;
    std::string logical;
    bool continued = false;
    auto consume = [&] {
        std::size_t key_end = 0;
        bool escaped = false;
        for (; key_end < logical.size(); ++key_end) {
            char c = logical[key_end];
            if (!escaped && (whitespace(c) || c == '=' || c == ':')) break;
            escaped = !escaped && c == '\\';
        }
        std::size_t value_start = key_end;
        while (value_start < logical.size() && whitespace(logical[value_start])) ++value_start;
        if (value_start < logical.size() && (logical[value_start] == '=' || logical[value_start] == ':')) ++value_start;
        while (value_start < logical.size() && whitespace(logical[value_start])) ++value_start;
        auto key = unescape(std::string_view(logical).substr(0, key_end), start_line);
        if (!keys.insert(key).second) fail("Duplicate property key: " + key, start_line);
        result.push_back({std::move(key), unescape(std::string_view(logical).substr(value_start), start_line), start_line});
        if (result.size() > max_nodes) fail("Too many properties.", start_line);
        logical.clear();
    };
    while (pos < input.size()) {
        ++physical;
        auto end = input.find_first_of("\r\n", pos);
        if (end == std::string_view::npos) end = input.size();
        auto part = input.substr(pos, end-pos);
        pos = end;
        if (pos < input.size()) { char c = input[pos++]; if (c == '\r' && pos < input.size() && input[pos] == '\n') ++pos; }
        while (!part.empty() && whitespace(part.front())) part.remove_prefix(1);
        // Java's LineReader treats an empty continued buffer as a new logical line.
        if (continued && logical.empty() && (part.empty() || part.front() == '#' || part.front() == '!')) {
            continued = false;
            continue;
        }
        if (!continued) {
            if (part.empty() || part.front() == '#' || part.front() == '!') continue;
            start_line = physical;
        }
        logical.append(part);
        std::size_t slash_count = 0;
        for (auto i = logical.size(); i && logical[i-1] == '\\'; --i) ++slash_count;
        continued = slash_count % 2 != 0;
        if (continued) logical.pop_back();
        else consume();
    }
    if (continued) consume();
    return result;
}

struct Part { bool index = false; std::string key; std::size_t number = 0; };
std::vector<Part> parse_path(const Property& property, KeyMode mode) {
    if (mode == KeyMode::Literal) return {{false, property.key, 0}};
    const auto& key = property.key;
    std::vector<Part> result;
    std::size_t i = 0;
    while (i < key.size()) {
        std::string name;
        bool indexed = false;
        auto previous_size = result.size();
        while (i < key.size() && key[i] != '.') {
            if (key[i] == '[') {
                auto close = key.find(']', i+1);
                if (close != std::string::npos) {
                    auto content = std::string_view(key).substr(i+1, close-i-1);
                    auto digits = content;
                    if (!digits.empty() && digits.front() == '-') digits.remove_prefix(1);
                    bool numeric = !digits.empty() && std::all_of(digits.begin(), digits.end(), [](char c) { return c >= '0' && c <= '9'; });
                    bool suffix = close+1 == key.size() || key[close+1] == '.' || key[close+1] == '[';
                    if ((!name.empty() || indexed) && numeric && suffix) {
                        if (content.front() == '-' || (content.size() > 1 && content.front() == '0'))
                            fail("Invalid array index: " + key, property.line);
                        if (!name.empty()) { result.push_back({false, std::move(name), 0}); name.clear(); }
                        std::size_t index = 0;
                        for (char c : content) {
                            index = index * 10 + static_cast<unsigned>(c-'0');
                            if (index > max_index) fail("Array index exceeds 9999.", property.line);
                        }
                        result.push_back({true, {}, index});
                        if (result.size() > max_depth) fail("Maximum path depth is 64.", property.line);
                        indexed = true;
                        i = close+1;
                        continue;
                    }
                    if (indexed) fail("Invalid path after array index: " + key, property.line);
                    // Non-numeric brackets are part of the key, including any dots inside.
                    name.append(key, i, close-i+1);
                    i = close+1;
                    continue;
                }
                if (indexed) fail("Invalid path after array index: " + key, property.line);
                // No closing bracket: consume once, avoiding repeated suffix scans.
                auto end = key.find('.', i);
                if (end == std::string::npos) end = key.size();
                name.append(key, i, end-i);
                i = end;
                continue;
            }
            if (indexed) fail("Invalid path after array index: " + key, property.line);
            name += key[i++];
        }
        if (!name.empty()) result.push_back({false, std::move(name), 0});
        if (result.size() == previous_size) fail("Invalid empty path segment: " + key, property.line);
        if (result.size() > max_depth) fail("Maximum path depth is 64.", property.line);
        if (i < key.size()) {
            if (key[i] != '.' || i+1 == key.size()) fail("Invalid path: " + key, property.line);
            ++i;
        }
    }
    if (result.empty()) fail("Empty path; enable Literal keys to preserve an empty key.", property.line);
    return result;
}
struct Tree {
    enum class Kind { Unset, Scalar, Map, Sequence } kind = Kind::Unset;
    std::string value;
    std::vector<std::pair<std::string, std::unique_ptr<Tree>>> entries;
    std::unordered_map<std::string, std::size_t> lookup;
    std::map<std::size_t, std::unique_ptr<Tree>> items;
    std::size_t line = 0;
};
void insert(Tree& root, const Property& property, KeyMode mode, std::size_t& nodes) {
    auto path = parse_path(property, mode);
    auto* current = &root;
    for (const auto& part : path) {
        auto expected = part.index ? Tree::Kind::Sequence : Tree::Kind::Map;
        if (current->kind != Tree::Kind::Unset && current->kind != expected) fail("Path conflict: " + property.key, property.line);
        current->kind = expected;
        current->line = property.line;
        if (part.index) {
            auto& child = current->items[part.number];
            if (!child) { child = std::make_unique<Tree>(); ++nodes; }
            current = child.get();
        } else {
            auto found = current->lookup.find(part.key);
            if (found == current->lookup.end()) {
                auto index = current->entries.size();
                current->lookup.emplace(part.key, index);
                current->entries.emplace_back(part.key, std::make_unique<Tree>());
                current = current->entries.back().second.get();
                ++nodes;
            } else current = current->entries[found->second].second.get();
        }
        if (nodes > max_nodes) fail("Maximum node count exceeded.", property.line);
    }
    if (current->kind != Tree::Kind::Unset) fail("Path conflict: " + property.key, property.line);
    current->kind = Tree::Kind::Scalar;
    current->value = property.value;
}
void emit_tree(YAML::Emitter& out, const Tree& tree) {
    switch (tree.kind) {
    case Tree::Kind::Scalar: out << YAML::DoubleQuoted << tree.value; break;
    case Tree::Kind::Map:
        out << YAML::BeginMap;
        for (const auto& entry : tree.entries) {
            out << YAML::Key << YAML::DoubleQuoted << entry.first << YAML::Value;
            emit_tree(out, *entry.second);
        }
        out << YAML::EndMap;
        break;
    case Tree::Kind::Sequence: {
        out << YAML::BeginSeq;
        std::size_t next = 0;
        for (const auto& item : tree.items) {
            if (item.first != next++) fail("Sparse array: indices must start at 0 without gaps.", tree.line);
            emit_tree(out, *item.second);
        }
        out << YAML::EndSeq;
        break;
    }
    case Tree::Kind::Unset: fail("Unexpected empty tree.");
    }
    if (out.size() > max_output) fail("Output exceeds 16 MiB.");
}

std::size_t line_of(const YAML::Node& node) {
    return node.Mark().is_null() ? 0 : static_cast<std::size_t>(node.Mark().line + 1);
}
void check_tag(const YAML::Node& node) {
    const auto& tag = node.Tag();
    static const std::set<std::string> allowed = {"", "!", "?", "tag:yaml.org,2002:str", "tag:yaml.org,2002:bool",
        "tag:yaml.org,2002:int", "tag:yaml.org,2002:float", "tag:yaml.org,2002:map", "tag:yaml.org,2002:seq",
        "tag:yaml.org,2002:null", "tag:yaml.org,2002:timestamp"};
    if (!allowed.count(tag)) fail("Unsupported YAML tag: " + tag, line_of(node));
}
struct Flattener {
    KeyMode mode;
    std::string output;
    std::set<std::string> keys;
    std::vector<YAML::Node> ancestors;
    std::size_t nodes = 0;

    void visit(const YAML::Node& node, const std::string& path, std::size_t depth) {
        if (depth > max_depth) fail("Maximum YAML depth is 64.", line_of(node));
        if (++nodes > max_nodes) fail("Maximum node count exceeded.", line_of(node));
        check_tag(node);
        if (node.IsNull()) fail("Null has no lossless Properties representation; use an explicit string.", line_of(node));
        if (node.IsScalar()) {
            if (!keys.insert(path).second) fail("Duplicate flattened key: " + path, line_of(node));
            output += escape(path, true) + "=" + escape(node.Scalar(), false) + "\n";
            if (output.size() > max_output) fail("Output exceeds 16 MiB.");
            return;
        }
        if (depth && mode == KeyMode::Literal) fail("Literal keys mode requires a flat mapping of scalar values.", line_of(node));
        if (depth && node.size() == 0) fail("Empty containers have no lossless Properties representation.", line_of(node));
        for (const auto& ancestor : ancestors)
            if (node.is(ancestor)) fail("Recursive YAML alias.", line_of(node));
        ancestors.push_back(node);
        if (node.IsMap()) {
            std::set<std::string> local_keys;
            for (const auto& item : node) {
                if (!item.first.IsScalar()) fail("YAML mapping keys must be scalar strings.", line_of(item.first));
                check_tag(item.first);
                const auto& key = item.first.Scalar();
                if (!local_keys.insert(key).second) fail("Duplicate YAML key: " + key, line_of(item.first));
                if (key == "<<" && item.first.Tag() != "!" && item.first.Tag() != "tag:yaml.org,2002:str")
                    fail("Merge keys must be expanded before conversion.", line_of(item.first));
                if (mode == KeyMode::Hierarchical && key.empty())
                    fail("Empty YAML key; use Literal keys mode for flat mappings.", line_of(item.first));
                visit(item.second, depth ? path + "." + key : key, depth+1);
            }
        } else if (node.IsSequence()) {
            if (node.size() > max_index+1) fail("Array index exceeds 9999.", line_of(node));
            for (std::size_t i = 0; i < node.size(); ++i) visit(node[i], path + "[" + std::to_string(i) + "]", depth+1);
        } else fail("Unsupported YAML node.", line_of(node));
        ancestors.pop_back();
    }
};

Format detect_format(std::string_view input) {
    while (!input.empty()) {
        auto end = input.find_first_of("\r\n");
        auto line = input.substr(0, end);
        input = end == std::string_view::npos ? std::string_view{} : input.substr(end+1);
        while (!line.empty() && whitespace(line.front())) line.remove_prefix(1);
        if (line.empty() || line.front() == '#' || line.front() == '!') continue;
        if (line == "---" || line.substr(0, 4) == "--- " || line.substr(0, 5) == "%YAML") return Format::Yaml;
        char quote = 0;
        bool escaped = false;
        for (std::size_t i = 0; i < line.size(); ++i) {
            char c = line[i];
            if (escaped) { escaped = false; continue; }
            if (c == '\\' && quote != '\'') { escaped = true; continue; }
            if (quote) { if (c == quote) quote = 0; continue; }
            if (c == '\'' || c == '"') { quote = c; continue; }
            if (c == '=') return Format::Properties;
            if (c == ':' && (i+1 == line.size() || whitespace(line[i+1]))) return Format::Yaml;
        }
        if (line.front() == '{' || line.front() == '[' || line.substr(0, 2) == "- ") return Format::Yaml;
        return Format::Properties;
    }
    fail("Could not detect a format from empty/comment-only text. Select a conversion direction manually.");
}
}

std::string to_yaml(std::string_view input, KeyMode mode) {
    input = validated(input);
    Tree root;
    root.kind = Tree::Kind::Map;
    std::size_t nodes = 1;
    for (const auto& property : parse_properties(input)) insert(root, property, mode, nodes);
    YAML::Emitter out;
    out.SetIndent(2);
    emit_tree(out, root);
    if (!out.good()) fail("YAML output error: " + out.GetLastError());
    return std::string(out.c_str(), out.size()) + "\n";
}
std::string to_properties(std::string_view input, KeyMode mode) {
    input = validated(input);
    try {
        auto docs = YAML::LoadAll(std::string(input));
        if (docs.empty()) return {};
        if (docs.size() != 1) fail("Expected a single YAML document.");
        if (!docs.front().IsMap()) fail("YAML root must be a mapping.", line_of(docs.front()));
        Flattener flattener{mode, {}, {}, {}, 0};
        flattener.visit(docs.front(), {}, 0);
        return flattener.output;
    } catch (const YAML::Exception& error) {
        fail("YAML parse error: " + error.msg, error.mark.is_null() ? 0 : static_cast<std::size_t>(error.mark.line+1));
    }
}
ConversionResult auto_convert(std::string_view input, KeyMode mode, std::optional<Format> source_hint) {
    input = validated(input);
    auto source = source_hint ? *source_hint : detect_format(input);
    if (source == Format::Yaml) return {Format::Properties, to_properties(input, mode)};
    return {Format::Yaml, to_yaml(input, mode)};
}
}
