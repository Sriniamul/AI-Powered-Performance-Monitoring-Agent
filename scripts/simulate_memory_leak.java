import java.util.*;

public class SimulateMemoryLeak {
    public static void main(String[] args) throws Exception {
        List<byte[]> leak = new ArrayList<>();
        while (true) {
            leak.add(new byte[5 * 1024 * 1024]);
            System.out.println("Allocated chunks: " + leak.size());
            Thread.sleep(1000);
        }
    }
}
