#include "converter.h"
#include <yaml-cpp/yaml.h>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

using yp::KeyMode;
using yp::to_properties;
using yp::to_yaml;
static void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
static void rejects(const std::function<void()>& f, const std::string& fragment) {
    try { f(); } catch (const yp::ConversionError& e) {
        check(std::string(e.what()).find(fragment) != std::string::npos, e.what());
        return;
    }
    throw std::runtime_error("Expected conversion error: " + fragment);
}
int main() {
    std::vector<std::pair<std::string, std::function<void()>>> tests = {
        {"nested YAML and arrays flatten", [] {
            check(to_properties("server:\n  port: 8080\nservers: [localhost, example.com]\n") ==
                  "server.port=8080\nservers[0]=localhost\nservers[1]=example.com\n", "flatten");
        }},
        {"properties become nested string scalars", [] {
            auto n = YAML::Load(to_yaml("server.port=8080\ncode=00123\nenabled=true\n"));
            check(n["server"]["port"].Scalar() == "8080", "port");
            check(n["code"].Scalar() == "00123" && n["code"].Tag() == "!", "quoted code");
            check(n["enabled"].Tag() == "!", "quoted boolean");
        }},
        {"arrays of objects and reversed index order", [] {
            auto n = YAML::Load(to_yaml("users[1].name=Bob\nusers[0].name=Alice\n"));
            check(n["users"].IsSequence() && n["users"].size() == 2, "sequence");
            check(n["users"][0]["name"].Scalar() == "Alice", "first object");
        }},
        {"literal keys stay intact both ways", [] {
            auto yaml = to_yaml("a.b=x\na[0]=y\n", KeyMode::Literal);
            auto n = YAML::Load(yaml);
            check(n["a.b"].Scalar() == "x" && n["a[0]"].Scalar() == "y", "literal keys");
            check(to_properties(yaml, KeyMode::Literal) == "a.b=x\na[0]=y\n", "literal round trip");
        }},
        {"Java separators escapes continuation and comments", [] {
            auto n = YAML::Load(to_yaml("# comment\r\n! comment\rkey\\ with\\ space : first\\\r\n  second\nurl=https\\://example.com\nempty\n"));
            check(n["key with space"].Scalar() == "firstsecond", "continuation");
            check(n["url"].Scalar() == "https://example.com", "colon");
            check(n["empty"].Scalar().empty(), "empty value");
        }},
        {"Unicode literal escaped and surrogate pairs", [] {
            auto n = YAML::Load(to_yaml("name=中文\nemoji=\\uD83D\\uDE00\nc=\\u4e2d\\u6587\n"));
            check(n["name"].Scalar() == "中文" && n["c"].Scalar() == "中文", "Chinese");
            check(n["emoji"].Scalar() == "😀", "surrogate pair");
        }},
        {"Java unknown escapes drop backslash", [] {
            check(YAML::Load(to_yaml("x=\\q\\z\n"))["x"].Scalar() == "qz", "unknown escape");
        }},
        {"empty continuation followed by blank line is ignored like Java", [] {
            check(YAML::Load(to_yaml("\\\n\n", KeyMode::Literal)).size() == 0, "empty continued line");
        }},
        {"empty continuation followed by comment is ignored like Java", [] {
            check(YAML::Load(to_yaml("\\\n  #x\n", KeyMode::Literal)).size() == 0, "continued comment");
        }},
        {"special characters and multiline round trip", [] {
            const std::string input = "' #key:=!': \" leading \\tline\\nnext\\r\\\\tail \"\n";
            auto result = YAML::Load(to_yaml(to_properties(input), KeyMode::Literal));
            check(result[" #key:=!"].Scalar() == " leading \tline\nnext\r\\tail ", "escaping");
        }},
        {"duplicate properties keys rejected", [] { rejects([] { to_yaml("a=1\na=2\n"); }, "Duplicate"); }},
        {"escaped duplicate keys rejected", [] { rejects([] { to_yaml("a=1\n\\u0061=2\n"); }, "Duplicate"); }},
        {"duplicate YAML keys rejected", [] { rejects([] { to_properties("a: 1\na: 2\n"); }, "Duplicate"); }},
        {"scalar and mapping conflict rejected", [] { rejects([] { to_yaml("a=1\na.b=2\n"); }, "conflict"); }},
        {"mapping and scalar conflict rejected", [] { rejects([] { to_yaml("a.b=1\na=2\n"); }, "conflict"); }},
        {"mapping and sequence conflict rejected", [] { rejects([] { to_yaml("a.b=1\na[0]=2\n"); }, "conflict"); }},
        {"sparse arrays rejected", [] { rejects([] { to_yaml("a[1]=x\n"); }, "Sparse"); }},
        {"invalid array syntax rejected", [] { rejects([] { to_yaml("a[-1]=x\n"); }, "index"); }},
        {"leading zero indices rejected", [] { rejects([] { to_yaml("a[00]=x\n"); }, "index"); }},
        {"dotted logger names flatten in default mode", [] {
            check(to_properties("logging:\n  level:\n    com.example: off\n    org.example: debug\n") ==
                  "logging.level.com.example=off\nlogging.level.org.example=debug\n", "logger names");
        }},
        {"dotted keys normalize while preserving property values", [] {
            const std::string props = "logging.level.com.example=off\nlogging.level.org.example=debug\n";
            check(to_properties(to_yaml(props)) == props, "normalized round trip");
            check(to_properties("a.b: x\n") == "a.b=x\n", "root dotted key");
        }},
        {"dotted and nested paths colliding are rejected", [] {
            rejects([] { to_properties("a.b: x\na: {b: y}\n"); }, "Duplicate flattened key");
        }},
        {"special mapping keys round trip under nested mappings", [] {
            const std::vector<std::string> keys = {"a b", "a:b", "a=b", "#tag", "!flag", "/api/*", "a\\b",
                "name[prod]", "tag[prod.eu]", "[all]", "[0]", "a[]", "unmatched[", "unmatched]", "version@1+$%^&()", "中文-key_name"};
            YAML::Emitter out;
            out << YAML::BeginMap << YAML::Key << "root" << YAML::Value << YAML::BeginMap;
            for (const auto& key : keys) out << YAML::Key << YAML::DoubleQuoted << key << YAML::Value << "text";
            out << YAML::EndMap << YAML::EndMap;
            auto restored = YAML::Load(to_yaml(to_properties(out.c_str())));
            for (const auto& key : keys) check(restored["root"][key].Scalar() == "text", key.c_str());
        }},
        {"symbol keys and real array indices coexist", [] {
            auto n = YAML::Load(to_yaml("group[prod][0].a\\:b=x\ngroup[prod][1].a\\:b=y\n"));
            check(n["group[prod]"].IsSequence() && n["group[prod]"][1]["a:b"].Scalar() == "y", "array alongside symbols");
        }},
        {"literal mode rejects nesting", [] { rejects([] { to_properties("a: {b: x}\n", KeyMode::Literal); }, "flat"); }},
        {"null is not silently converted to empty", [] { rejects([] { to_properties("a: null\n"); }, "Null"); }},
        {"empty containers are not silently dropped", [] { rejects([] { to_properties("a: []\n"); }, "Empty"); }},
        {"multiple YAML documents rejected", [] { rejects([] { to_properties("a: x\n---\nb: y\n"); }, "single"); }},
        {"recursive aliases rejected", [] { rejects([] { to_properties("a: &a {b: *a}\n"); }, "Recursive"); }},
        {"nonrecursive aliases expand", [] {
            check(to_properties("a: &a {b: x}\nc: *a\n") == "a.b=x\nc.b=x\n", "alias expansion");
        }},
        {"merge keys require explicit expansion", [] { rejects([] { to_properties("a: &a {x: y}\nb: {<<: *a}\n"); }, "Merge"); }},
        {"malformed YAML reports line", [] { rejects([] { to_properties("a: [\n"); }, "line"); }},
        {"malformed Unicode reports line", [] { rejects([] { to_yaml("a=\\uXX00\n"); }, "line 1"); }},
        {"unpaired surrogates rejected", [] { rejects([] { to_yaml("a=\\uD800\n"); }, "surrogate"); }},
        {"empty documents map to empty mapping", [] {
            check(to_properties("{}").empty(), "empty YAML");
            check(YAML::Load(to_yaml("# only comment\n")).IsMap(), "empty properties");
        }},
        {"UTF-8 BOM accepted", [] { check(to_properties("\xef\xbb\xbf" "a: x\n") == "a=x\n", "BOM"); }},
        {"large index rejected before allocation", [] { rejects([] { to_yaml("a[999999999999999999999]=x\n"); }, "index"); }},
        {"invalid UTF-8 rejected", [] { rejects([] { to_yaml(std::string("a=\xff")); }, "UTF-8"); }},
        {"null bytes in source rejected", [] { rejects([] { to_yaml(std::string("a=x\0y", 5)); }, "NUL"); }},
        {"custom YAML tags rejected", [] { rejects([] { to_properties("a: !custom x\n"); }, "tag"); }},
        {"root sequence rejected", [] { rejects([] { to_properties("- x\n"); }, "mapping"); }},
        {"empty path segments rejected", [] { rejects([] { to_yaml("a..b=x\n"); }, "path"); }},
        {"empty literal key is preserved", [] {
            auto n = YAML::Load(to_yaml("=x\n", KeyMode::Literal));
            check(n[""].Scalar() == "x", "empty key");
        }},
        {"depth bound enforced", [] {
            std::string key = "a"; for (int i=0; i<70; ++i) key += ".a";
            rejects([&] { to_yaml(key + "=x\n"); }, "depth");
        }},
        {"auto detects YAML with dotted keys", [] {
            auto r = yp::auto_convert("logging:\n  level:\n    com.example: off\n");
            check(r.output_format == yp::Format::Properties && r.text == "logging.level.com.example=off\n", "auto YAML");
        }},
        {"auto detects Properties and ignores URL colons", [] {
            auto r = yp::auto_convert("# header\n! comment\nurl=https://example.com\n");
            check(r.output_format == yp::Format::Yaml && YAML::Load(r.text)["url"].Scalar() == "https://example.com", "auto Properties");
        }},
        {"auto file hint resolves colon-only properties", [] {
            auto r = yp::auto_convert("key: value\n", KeyMode::Hierarchical, yp::Format::Properties);
            check(r.output_format == yp::Format::Yaml && YAML::Load(r.text)["key"].Scalar() == "value", "Properties hint");
        }},
        {"auto ambiguous unsaved colon text defaults to YAML", [] {
            auto r = yp::auto_convert("key: value\n");
            check(r.output_format == yp::Format::Properties && r.text == "key=value\n", "default YAML");
        }},
        {"auto respects equals within quoted YAML keys", [] {
            check(yp::auto_convert("'a=b': value\n").text == "a\\=b=value\n", "quoted key");
        }},
        {"auto recognizes flow mappings and document markers", [] {
            check(yp::auto_convert("{a: x}\n").text == "a=x\n", "flow YAML");
            check(yp::auto_convert("---\na: x\n").text == "a=x\n", "document YAML");
        }},
        {"auto malformed YAML is not retried as Properties", [] {
            rejects([] { yp::auto_convert("a: [\n"); }, "line");
        }},
        {"auto preserves literal-key option", [] {
            auto r = yp::auto_convert("a.b=x\n", KeyMode::Literal);
            check(YAML::Load(r.text)["a.b"].Scalar() == "x", "literal auto");
        }},
        {"auto empty input requests explicit direction", [] {
            rejects([] { yp::auto_convert("# comment\n"); }, "detect");
        }}
    };
    int failed = 0;
    for (const auto& test : tests) {
        try { test.second(); std::cout << "PASS " << test.first << '\n'; }
        catch (const std::exception& e) { ++failed; std::cout << "FAIL " << test.first << ": " << e.what() << '\n'; }
    }
    std::cout << tests.size() - failed << '/' << tests.size() << " passed\n";
    return failed ? 1 : 0;
}
