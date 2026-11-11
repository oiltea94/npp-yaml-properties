import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.Properties;
import java.util.TreeSet;

public class PropertiesOracle {
    public static void main(String[] args) throws Exception {
        var encoder = Base64.getEncoder();
        for (String file : args) {
            var properties = new Properties();
            try (var reader = Files.newBufferedReader(Path.of(file), StandardCharsets.UTF_8)) {
                properties.load(reader);
            }
            System.out.println("FILE");
            for (String key : new TreeSet<>(properties.stringPropertyNames())) {
                System.out.println(encoder.encodeToString(key.getBytes(StandardCharsets.UTF_8)) + ":" +
                    encoder.encodeToString(properties.getProperty(key).getBytes(StandardCharsets.UTF_8)));
            }
        }
    }
}
