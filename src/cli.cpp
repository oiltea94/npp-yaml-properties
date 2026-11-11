#include "converter.h"
#include <fcntl.h>
#include <io.h>
#include <iostream>
#include <iterator>
#include <string>

int main(int argc, char** argv) {
    if (argc < 2 || argc > 3 || (std::string(argv[1]) != "to-yaml" && std::string(argv[1]) != "to-properties") ||
        (argc == 3 && std::string(argv[2]) != "--literal")) {
        std::cerr << "Usage: ypconvert (to-yaml|to-properties) [--literal] < input > output\n";
        return 2;
    }
    _setmode(_fileno(stdin), _O_BINARY);
    _setmode(_fileno(stdout), _O_BINARY);
    try {
        std::string input((std::istreambuf_iterator<char>(std::cin)), {});
        auto mode = argc == 3 ? yp::KeyMode::Literal : yp::KeyMode::Hierarchical;
        std::cout << (std::string(argv[1]) == "to-yaml" ? yp::to_yaml(input, mode) : yp::to_properties(input, mode));
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
    return 0;
}
