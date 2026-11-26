import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import ghidra.program.model.mem.*;
import ghidra.program.model.symbol.*;
import java.util.*;
import java.io.*;

// args: outfile needle1 needle2 ... ; finds strings, refs (incl. lis/addi pairs via analysis), decompiles functions
public class StrRefs extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter out = new PrintWriter(new FileWriter(a[0]));
    DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
    Memory mem = currentProgram.getMemory();
    Set<Function> done = new HashSet<>();
    for (int i = 1; i < a.length; i++) {
      byte[] needle = (a[i] + "\0").getBytes();
      Address s = mem.getMinAddress();
      while (true) {
        Address f = mem.findBytes(s, needle, null, true, monitor);
        if (f == null) break;
        out.println("### string '" + a[i] + "' at " + f);
        for (Reference r : getReferencesTo(f)) {
          Function fn = getFunctionContaining(r.getFromAddress());
          out.println("  ref from " + r.getFromAddress() + " in " + (fn == null ? "?" : fn.getName() + "@" + fn.getEntryPoint()));
          if (fn != null && done.add(fn)) {
            DecompileResults res = di.decompileFunction(fn, 120, monitor);
            out.println("---- " + fn.getName() + " @ " + fn.getEntryPoint());
            out.println(res.getDecompiledFunction() == null ? res.getErrorMessage() : res.getDecompiledFunction().getC());
          }
        }
        s = f.add(1);
      }
    }
    out.close();
  }
}
