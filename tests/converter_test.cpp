#include "converter.h"
#include <yaml-cpp/yaml.h>
#include <functional>
#include <iostream>
#include <string>
#include <vector>

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
        {"sorting is opt-in and orders sibling keys in both directions", [] {
            const std::string props = "server.port=8080\nspring.profiles.active=\"${profileActive}\"\nserver.address=localhost\n";
            const std::string yaml = "server:\n  port: 8080\n  address: localhost\nspring:\n  profiles:\n    active: \"${profileActive}\"\n";
            const std::string sorted_yaml = "server:\n  address: localhost\n  port: 8080\nspring:\n  profiles:\n    active: \"${profileActive}\"\n";
            const std::string sorted_props = "server.address=localhost\nserver.port=8080\nspring.profiles.active=\"${profileActive}\"\n";
            check(to_yaml(props) == yaml && to_yaml(props, false) == yaml, "default preserves insertion order");
            check(to_properties(yaml) == "server.port=8080\nserver.address=localhost\nspring.profiles.active=\"${profileActive}\"\n", "default flatten order");
            check(to_yaml(props, true) == sorted_yaml, "sort YAML sibling keys");
            check(to_properties(yaml, true) == sorted_props, "sort Properties sibling keys");
            check(yp::auto_convert(props, std::nullopt, true).text == sorted_yaml, "auto Properties sorting");
            check(yp::auto_convert(yaml, yp::Format::Yaml, true).text == sorted_props, "auto YAML sorting");
        }},
        {"sorting preserves sequence positions and sorts object members", [] {
            std::string yaml = "items:\n";
            std::string expected;
            for (int i = 0; i < 12; ++i) {
                yaml += "  - z: \"" + std::to_string(12-i) + "\"\n    a: off\n";
                expected += "items[" + std::to_string(i) + "].a=off\nitems[" + std::to_string(i) + "].z=\"" + std::to_string(12-i) + "\"\n";
            }
            check(to_properties(yaml, true) == expected, "numeric array indices, unchanged element values");
            auto output = YAML::Load(to_yaml(expected, true));
            for (int i = 0; i < 12; ++i) {
                check(output["items"][i].begin()->first.Scalar() == "a", "object member order");
                check(output["items"][i]["z"].Scalar() == std::to_string(12-i), "element order");
            }
        }},
        {"sorting compares decoded keys with case-sensitive Unicode ordering", [] {
            const std::string props = "中=x\na=x\nZ=x\nA=x\na2=x\na10=x\n\\u0062=x\n";
            const std::string expected = "A: x\nZ: x\na: x\na10: x\na2: x\nb: x\n中: x\n";
            check(to_yaml(props, true) == expected, "lexical ordering without locale or natural-number sorting");
            check(to_properties("中: x\n' a': x\na: x\nZ: x\nA: x\n", true) ==
                  "\\ a=x\nA=x\nZ=x\na=x\n中=x\n", "compare decoded keys before Properties escaping");
        }},
        {"sorting preserves logger names quotes and escape spellings", [] {
            const std::string props = "logging.level.org.example=off\nlogging.level.com.example.Mapper=\"debug\"\nlogging.level.com.example=info\n";
            const std::string expected = "logging:\n  level:\n    com.example: info\n    com.example.Mapper: \"debug\"\n    org.example: off\n";
            check(to_yaml(props, true) == expected, "logger names stay complete");
            const std::string yaml = "z: \"line\\nnext\"\na: \"00123\"\n";
            check(to_yaml(to_properties(yaml, true), true) == "a: \"00123\"\nz: \"line\\nnext\"\n", "quotes survive sorting round trip");
        }},
        {"sorting alias mappings does not mutate YAML nodes", [] {
            const std::string yaml = "z: &base {z: \"two\", a: one}\na: *base\n";
            check(to_properties(yaml, true) == "a.a=one\na.z=\"two\"\nz.a=one\nz.z=\"two\"\n", "aliases expanded in sorted order");
            rejects([] { to_properties("z: &z {a: *z}\n", true); }, "Recursive");
            rejects([] { to_properties("a: 1\na: 2\n", true); }, "Duplicate");
            rejects([] { to_properties("a.b: x\na: {b: y}\n", true); }, "Duplicate flattened");
        }},
        {"sorting remains per mapping rather than globally sorting flattened paths", [] {
            check(to_properties("a!: last\na: {z: first}\n", true) == "a.z=first\na\\!=last\n", "keep hierarchy groups together");
            check(to_yaml("a!=last\na.z=first\n", true) == "a:\n  z: first\na!: last\n", "same grouping both ways");
            check(to_properties("{}", true).empty() && to_yaml("", true) == "{}\n", "empty root");
        }},
        {"YAML double quoted values retain quotes in manual and auto conversion", [] {
            const std::string yaml = "name: \"demo\"\ncode: \"00123\"\nprofile: \"${profileActive}\"\nempty: \"\"\nplain: demo\n";
            const std::string props = "name=\"demo\"\ncode=\"00123\"\nprofile=\"${profileActive}\"\nempty=\"\"\nplain=demo\n";
            check(to_properties(yaml) == props, "double quotes retained");
            check(yp::auto_convert(yaml).text == props, "auto retains double quotes");
            check(to_yaml(props) == yaml, "no additional quote layer");
        }},
        {"double quoted escapes survive both syntaxes", [] {
            const std::string yaml = "value: \"line\\nnext\\t\\\"quoted\\\" C:\\\\temp \\u4e2d \\x41\"\n";
            const std::string props = "value=\"line\\\\nnext\\\\t\\\\\"quoted\\\\\" C:\\\\\\\\temp \\\\u4e2d \\\\x41\"\n";
            check(to_properties(yaml) == props, "Properties escapes preserve YAML escape spelling");
            check(to_yaml(to_properties(yaml)) == yaml, "escape spelling round trip");
        }},
        {"quoted values after tags anchors and comments retain their source style", [] {
            const std::string yaml = "a: &text !!str \"demo\"\nb: *text\nc: !!str &other # comment\n  \"off\"\nd: !<tag:yaml.org,2002:str> \"00123\"\ne: ! \"yes\"\nitems: [\"one\", two, *other]\n";
            check(to_properties(yaml) == "a=\"demo\"\nb=\"demo\"\nc=\"off\"\nd=\"00123\"\ne=\"yes\"\nitems[0]=\"one\"\nitems[1]=two\nitems[2]=\"off\"\n", "metadata and aliases");
        }},
        {"UTF-8 source offsets and BOM preserve double quotes", [] {
            const std::string yaml = "\xef\xbb\xbf" "中文: 中文\n名字: \"中文😀\"\nlist: [中文, \"你好\"]\n";
            check(to_properties(yaml) == "中文=中文\n名字=\"中文😀\"\nlist[0]=中文\nlist[1]=\"你好\"\n", "UTF-8 byte positions");
        }},
        {"multiline double quotes normalize to a quoted single line", [] {
            const std::string yaml = "folded: \"first\n  second\"\njoined: \"first\\\n  second\"\n";
            check(to_properties(yaml) == "folded=\"first second\"\njoined=\"firstsecond\"\n", "YAML line folding retained");
            auto result = YAML::Load(to_yaml(to_properties(yaml)));
            check(result["folded"].Scalar() == "first second" && result["joined"].Scalar() == "firstsecond", "multiline semantics");
        }},
        {"plain single quoted and block scalar values retain existing decoding", [] {
            check(to_properties("plain: text\nsingle: 'demo'\nblock: |-\n  \"demo\"\n") ==
                  "plain=text\nsingle=demo\nblock=\"demo\"\n", "only double quoted scalar syntax is retained");
            check(to_properties("value: !!str plain\n") == "value=plain\n", "explicit string tag is not quoting");
        }},
        {"nested YAML and arrays flatten", [] {
            check(to_properties("server:\n  port: 8080\nservers: [localhost, example.com]\n") ==
                  "server.port=8080\nservers[0]=localhost\nservers[1]=example.com\n", "flatten");
        }},
        {"nested scalar spellings are preserved without extra quotes", [] {
            auto n = YAML::Load(to_yaml("server.port=8080\ncode=00123\nenabled=true\n"));
            check(n["server"]["port"].Scalar() == "8080", "port");
            check(n["code"].Scalar() == "00123" && n["code"].Tag() == "?", "unquoted code");
            check(n["enabled"].Tag() == "?", "unquoted boolean");
        }},
        {"default output never adds quotes to numeric or boolean text", [] {
            check(to_yaml("server.port=8080\nlogging.level.com.example=off\n中文=00123\n") ==
                  "server:\n  port: 8080\nlogging:\n  level:\n    com.example: off\n中文: 00123\n", "original unquoted values");
            check(to_yaml("server.port=8080\n") == "server:\n  port: 8080\n", "dotted keys always expand");
        }},
        {"default output retains original single and double quotes", [] {
            const std::string props = "name=\"demo\"\nprofile='${profileActive}'\ncode=\"00123\"\nflag=true\n";
            const std::string expected = "name: \"demo\"\nprofile: '${profileActive}'\ncode: \"00123\"\nflag: true\n";
            check(to_yaml(props) == expected, "original quotes are YAML syntax");
            check(yp::auto_convert(props).text == expected, "auto uses original quotes");
            check(to_yaml("\"name\"='demo'\ntrue=off\n00123=0001\n") ==
                  "\"name\": 'demo'\ntrue: off\n00123: 0001\n", "quoted and unquoted keys preserved");
            auto n = YAML::Load(expected);
            check(n["name"].Scalar() == "demo" && n["profile"].Scalar() == "${profileActive}", "no extra quote layer");
            check(n["code"].Tag() == "!" && n["flag"].Tag() == "?", "source chooses string or implicit type");
        }},
        {"ordinary values and Spring placeholders are plain by default", [] {
            const std::string props = "name=中文\nhost=localhost\nprofile=${profileActive}\nsize=10GB\nurl=https://example.com\n";
            auto yaml = to_yaml(props);
            check(yaml == "name: 中文\nhost: localhost\nprofile: ${profileActive}\nsize: 10GB\nurl: https://example.com\n", "plain default output");
            check(to_properties(yaml) == props, "plain text round trip");
        }},
        {"source quoting preserves log patterns and does not repair unquoted syntax", [] {
            const std::string quoted = "logging.pattern.file=\"%d{yyyy-MM-dd HH:mm:ss.SSS} %5p : %m%n%wEx\"\n";
            check(to_yaml(quoted) == "logging:\n  pattern:\n    file: \"%d{yyyy-MM-dd HH:mm:ss.SSS} %5p : %m%n%wEx\"\n", "quoted logging pattern preserved");
            auto n = YAML::Load(to_yaml(quoted));
            check(n["logging"]["pattern"]["file"].Scalar() == "%d{yyyy-MM-dd HH:mm:ss.SSS} %5p : %m%n%wEx", "log format contains no added quote characters");
            check(to_yaml("pattern=%d{HH:mm:ss}\ncomment=a # b\nempty=\nvalue=null\n") ==
                  "pattern: %d{HH:mm:ss}\ncomment: a # b\nempty: \nvalue: null\n", "source syntax is not auto-quoted");
        }},
        {"source quotes work inside arrays nested arrays and dotted keys", [] {
            const std::string props = "users[1].name='Bob'\nusers[0].name=\"Alice\"\nusers[0].enabled=true\nmatrix[0][0]=00123\nmatrix[0][1]=\"off\"\n";
            const std::string expected = "users:\n  - name: \"Alice\"\n    enabled: true\n  - name: 'Bob'\nmatrix:\n  - - 00123\n    - \"off\"\n";
            check(to_yaml(props) == expected, "nested blocks preserve quotes and indentation");
            auto n = YAML::Load(expected);
            check(n["users"][0]["name"].Scalar() == "Alice" && n["matrix"][0][1].Scalar() == "off", "nested values parse");
            check(to_yaml("server.port=\"8080\"\n") == "server:\n  port: \"8080\"\n", "nested values retain quotes");
            check(to_yaml("message='It''s ready'\n") == "message: 'It''s ready'\n", "original single quote escaping retained");
        }},
        {"double quoted special values retain source syntax", [] {
            const std::vector<std::string> values = {"", "00123", "8080", "true", "FALSE", "off", "Yes", "N", "null", "~",
                "0xFF", "0o17", "0b101", "1_000", "1e3", "-1.2e-3", "+12", ".5", ".NaN", "-.Inf",
                "12:34:56", "2026-11-11", "2026-11-11T12:34:56Z", "2026-11-11 12:34:56 +08:00",
                "<<", "=", "#comment", "a: b", "a #comment", " leading", "trailing ", "line\nbreak", "[a,b]", "*alias"};
            for (const auto& value : values) {
                YAML::Emitter source;
                source << YAML::BeginMap << YAML::Key << "value" << YAML::Value << YAML::DoubleQuoted << value << YAML::EndMap;
                auto props = to_properties(source.c_str());
                check(to_yaml(props) == std::string(source.c_str()) + "\n", "special value quote spelling preserved");
                check(YAML::Load(to_yaml(props))["value"].Scalar() == value, "decoded value unchanged");
            }
        }},
        {"ambiguous and special keys are emitted without additional quotes", [] {
            const std::vector<std::string> keys = {"", "true", "False", "YES", "no", "On", "OFF", "y", "N",
                "null", "~", "00123", "1e3", "-1", "+2", ".nan", "2026-11-11", "<<", "=",
                "a: b", "#tag", "a #comment", " key ", "line\nbreak", "[0]", "*alias", "!tag"};
            for (const auto& key : keys) {
                YAML::Emitter source;
                source << YAML::BeginMap << YAML::Key << YAML::DoubleQuoted << key
                       << YAML::Value << YAML::DoubleQuoted << "off" << YAML::EndMap;
                if (key.empty()) {
                    rejects([&] { to_properties(source.c_str()); }, "Empty YAML key");
                    continue;
                }
                auto props = to_properties(source.c_str());
                if (key == ".nan") {
                    rejects([&] { to_yaml(props); }, "empty path segment");
                    continue;
                }
                check(to_yaml(props) == key + ": \"off\"\n", "special key text preserved");
            }
        }},
        {"manual and auto conversion use the same fixed quoting rule", [] {
            const std::string props = "users[0].name=Alice\nprofile=${profileActive}\n";
            const std::string expected = "users:\n  - name: Alice\nprofile: ${profileActive}\n";
            check(to_yaml(props) == expected, "source spelling retained");
            check(to_properties(expected) == props, "placeholder preserved");
            check(to_yaml("a.b=text\n") == "a:\n  b: text\n", "hierarchical key spelling");
            check(yp::auto_convert(props).text == expected, "auto uses same rule");
            check(yp::auto_convert(expected).text == props, "YAML to Properties unaffected");
        }},
        {"arrays of objects and reversed index order", [] {
            auto n = YAML::Load(to_yaml("users[1].name=Bob\nusers[0].name=Alice\n"));
            check(n["users"].IsSequence() && n["users"].size() == 2, "sequence");
            check(n["users"][0]["name"].Scalar() == "Alice", "first object");
        }},
        {"dotted keys and array indices always expand both ways", [] {
            auto yaml = to_yaml("server.port=8080\nservers[0]=localhost\n");
            auto n = YAML::Load(yaml);
            check(n["server"]["port"].Scalar() == "8080" && n["servers"][0].Scalar() == "localhost", "nested keys and sequence");
            check(to_properties(yaml) == "server.port=8080\nservers[0]=localhost\n", "hierarchical round trip");
        }},
        {"Java separators escapes continuation and comments", [] {
            auto yaml = to_yaml("# comment\r\n! comment\rkey\\ with\\ space : first\\\r\n  second\nurl=https\\://example.com\nempty\n");
            check(yaml == "key with space: firstsecond\nurl: https://example.com\nempty: \n", "Java syntax decoded");
            auto n = YAML::Load(yaml);
            check(n["key with space"].Scalar() == "firstsecond", "continuation");
            check(n["url"].Scalar() == "https://example.com", "colon");
            check(n["empty"].IsNull(), "unquoted empty value follows YAML syntax");
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
            check(YAML::Load(to_yaml("\\\n\n")).size() == 0, "empty continued line");
        }},
        {"empty continuation followed by comment is ignored like Java", [] {
            check(YAML::Load(to_yaml("\\\n  #x\n")).size() == 0, "continued comment");
        }},
        {"special characters and multiline decoded text are retained", [] {
            const std::string input = "' #key:=!': \" leading \\tline\\nnext\\r\\\\tail \"\n";
            check(to_yaml(to_properties(input)) ==
                  " #key:=!: \" leading \\tline\\nnext\\r\\\\tail \"\n", "escaping");
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
        {"logger packages and classes coexist in either input order", [] {
            const std::string parent = "logging.level.com.example=debug\n";
            const std::string child = "logging.level.com.example.dao.Mapper=off\n";
            for (const auto& props : {parent + child, child + parent}) {
                auto yaml = to_yaml(props);
                auto level = YAML::Load(yaml)["logging"]["level"];
                check(level.size() == 2, "two independent logger names");
                check(level["com.example"].Scalar() == "debug", "package level");
                check(level["com.example.dao.Mapper"].Scalar() == "off", "class level");
                check(to_properties(yaml) == props, "logger order and values round trip");
            }
        }},
        {"logger names are literal only beneath the exact logging level prefix", [] {
            auto n = YAML::Load(to_yaml("logging.level.root=info\nlogging.level.com.example=off\n"
                                       "logging.logback.rollingpolicy.max-history=180\n"
                                       "logbook.predicate.exclude[0].path=/api/**\n"
                                       "custom.logging.level.com.example=trace\n"));
            check(n["logging"]["level"]["root"].Scalar() == "info", "root logger");
            check(n["logging"]["level"]["com.example"].Scalar() == "off", "literal logger");
            check(n["logging"]["logback"]["rollingpolicy"]["max-history"].Scalar() == "180", "ordinary paths");
            check(n["logbook"]["predicate"]["exclude"][0]["path"].Scalar() == "/api/**", "array path");
            check(n["custom"]["logging"]["level"]["com"]["example"].Scalar() == "trace", "exact prefix only");
        }},
        {"logger grouping always preserves complete logger names", [] {
            const std::string props = "logging.level.com.example=info\nlogging.level.com.example.Mapper=off\n";
            auto yaml = to_yaml(props);
            auto n = YAML::Load(yaml);
            check(n["logging"]["level"]["com.example"].Scalar() == "info", "package logger");
            check(n["logging"]["level"]["com.example.Mapper"].Scalar() == "off", "class logger");
            check(to_properties(yaml) == props, "logger round trip");
        }},
        {"logger grouping still rejects namespace conflicts and empty logger names", [] {
            rejects([] { to_yaml("logging.level=info\nlogging.level.com.example=off\n"); }, "conflict");
            rejects([] { to_yaml("logging.level.com.example=off\nlogging.level=info\n"); }, "conflict");
            rejects([] { to_yaml("logging.level.=off\n"); }, "Invalid path");
        }},
        {"dotted keys normalize while preserving property values", [] {
            const std::string props = "logging.level.com.example=off\nlogging.level.org.example=debug\n";
            check(to_properties(to_yaml(props)) == props, "normalized round trip");
            check(to_properties("a.b: x\n") == "a.b=x\n", "root dotted key");
        }},
        {"dotted and nested paths colliding are rejected", [] {
            rejects([] { to_properties("a.b: x\na: {b: y}\n"); }, "Duplicate flattened key");
        }},
        {"special mapping keys retain parsed spelling under nested mappings", [] {
            const std::vector<std::string> keys = {"a b", "a:b", "a=b", "#tag", "!flag", "/api/*", "a\\b",
                "name[prod]", "tag[prod.eu]", "[all]", "[0]", "a[]", "unmatched[", "unmatched]", "version@1+$%^&()", "中文-key_name"};
            YAML::Emitter out;
            out << YAML::BeginMap << YAML::Key << "root" << YAML::Value << YAML::BeginMap;
            for (const auto& key : keys) out << YAML::Key << YAML::DoubleQuoted << key << YAML::Value << "text";
            out << YAML::EndMap << YAML::EndMap;
            std::string expected = "root:\n";
            for (const auto& key : keys) expected += "  " + key + ": text\n";
            check(to_yaml(to_properties(out.c_str())) == expected, "special nested key text");
        }},
        {"symbol keys and real array indices coexist", [] {
            auto n = YAML::Load(to_yaml("group[prod][0].a\\:b=x\ngroup[prod][1].a\\:b=y\n"));
            check(n["group[prod]"].IsSequence() && n["group[prod]"][1]["a:b"].Scalar() == "y", "array alongside symbols");
        }},
        {"nested YAML always flattens", [] { check(to_properties("a: {b: x}\n") == "a.b=x\n", "nested mapping"); }},
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
        {"empty keys reject with line numbers and no removed-mode suggestion", [] {
            rejects([] { to_yaml("=x\n"); }, "Empty property key has no hierarchical path. (line 1)");
            rejects([] { to_properties("\"\": x\n"); }, "Empty YAML key has no hierarchical path. (line 1)");
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
            auto r = yp::auto_convert("key: value\n", yp::Format::Properties);
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
        {"auto always expands dotted keys", [] {
            auto r = yp::auto_convert("a.b=x\n");
            check(YAML::Load(r.text)["a"]["b"].Scalar() == "x", "hierarchical auto");
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
