import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.*;
import java.io.*;
public class Decomp extends GhidraScript {
  public void run() throws Exception {
    String[] a = getScriptArgs();
    PrintWriter out = new PrintWriter(new FileWriter(a[0]));
    DecompInterface di = new DecompInterface(); di.openProgram(currentProgram);
    for (int i = 1; i < a.length; i++) {
      Address ad = toAddr(Long.parseLong(a[i], 16));
      Function fn = getFunctionContaining(ad);
      if (fn == null) { disassemble(ad); fn = createFunction(ad, null); }
      if (fn == null) { out.println("// no function at " + a[i]); continue; }
      DecompileResults r = di.decompileFunction(fn, 180, monitor);
      out.println("// ===== " + fn.getName() + " @ " + fn.getEntryPoint());
      for (ghidra.program.model.symbol.Reference rf : getReferencesTo(fn.getEntryPoint())) { Function c = getFunctionContaining(rf.getFromAddress()); out.println("//   ref from " + rf.getFromAddress() + " " + rf.getReferenceType() + " in " + (c==null?"?":c.getName())); }
      out.println(r.getDecompiledFunction() == null ? r.getErrorMessage() : r.getDecompiledFunction().getC());
    }
    out.close();
  }
}
